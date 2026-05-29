import json
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

import jsonschema
import pytest

SARIF_SCHEMA = Path(__file__).parent.parent.parent / "code_review" / "schemas" / "sarif-2.1.0.json"


def test_trivy_protocol_conformance() -> None:
    from code_review.adapters.trivy import TrivyAdapter
    from code_review.contracts import Analyzer

    assert isinstance(TrivyAdapter(), Analyzer)
    assert TrivyAdapter.name == "trivy"
    assert TrivyAdapter.required_binary == "trivy"


async def test_trivy_returns_error_when_cache_absent(tmp_path: Path) -> None:
    from code_review.adapters.trivy import TrivyAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(tmp_path),),
                            languages=frozenset(), config={})
    with patch(
        "code_review.adapters.trivy._trivy_cache_dir",
        return_value=tmp_path / "nonexistent",
    ):
        output = await TrivyAdapter().run(request)
    assert output.status == "error"
    assert "setup.sh" in (output.error or "")


async def test_trivy_parses_sarif_from_report_file(tmp_path: Path) -> None:
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.trivy import TrivyAdapter
    from code_review.contracts import ReviewRequest

    fake_sarif = {
        "$schema": "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": "trivy"}}, "results": []}],
    }

    def fake_run(*args: object, **kwargs: object) -> SubprocessResult:
        idx = list(args).index("--output")
        Path(str(args[idx + 1])).write_text(json.dumps(fake_sarif))
        return SubprocessResult(b"", b"", 0)

    cache_dir = tmp_path / "trivy-db"
    cache_dir.mkdir()
    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(tmp_path),),
                            languages=frozenset(), config={})
    with (
        patch("code_review.adapters.trivy._trivy_cache_dir", return_value=cache_dir),
        patch("code_review.adapters.trivy.run_subprocess", new=AsyncMock(side_effect=fake_run)),
    ):
        output = await TrivyAdapter().run(request)
    assert output.status == "ok"


@pytest.mark.skipif(shutil.which("trivy") is None, reason="trivy not installed")
async def test_trivy_integration(tmp_path: Path) -> None:
    from code_review.adapters.trivy import TrivyAdapter
    from code_review.contracts import ReviewRequest
    from code_review.paths import trivy_cache_dir

    if not trivy_cache_dir().exists():
        pytest.skip("trivy DB not pre-fetched (run scripts/setup.sh)")
    clean_file = tmp_path / "main.py"
    clean_file.write_text("x = 1\n")
    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(tmp_path),),
                            languages=frozenset(), config={})
    output = await TrivyAdapter().run(request)
    assert output.status == "ok"
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)
