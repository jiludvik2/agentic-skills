"""s1-t2 — dependency-cruiser invoke-and-capture contract (ADR-0020).

Pins the load-bearing invocation (the adapter supplies its own ``--config`` because
depcruise aborts without one; ``--output-type json`` so the dependency graph lands on
stdout; the directory target), the raw stdout passthrough (no parse / no _to_sarif), and
the availability pre-flight (missing binary → unavailable per ADR-0019, no longer error).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from code_review.adapters.depcruiser import DependencyCruiserAdapter
from code_review.adapters.js_base import node_binary
from code_review.capture import CaptureOutput
from code_review.contracts import Analyzer, ReviewRequest

FIXTURE = Path(__file__).parent.parent / "fixtures" / "js-with-known-issues"
# Dedicated cycle fixture: cycle_a.ts <-> cycle_b.ts, so depcruise reports a circular dep.
CIRCULAR_FIXTURE = Path(__file__).parent.parent / "fixtures" / "js-circular"


def _req(paths: tuple[str, ...]) -> ReviewRequest:
    return ReviewRequest(scope="per-task", diff_range=None, target_paths=paths,
                         languages=frozenset(), config={})


def test_depcruiser_protocol_conformance() -> None:
    assert isinstance(DependencyCruiserAdapter(), Analyzer)
    assert DependencyCruiserAdapter.name == "depcruiser"
    assert DependencyCruiserAdapter.node_tool == "depcruise"


async def test_depcruiser_invocation_pins_config_and_json_dir_target(tmp_path: Path) -> None:
    """Pins the self-supplied ``--config`` (file present + correct contents), the
    ``--output-type json`` dependency graph, and the directory target."""
    captured: dict[str, Any] = {}

    async def fake(*args: str, **kwargs: object) -> CaptureOutput:
        captured["args"] = args
        config_path = Path(args[args.index("--config") + 1])
        captured["config_exists"] = config_path.is_file()
        captured["config_text"] = config_path.read_text() if config_path.is_file() else ""
        return CaptureOutput(tool="depcruiser", stdout='{"modules": []}', exit_code=0)

    with (
        patch("code_review.adapters.depcruiser.node_binary", return_value=Path("/fake/depcruise")),
        patch("code_review.adapters.depcruiser.run_and_capture", new=fake),
    ):
        await DependencyCruiserAdapter().run(_req((str(tmp_path),)))

    args = captured["args"]
    assert args[0] == "depcruiser"
    assert "node" in args
    assert args[args.index("--output-type") + 1] == "json"
    assert str(tmp_path) in args, "the directory target must be passed to depcruise"
    assert captured["config_exists"], "the --config file must exist when depcruise is invoked"
    # Guard the config contents, not just presence: a refactor writing an empty/wrong
    # config is caught here without the vendored toolchain.
    assert "enhancedResolveOptions" in captured["config_text"], (
        "config must set enhancedResolveOptions.extensions to resolve bare TS/JS imports"
    )
    assert "doNotFollow" in captured["config_text"]


async def test_depcruiser_captures_raw_stdout(tmp_path: Path) -> None:
    cap = CaptureOutput(tool="depcruiser", stdout='{"modules": []}', exit_code=0)
    with (
        patch("code_review.adapters.depcruiser.node_binary", return_value=Path("/fake/depcruise")),
        patch("code_review.adapters.depcruiser.run_and_capture", new=AsyncMock(return_value=cap)),
    ):
        out = await DependencyCruiserAdapter().run(_req((str(tmp_path),)))
    assert out is cap


async def test_depcruiser_unavailable_when_vendored_binary_absent(tmp_path: Path) -> None:
    with patch("code_review.adapters.depcruiser.node_binary", return_value=None):
        out = await DependencyCruiserAdapter().run(_req((str(tmp_path),)))
    assert out.status == "unavailable"
    assert "setup.sh" in (out.error or "")


async def test_depcruiser_empty_target_paths_unavailable() -> None:
    with patch("code_review.adapters.depcruiser.node_binary", return_value=Path("/fake/depcruise")):
        out = await DependencyCruiserAdapter().run(_req(()))
    assert out.status == "unavailable"


@pytest.mark.integration
@pytest.mark.skipif(
    node_binary("depcruise") is None,
    reason="depcruise not in node_modules (run scripts/setup.sh)",
)
async def test_depcruiser_integration() -> None:
    """End-to-end on the vendored toolchain: the target carries no cruise config, so the
    adapter supplies its own; depcruise then reports the cycle_a.ts <-> cycle_b.ts circular
    dependency in the raw JSON capture."""
    request = ReviewRequest(
        scope="per-task", diff_range=None, target_paths=(str(CIRCULAR_FIXTURE),),
        languages=frozenset({"javascript", "typescript"}), config={},
    )
    out = await DependencyCruiserAdapter().run(request)
    assert out.status == "ok", out.error
    assert out.stdout, "expected a non-empty raw dependency-graph capture"
    data = json.loads(out.stdout)
    circular = [
        dep
        for module in data.get("modules", [])
        for dep in module.get("dependencies", [])
        if dep.get("circular", False)
    ]
    assert len(circular) >= 1, "expected >=1 circular dependency on the cycle fixture"


@pytest.mark.integration
@pytest.mark.skipif(
    node_binary("depcruise") is None,
    reason="depcruise not in node_modules (run scripts/setup.sh)",
)
async def test_depcruiser_loads_without_r_ok_syntaxerror() -> None:
    """After the pin bump, depcruise must load and run on the supported Node range — it no
    longer dies with the ``node:fs`` ``R_OK`` SyntaxError. Whatever the outcome, the
    failure mode must never be that SyntaxError."""
    request = ReviewRequest(
        scope="per-task", diff_range=None, target_paths=(str(FIXTURE),),
        languages=frozenset({"javascript", "typescript"}), config={},
    )
    out = await DependencyCruiserAdapter().run(request)
    blob = f"{out.error or ''}\n{out.stderr}"
    assert "R_OK" not in blob, f"R_OK SyntaxError still present (pin not bumped?): {blob}"
    assert "does not provide an export named" not in blob, (
        f"node:fs named-export SyntaxError still present: {blob}"
    )
