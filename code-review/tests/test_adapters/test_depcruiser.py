from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import jsonschema
import pytest

from code_review.adapters.js_base import node_binary

FIXTURE = Path(__file__).parent.parent / "fixtures" / "js-with-known-issues"
# Dedicated cycle fixture: cycle_a.ts imports cycle_b.ts and vice versa, so
# depcruise reports a circular dependency (js-with-known-issues has no cycle —
# asserting findings there would be zero-signal). Mirrors s2's js-duplication.
CIRCULAR_FIXTURE = Path(__file__).parent.parent / "fixtures" / "js-circular"
SARIF_SCHEMA = Path(__file__).parent.parent.parent / "code_review" / "schemas" / "sarif-2.1.0.json"


def test_depcruiser_protocol_conformance() -> None:
    from code_review.adapters.depcruiser import DependencyCruiserAdapter
    from code_review.contracts import Analyzer

    assert isinstance(DependencyCruiserAdapter(), Analyzer)
    assert DependencyCruiserAdapter.name == "depcruiser"
    assert DependencyCruiserAdapter.node_tool == "depcruise"


async def test_depcruiser_returns_error_when_binary_absent(tmp_path: Path) -> None:
    from code_review.adapters.depcruiser import DependencyCruiserAdapter
    from code_review.contracts import ReviewRequest

    with patch("code_review.adapters.depcruiser.node_binary", return_value=None):
        request = ReviewRequest(
            scope="per-task", diff_range=None,
            target_paths=(str(tmp_path),),
            languages=frozenset(), config={},
        )
        output = await DependencyCruiserAdapter().run(request)
    assert output.status == "error"
    assert "setup.sh" in (output.error or "")


async def test_depcruiser_empty_target_paths() -> None:
    from code_review.adapters.depcruiser import DependencyCruiserAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(
        scope="per-task", diff_range=None,
        target_paths=(), languages=frozenset(), config={},
    )
    with patch("code_review.adapters.depcruiser.node_binary", return_value=Path("/fake/depcruise")):
        output = await DependencyCruiserAdapter().run(request)
    assert output.status == "ok"


async def test_depcruiser_parses_json_to_sarif() -> None:
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.depcruiser import DependencyCruiserAdapter
    from code_review.contracts import ReviewRequest

    fake_json = json.dumps({
        "modules": [
            {
                "source": "src/a.ts",
                "dependencies": [
                    {"resolved": "src/b.ts", "circular": True},
                    {"resolved": "src/c.ts", "circular": False},
                ],
            },
            {
                "source": "src/d.ts",
                "dependencies": [],
            },
        ]
    }).encode()

    request = ReviewRequest(
        scope="per-task", diff_range=None,
        target_paths=("src/",), languages=frozenset(), config={},
    )
    with (
        patch("code_review.adapters.depcruiser.node_binary", return_value=Path("/fake/depcruise")),
        patch(
            "code_review.adapters.depcruiser.run_subprocess",
            new=AsyncMock(return_value=SubprocessResult(fake_json, b"", 0)),
        ),
    ):
        output = await DependencyCruiserAdapter().run(request)

    assert output.status == "ok"
    assert output.sarif["runs"][0]["tool"]["driver"]["name"] == "dependency-cruiser"
    results = output.sarif["runs"][0]["results"]
    assert len(results) == 1
    assert results[0]["ruleId"] == "depcruiser.circular-dependency"
    assert "src/a.ts" in results[0]["message"]["text"]
    assert "src/b.ts" in results[0]["message"]["text"]
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)


async def test_depcruiser_no_circular_deps() -> None:
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.depcruiser import DependencyCruiserAdapter
    from code_review.contracts import ReviewRequest

    fake_json = json.dumps({
        "modules": [
            {
                "source": "src/a.ts",
                "dependencies": [{"resolved": "src/b.ts", "circular": False}],
            }
        ]
    }).encode()

    request = ReviewRequest(
        scope="per-task", diff_range=None,
        target_paths=("src/",), languages=frozenset(), config={},
    )
    with (
        patch("code_review.adapters.depcruiser.node_binary", return_value=Path("/fake/depcruise")),
        patch(
            "code_review.adapters.depcruiser.run_subprocess",
            new=AsyncMock(return_value=SubprocessResult(fake_json, b"", 0)),
        ),
    ):
        output = await DependencyCruiserAdapter().run(request)

    assert output.status == "ok"
    assert output.sarif["runs"][0]["results"] == []


@pytest.mark.integration
@pytest.mark.skipif(
    node_binary("depcruise") is None,
    reason="depcruise not in node_modules (run scripts/setup.sh)",
)
async def test_depcruiser_integration() -> None:
    """s3-t1 (F1): end-to-end on the vendored toolchain. The target carries no
    cruise config, so the adapter must supply its own; depcruise then reports the
    cycle_a.ts <-> cycle_b.ts circular dependency. Was xfail(strict) through
    s3-t0 (depcruise loaded past R_OK but aborted on the missing config); s3-t1
    supplies the config and flips this to a real pass (asserting findings, not
    just status — per the analyzer-test discipline)."""
    from code_review.adapters.depcruiser import DependencyCruiserAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=(str(CIRCULAR_FIXTURE),),
        languages=frozenset({"javascript", "typescript"}),
        config={},
    )
    output = await DependencyCruiserAdapter().run(request)
    assert output.status == "ok", output.error
    results = output.sarif["runs"][0]["results"]
    assert len(results) >= 1, "expected >=1 circular-dependency finding on the cycle fixture"
    assert all(r["ruleId"] == "depcruiser.circular-dependency" for r in results)
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)


async def test_depcruiser_supplies_config_when_target_has_none(tmp_path: Path) -> None:
    """s3-t1 (F1): dependency-cruiser aborts with "Can't open a config file"
    when invoked without one. The adapter must supply its own config so a target
    that has no ``.dependency-cruiser.cjs`` is still analysed — assert depcruise
    is invoked with ``--config`` pointing at a real file the adapter created."""
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.depcruiser import DependencyCruiserAdapter
    from code_review.contracts import ReviewRequest

    captured: dict[str, Any] = {}

    async def fake_run(*cmd: str, timeout_s: int = 0) -> SubprocessResult:
        captured["cmd"] = cmd
        if "--config" in cmd:
            config_path = Path(cmd[cmd.index("--config") + 1])
            captured["config_exists"] = config_path.is_file()
            captured["config_text"] = config_path.read_text() if config_path.is_file() else ""
        else:
            captured["config_exists"] = False
            captured["config_text"] = ""
        return SubprocessResult(b'{"modules": []}', b"", 0)

    request = ReviewRequest(
        scope="per-task", diff_range=None,
        target_paths=(str(tmp_path),), languages=frozenset(), config={},
    )
    with (
        patch("code_review.adapters.depcruiser.node_binary", return_value=Path("/fake/depcruise")),
        patch("code_review.adapters.depcruiser.run_subprocess", new=fake_run),
    ):
        output = await DependencyCruiserAdapter().run(request)

    assert output.status == "ok"
    assert "--config" in captured["cmd"], "adapter must pass --config (depcruise requires it)"
    assert captured["config_exists"], "the --config file must exist when depcruise is invoked"
    # Guard the config *contents*, not just its presence, so a refactor that writes
    # an empty/wrong config is caught here without the vendored toolchain.
    assert "enhancedResolveOptions" in captured["config_text"], (
        "config must set enhancedResolveOptions.extensions to resolve bare TS/JS imports"
    )
    assert "doNotFollow" in captured["config_text"]


@pytest.mark.integration
@pytest.mark.skipif(
    node_binary("depcruise") is None,
    reason="depcruise not in node_modules (run scripts/setup.sh)",
)
async def test_depcruiser_loads_without_r_ok_syntaxerror() -> None:
    """s3-t0 (F1): after the pin bump, dependency-cruiser must load and run on the
    supported Node range — it no longer dies with the ``node:fs`` ``R_OK``
    SyntaxError at ``assert-file-existence.mjs``. It may still fail here (the
    adapter supplies no ``--config`` until s3-t1, so depcruise aborts on the
    missing config), but the failure mode must be the *config* error, never the
    ``R_OK`` SyntaxError."""
    from code_review.adapters.depcruiser import DependencyCruiserAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=(str(FIXTURE),),
        languages=frozenset({"javascript", "typescript"}),
        config={},
    )
    output = await DependencyCruiserAdapter().run(request)
    err = output.error or ""
    assert "R_OK" not in err, f"R_OK SyntaxError still present (pin not bumped?): {err}"
    assert "does not provide an export named" not in err, (
        f"node:fs named-export SyntaxError still present: {err}"
    )
