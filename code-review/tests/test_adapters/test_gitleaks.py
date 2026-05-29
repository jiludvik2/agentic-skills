import json
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

import jsonschema
import pytest

SARIF_SCHEMA = Path(__file__).parent.parent.parent / "code_review" / "schemas" / "sarif-2.1.0.json"


def test_gitleaks_protocol_conformance() -> None:
    from code_review.adapters.gitleaks import GitleaksAdapter
    from code_review.contracts import Analyzer

    assert isinstance(GitleaksAdapter(), Analyzer)
    assert GitleaksAdapter.name == "gitleaks"
    assert GitleaksAdapter.required_binary == "gitleaks"


async def test_gitleaks_returns_error_when_subprocess_fails() -> None:
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.gitleaks import GitleaksAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(".",), languages=frozenset(), config={})
    with patch(
        "code_review.adapters.gitleaks.run_subprocess",
        return_value=SubprocessResult(b"", b"no binary", -1, error="gitleaks not found"),
    ):
        output = await GitleaksAdapter().run(request)
    assert output.status == "error"


async def test_gitleaks_parses_sarif_from_report_file(tmp_path: Path) -> None:
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.gitleaks import GitleaksAdapter
    from code_review.contracts import ReviewRequest

    fake_sarif = {
        "$schema": "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": "gitleaks"}}, "results": []}],
    }

    def fake_run(*args: object, **kwargs: object) -> SubprocessResult:
        for arg in args:
            if str(arg).endswith(".sarif"):
                Path(str(arg)).write_text(json.dumps(fake_sarif))
                break
        return SubprocessResult(b"", b"", 0)

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(".",), languages=frozenset(), config={})
    with patch("code_review.adapters.gitleaks.run_subprocess", new=AsyncMock(side_effect=fake_run)):
        output = await GitleaksAdapter().run(request)
    assert output.status == "ok"
    assert output.sarif["runs"][0]["tool"]["driver"]["name"] == "gitleaks"


@pytest.mark.skipif(shutil.which("gitleaks") is None, reason="gitleaks not installed")
async def test_gitleaks_integration_no_secrets(tmp_path: Path) -> None:
    from code_review.adapters.gitleaks import GitleaksAdapter
    from code_review.contracts import ReviewRequest

    clean_file = tmp_path / "clean.py"
    clean_file.write_text("x = 1\n")
    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(tmp_path),),
                            languages=frozenset(), config={})
    output = await GitleaksAdapter().run(request)
    assert output.status == "ok"
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)
