from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import jsonschema
import pytest

from code_review.adapters.js_base import node_binary

FIXTURE = Path(__file__).parent.parent / "fixtures" / "js-with-known-issues"
SARIF_SCHEMA = Path(__file__).parent.parent.parent / "code_review" / "schemas" / "sarif-2.1.0.json"


def test_jscpd_protocol_conformance() -> None:
    from code_review.adapters.jscpd import JscpdAdapter
    from code_review.contracts import Analyzer

    assert isinstance(JscpdAdapter(), Analyzer)
    assert JscpdAdapter.name == "jscpd"
    assert JscpdAdapter.node_tool == "jscpd"


async def test_jscpd_returns_error_when_binary_absent(tmp_path: Path) -> None:
    from code_review.adapters.jscpd import JscpdAdapter
    from code_review.contracts import ReviewRequest

    with patch("code_review.adapters.jscpd.node_binary", return_value=None):
        request = ReviewRequest(
            scope="per-task", diff_range=None,
            target_paths=(str(tmp_path),),
            languages=frozenset(), config={},
        )
        output = await JscpdAdapter().run(request)
    assert output.status == "error"
    assert "setup.sh" in (output.error or "")


async def test_jscpd_empty_target_paths() -> None:
    from code_review.adapters.jscpd import JscpdAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(
        scope="per-task", diff_range=None,
        target_paths=(), languages=frozenset(), config={},
    )
    with patch("code_review.adapters.jscpd.node_binary", return_value=Path("/fake/jscpd")):
        output = await JscpdAdapter().run(request)
    assert output.status == "ok"


async def test_jscpd_parses_json_to_sarif() -> None:
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.jscpd import JscpdAdapter
    from code_review.contracts import ReviewRequest

    fake_json = json.dumps({
        "duplicates": [
            {
                "firstFile": {"name": "src/a.ts", "start": 10},
                "secondFile": {"name": "src/b.ts", "start": 20},
            }
        ],
        "statistics": {"total": {"duplicatedLines": 5}},
    }).encode()

    request = ReviewRequest(
        scope="per-task", diff_range=None,
        target_paths=("src/",), languages=frozenset(), config={},
    )
    with (
        patch("code_review.adapters.jscpd.node_binary", return_value=Path("/fake/jscpd")),
        patch(
            "code_review.adapters.jscpd.run_subprocess",
            new=AsyncMock(return_value=SubprocessResult(fake_json, b"", 0)),
        ),
    ):
        output = await JscpdAdapter().run(request)

    assert output.status == "ok"
    assert output.sarif["runs"][0]["tool"]["driver"]["name"] == "jscpd"
    results = output.sarif["runs"][0]["results"]
    assert len(results) == 1
    assert results[0]["ruleId"] == "jscpd.duplicate-code"
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)


async def test_jscpd_handles_empty_duplicates() -> None:
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.jscpd import JscpdAdapter
    from code_review.contracts import ReviewRequest

    fake_json = json.dumps({"duplicates": [], "statistics": {}}).encode()

    request = ReviewRequest(
        scope="per-task", diff_range=None,
        target_paths=("src/",), languages=frozenset(), config={},
    )
    with (
        patch("code_review.adapters.jscpd.node_binary", return_value=Path("/fake/jscpd")),
        patch(
            "code_review.adapters.jscpd.run_subprocess",
            new=AsyncMock(return_value=SubprocessResult(fake_json, b"", 0)),
        ),
    ):
        output = await JscpdAdapter().run(request)

    assert output.status == "ok"
    assert output.sarif["runs"][0]["results"] == []


@pytest.mark.skipif(
    node_binary("jscpd") is None,
    reason="jscpd not in node_modules (run scripts/setup.sh)",
)
async def test_jscpd_integration() -> None:
    from code_review.adapters.jscpd import JscpdAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=(str(FIXTURE),),
        languages=frozenset({"javascript", "typescript"}),
        config={},
    )
    output = await JscpdAdapter().run(request)
    assert output.status == "ok"
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)
