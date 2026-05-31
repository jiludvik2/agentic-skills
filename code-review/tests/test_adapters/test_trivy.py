"""s1-t1 — trivy invoke-and-capture contract (ADR-0020).

Pins the offline invocation (--skip-db-update/--offline-scan) and the SARIF-to-stdout
redirect, the raw passthrough, and the availability pre-flights (missing binary, missing
provisioned DB → unavailable per ADR-0019, no longer error).
"""

import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from code_review.adapters.trivy import TrivyAdapter
from code_review.capture import CaptureOutput
from code_review.contracts import Analyzer, ReviewRequest
from code_review.paths import trivy_cache_dir


def _req(paths: tuple[str, ...]) -> ReviewRequest:
    return ReviewRequest(scope="per-task", diff_range=None, target_paths=paths,
                         languages=frozenset(), config={})


def test_trivy_protocol_conformance() -> None:
    assert isinstance(TrivyAdapter(), Analyzer)
    assert TrivyAdapter.name == "trivy"
    assert TrivyAdapter.required_binary == "trivy"


async def test_trivy_invocation_pins_offline_flags(tmp_path: Path) -> None:
    cache_dir = tmp_path / "trivy-db"
    cache_dir.mkdir()
    mock = AsyncMock(return_value=CaptureOutput(tool="trivy"))
    with patch("code_review.adapters.trivy.shutil.which", return_value="/usr/bin/trivy"), \
         patch("code_review.adapters.trivy._trivy_cache_dir", return_value=cache_dir), \
         patch("code_review.adapters.trivy.run_and_capture", new=mock):
        await TrivyAdapter().run(_req((str(tmp_path),)))
    args = mock.call_args.args
    assert args[0] == "trivy"
    assert "fs" in args
    assert "--skip-db-update" in args and "--offline-scan" in args  # offline, no egress
    assert args[args.index("--format") + 1] == "sarif"
    assert "--output" not in args  # SARIF written to stdout natively (no /dev/stdout)


async def test_trivy_captures_raw_stdout(tmp_path: Path) -> None:
    cache_dir = tmp_path / "trivy-db"
    cache_dir.mkdir()
    cap = CaptureOutput(tool="trivy", stdout='{"runs": []}', exit_code=0)
    with patch("code_review.adapters.trivy.shutil.which", return_value="/x"), \
         patch("code_review.adapters.trivy._trivy_cache_dir", return_value=cache_dir), \
         patch("code_review.adapters.trivy.run_and_capture", new=AsyncMock(return_value=cap)):
        out = await TrivyAdapter().run(_req((str(tmp_path),)))
    assert out is cap


async def test_trivy_unavailable_when_binary_absent(tmp_path: Path) -> None:
    with patch("code_review.adapters.trivy.shutil.which", return_value=None):
        out = await TrivyAdapter().run(_req((str(tmp_path),)))
    assert out.status == "unavailable"


async def test_trivy_unavailable_when_db_absent(tmp_path: Path) -> None:
    with patch("code_review.adapters.trivy.shutil.which", return_value="/x"), \
         patch("code_review.adapters.trivy._trivy_cache_dir", return_value=tmp_path / "nope"):
        out = await TrivyAdapter().run(_req((str(tmp_path),)))
    assert out.status == "unavailable"
    assert "setup.sh" in (out.error or "")


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("trivy") is None, reason="trivy not installed")
async def test_trivy_integration(tmp_path: Path) -> None:
    if not trivy_cache_dir().exists():
        pytest.skip("trivy DB not pre-fetched (run scripts/setup.sh)")
    (tmp_path / "main.py").write_text("x = 1\n")
    out = await TrivyAdapter().run(_req((str(tmp_path),)))
    assert out.status == "ok", out.error
    assert "runs" in out.stdout
