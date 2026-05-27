import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import jsonschema
import pytest

from code_review.adapters.js_base import node_binary

FIXTURE = Path(__file__).parent.parent / "fixtures" / "js-with-known-issues"
SARIF_SCHEMA = Path(__file__).parent.parent.parent / "code_review" / "schemas" / "sarif-2.1.0.json"


def test_eslint_protocol_conformance():
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import Analyzer

    assert isinstance(EslintAdapter(), Analyzer)
    assert EslintAdapter.name == "eslint"
    assert EslintAdapter.node_tool == "eslint"


async def test_eslint_returns_error_when_binary_absent(tmp_path):
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import ReviewRequest

    with patch("code_review.adapters.eslint.node_binary", return_value=None):
        request = ReviewRequest(scope="per-task", diff_range=None,
                                target_paths=(str(tmp_path),),
                                languages=frozenset(), config={})
        output = await EslintAdapter().run(request)
    assert output.status == "error"
    assert "setup.sh" in (output.error or "")


async def test_eslint_empty_target_paths():
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(), languages=frozenset(), config={})
    with patch("code_review.adapters.eslint.node_binary", return_value=Path("/fake/eslint")):
        output = await EslintAdapter().run(request)
    assert output.status == "ok"


async def test_eslint_parses_sarif_stdout():
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import ReviewRequest

    fake_sarif = json.dumps({
        "$schema": "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": "ESLint"}}, "results": []}],
    }).encode()

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=("src/",), languages=frozenset(), config={})
    with (
        patch("code_review.adapters.eslint.node_binary", return_value=Path("/fake/eslint")),
        patch("code_review.adapters.eslint.run_subprocess",
              new=AsyncMock(return_value=SubprocessResult(fake_sarif, b"", 0))),
    ):
        output = await EslintAdapter().run(request)
    assert output.status == "ok"
    assert output.sarif["runs"][0]["tool"]["driver"]["name"] == "ESLint"
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)


@pytest.mark.skipif(
    node_binary("eslint") is None,
    reason="eslint not in node_modules (run scripts/setup.sh)",
)
async def test_eslint_integration_detects_console_log():
    from code_review.adapters.eslint import EslintAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=(str(FIXTURE),),
        languages=frozenset({"javascript", "typescript"}),
        config={},
    )
    output = await EslintAdapter().run(request)
    assert output.status == "ok"
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)
