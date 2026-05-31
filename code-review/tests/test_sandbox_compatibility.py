"""
Verify adapters do not litter the working directory with temp files.

After the thin-runner migration (ADR-0020) gitleaks captures native output and trivy
writes SARIF to stdout — neither creates any scratch file. semgrep still redirects its
log/settings into a ``tempfile.TemporaryDirectory`` under ``$TMPDIR``, never the CWD. The
adapters invoke through ``run_and_capture`` (patched here), so the CWD must stay untouched.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from code_review.capture import CaptureOutput


@pytest.mark.asyncio
async def test_gitleaks_no_temp_files_in_cwd(tmp_path: Path) -> None:
    """GitleaksAdapter must not create any files in CWD."""
    from code_review.adapters.gitleaks import GitleaksAdapter
    from code_review.contracts import ReviewRequest

    cap = CaptureOutput(tool="gitleaks", stdout="", exit_code=0)
    before = set(tmp_path.iterdir())
    with (
        patch("code_review.adapters.gitleaks.shutil.which", return_value="/x"),
        patch("code_review.adapters.gitleaks.run_and_capture",
              new=AsyncMock(return_value=cap)),
        patch("os.getcwd", return_value=str(tmp_path)),
    ):
        request = ReviewRequest(
            scope="per-task", diff_range=None, target_paths=(".",),
            languages=frozenset(), config={},
        )
        output = await GitleaksAdapter().run(request)

    after = set(tmp_path.iterdir())
    assert before == after, f"Unexpected files in CWD: {after - before}"
    assert output.status == "ok"


@pytest.mark.asyncio
async def test_trivy_no_temp_files_in_cwd(tmp_path: Path) -> None:
    """TrivyAdapter must not create any files in CWD."""
    from code_review.adapters.trivy import TrivyAdapter
    from code_review.contracts import ReviewRequest

    cache_dir = tmp_path / "trivy-db"
    cache_dir.mkdir()
    cap = CaptureOutput(tool="trivy", stdout='{"runs":[]}', exit_code=0)
    before = set(tmp_path.iterdir())
    with (
        patch("code_review.adapters.trivy.shutil.which", return_value="/x"),
        patch("code_review.adapters.trivy._trivy_cache_dir", return_value=cache_dir),
        patch("code_review.adapters.trivy.run_and_capture",
              new=AsyncMock(return_value=cap)),
        patch("os.getcwd", return_value=str(tmp_path)),
    ):
        request = ReviewRequest(
            scope="per-task", diff_range=None, target_paths=(str(tmp_path),),
            languages=frozenset(), config={},
        )
        output = await TrivyAdapter().run(request)

    after = set(tmp_path.iterdir())
    assert {p for p in after if p != cache_dir} == {p for p in before if p != cache_dir}, \
        f"Unexpected files in CWD: {after - before}"
    assert output.status == "ok"


@pytest.mark.asyncio
async def test_schemathesis_sandbox_blocked_network_names_allowed_domains() -> None:
    """When the network rejects the Schemathesis target, error must name sandbox.allowedDomains."""
    from unittest.mock import patch

    from code_review.adapters.schemathesis_ import SchemathesisAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(
        scope="story-level",
        diff_range=None,
        target_paths=(),
        languages=frozenset(),
        config={
            "contract_testing": {
                "api": {
                    "spec_url": "http://localhost:8080/openapi.json",
                    "base_url": "http://localhost:8080",
                    "timeout_s": 5,
                }
            }
        },
    )

    with patch(
        "schemathesis.openapi.from_url",
        side_effect=OSError("Network access blocked by sandbox"),
    ):
        output = await SchemathesisAdapter().run(request)

    assert output.status == "error"
    assert output.error is not None
    assert "sandbox.allowedDomains" in output.error


@pytest.mark.asyncio
async def test_semgrep_no_temp_files_in_cwd(tmp_path: Path) -> None:
    """SemgrepAdapter must not create any files in CWD."""
    from code_review.adapters.semgrep import SemgrepAdapter
    from code_review.contracts import ReviewRequest

    cap = CaptureOutput(tool="semgrep", stdout='{"runs":[]}', exit_code=0)

    # A real rules dir so the adapter proceeds past its pre-flight to run_and_capture
    # (fail-loud otherwise, per ADR-0016); kept in a sibling dir, not the CWD under test.
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    cwd = tmp_path / "cwd"
    cwd.mkdir()

    before = set(cwd.iterdir())
    with (
        patch("code_review.adapters.semgrep.shutil.which", return_value="/x"),
        patch("code_review.adapters.semgrep.run_and_capture",
              new=AsyncMock(return_value=cap)),
        patch("os.getcwd", return_value=str(cwd)),
    ):
        request = ReviewRequest(
            scope="per-task",
            diff_range=None,
            target_paths=(".",),
            languages=frozenset({"python"}),
            config={"semgrep_rules": str(rules_dir)},
        )
        output = await SemgrepAdapter().run(request)

    after = set(cwd.iterdir())
    assert before == after, f"Unexpected files in CWD: {after - before}"
    assert output.status == "ok"
