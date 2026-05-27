"""
Verify adapters do not litter the working directory with temp files.
Binary adapters (gitleaks, trivy, semgrep) use tempfile.TemporaryDirectory
so their scratch files land in $TMPDIR and are auto-cleaned — never in CWD.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_gitleaks_no_temp_files_in_cwd(tmp_path: Path) -> None:
    """GitleaksAdapter must not create any files in CWD."""
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.gitleaks import GitleaksAdapter
    from code_review.contracts import ReviewRequest

    async def fake_run(*args: object, **kwargs: object) -> SubprocessResult:
        for arg in args:
            s = str(arg)
            if s.endswith(".sarif"):
                Path(s).write_text('{"version":"2.1.0","$schema":"x","runs":[]}')
                break
        return SubprocessResult(b"", b"", 0)

    before = set(tmp_path.iterdir())
    with (
        patch("code_review.adapters.gitleaks.run_subprocess", side_effect=fake_run),
        patch("os.getcwd", return_value=str(tmp_path)),
    ):
        request = ReviewRequest(
            scope="per-task",
            diff_range=None,
            target_paths=(".",),
            languages=frozenset(),
            config={},
        )
        output = await GitleaksAdapter().run(request)

    after = set(tmp_path.iterdir())
    assert before == after, f"Unexpected files in CWD: {after - before}"
    assert output.status == "ok"


@pytest.mark.asyncio
async def test_trivy_no_temp_files_in_cwd(tmp_path: Path) -> None:
    """TrivyAdapter must not create any files in CWD."""
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.trivy import TrivyAdapter
    from code_review.contracts import ReviewRequest

    cache_dir = tmp_path / "trivy-db"
    cache_dir.mkdir()

    async def fake_run(*args: object, **kwargs: object) -> SubprocessResult:
        for i, arg in enumerate(args):
            if str(arg) == "--output" and i + 1 < len(args):
                Path(str(args[i + 1])).write_text(
                    '{"version":"2.1.0","$schema":"x","runs":[]}'
                )
                break
        return SubprocessResult(b"", b"", 0)

    before = set(tmp_path.iterdir())
    with (
        patch("code_review.adapters.trivy._TRIVY_CACHE_DIR", cache_dir),
        patch("code_review.adapters.trivy.run_subprocess", side_effect=fake_run),
        patch("os.getcwd", return_value=str(tmp_path)),
    ):
        request = ReviewRequest(
            scope="per-task",
            diff_range=None,
            target_paths=(str(tmp_path),),
            languages=frozenset(),
            config={},
        )
        output = await TrivyAdapter().run(request)

    after = set(tmp_path.iterdir())
    assert {p for p in after if p != cache_dir} == {p for p in before if p != cache_dir}, \
        f"Unexpected files in CWD: {after - before}"
    assert output.status == "ok"


@pytest.mark.asyncio
async def test_semgrep_no_temp_files_in_cwd(tmp_path: Path) -> None:
    """SemgrepAdapter must not create any files in CWD."""
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.semgrep import SemgrepAdapter
    from code_review.contracts import ReviewRequest

    fake_sarif = (
        '{"version":"2.1.0","$schema":"x","runs":[{"tool":{"driver":{"name":"semgrep"}},"results":[]}]}'
    )

    def fake_run(*args: object, **kwargs: object) -> SubprocessResult:
        return SubprocessResult(fake_sarif.encode(), b"", 0)

    before = set(tmp_path.iterdir())
    with (
        patch("code_review.adapters.semgrep.run_subprocess", side_effect=fake_run),
        patch("os.getcwd", return_value=str(tmp_path)),
    ):
        request = ReviewRequest(
            scope="per-task",
            diff_range=None,
            target_paths=(".",),
            languages=frozenset({"python"}),
            config={"semgrep_rules": "/nonexistent"},
        )
        output = await SemgrepAdapter().run(request)

    after = set(tmp_path.iterdir())
    assert before == after, f"Unexpected files in CWD: {after - before}"
    assert output.status == "ok"
