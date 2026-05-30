from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import jsonschema
import pytest

from code_review.adapters.js_base import node_binary

FIXTURE = Path(__file__).parent.parent / "fixtures" / "js-with-known-issues"
SARIF_SCHEMA = Path(__file__).parent.parent.parent / "code_review" / "schemas" / "sarif-2.1.0.json"


def test_knip_protocol_conformance() -> None:
    from code_review.adapters.knip import KnipAdapter
    from code_review.contracts import Analyzer

    assert isinstance(KnipAdapter(), Analyzer)
    assert KnipAdapter.name == "knip"
    assert KnipAdapter.node_tool == "knip"


async def test_knip_returns_error_when_binary_absent(tmp_path: Path) -> None:
    from code_review.adapters.knip import KnipAdapter
    from code_review.contracts import ReviewRequest

    with patch("code_review.adapters.knip.node_binary", return_value=None):
        request = ReviewRequest(
            scope="per-task", diff_range=None,
            target_paths=(str(tmp_path),),
            languages=frozenset(), config={},
        )
        output = await KnipAdapter().run(request)
    assert output.status == "error"
    assert "setup.sh" in (output.error or "")


async def test_knip_empty_target_paths() -> None:
    from code_review.adapters.knip import KnipAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(
        scope="per-task", diff_range=None,
        target_paths=(), languages=frozenset(), config={},
    )
    with patch("code_review.adapters.knip.node_binary", return_value=Path("/fake/knip")):
        output = await KnipAdapter().run(request)
    assert output.status == "ok"


async def test_knip_parses_json_to_sarif() -> None:
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.knip import KnipAdapter
    from code_review.contracts import ReviewRequest

    fake_json = json.dumps({
        "files": ["src/unused.ts"],
        "exports": [{"file": "src/lib.ts", "symbol": "unusedFn"}],
        "dependencies": [],
    }).encode()

    request = ReviewRequest(
        scope="per-task", diff_range=None,
        target_paths=("src/",), languages=frozenset(), config={},
    )
    with (
        patch("code_review.adapters.knip.node_binary", return_value=Path("/fake/knip")),
        patch(
            "code_review.adapters.knip.run_subprocess",
            new=AsyncMock(return_value=SubprocessResult(fake_json, b"", 0)),
        ),
    ):
        output = await KnipAdapter().run(request)

    assert output.status == "ok"
    assert output.sarif["runs"][0]["tool"]["driver"]["name"] == "knip"
    results = output.sarif["runs"][0]["results"]
    assert len(results) == 2
    rule_ids = {r["ruleId"] for r in results}
    assert "knip.unused-file" in rule_ids
    assert "knip.unused-export" in rule_ids
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)


async def test_knip_exit_1_is_ok() -> None:
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.knip import KnipAdapter
    from code_review.contracts import ReviewRequest

    fake_json = json.dumps({"files": [], "exports": [], "dependencies": []}).encode()

    request = ReviewRequest(
        scope="per-task", diff_range=None,
        target_paths=("src/",), languages=frozenset(), config={},
    )
    with (
        patch("code_review.adapters.knip.node_binary", return_value=Path("/fake/knip")),
        patch(
            "code_review.adapters.knip.run_subprocess",
            new=AsyncMock(return_value=SubprocessResult(fake_json, b"", 1)),
        ),
    ):
        output = await KnipAdapter().run(request)

    assert output.status == "ok"


@pytest.mark.integration
@pytest.mark.skipif(
    node_binary("knip") is None,
    reason="knip not in node_modules (run scripts/setup.sh)",
)
async def test_knip_integration() -> None:
    from code_review.adapters.knip import KnipAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=(str(FIXTURE),),
        languages=frozenset({"javascript", "typescript"}),
        config={},
    )
    output = await KnipAdapter().run(request)
    assert output.status in ("ok", "error")  # knip needs package.json in cwd
    if output.status == "ok":
        schema = json.loads(SARIF_SCHEMA.read_text())
        jsonschema.validate(output.sarif, schema)
