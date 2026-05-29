from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import jsonschema
import pytest

from code_review.adapters.js_base import node_binary

FIXTURE = Path(__file__).parent.parent / "fixtures" / "js-with-known-issues"
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


@pytest.mark.skipif(
    node_binary("depcruise") is None,
    reason="depcruise not in node_modules (run scripts/setup.sh)",
)
async def test_depcruiser_integration() -> None:
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
    assert output.status == "ok"
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)
