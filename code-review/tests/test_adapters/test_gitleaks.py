"""s1-t1 — gitleaks invoke-and-capture contract (ADR-0020).

Pins the native-output capture (no --report-path: neither /dev/stdout nor a temp file;
the bundle carries both stdout and stderr), the raw passthrough, and the missing-binary
availability pre-flight.
"""

import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from code_review.adapters.gitleaks import GitleaksAdapter
from code_review.capture import CaptureOutput
from code_review.contracts import Analyzer, ReviewRequest


def _req(paths: tuple[str, ...]) -> ReviewRequest:
    return ReviewRequest(scope="per-task", diff_range=None, target_paths=paths,
                         languages=frozenset(), config={})


def test_gitleaks_protocol_conformance() -> None:
    assert isinstance(GitleaksAdapter(), Analyzer)
    assert GitleaksAdapter.name == "gitleaks"
    assert GitleaksAdapter.required_binary == "gitleaks"


async def test_gitleaks_invocation_pins_flags() -> None:
    mock = AsyncMock(return_value=CaptureOutput(tool="gitleaks"))
    with patch("code_review.adapters.gitleaks.shutil.which", return_value="/usr/bin/gitleaks"), \
         patch("code_review.adapters.gitleaks.run_and_capture", new=mock):
        await GitleaksAdapter().run(_req((".",)))
    args = mock.call_args.args
    assert args[0] == "gitleaks"
    assert "detect" in args
    assert "--source" in args
    assert "--no-git" in args  # scan the working tree, not git history
    # no --report-path: native output captured (no /dev/stdout, no temp file)
    assert "--report-path" not in args
    # leaks-present exit 1 must be tolerated as success
    assert mock.call_args.kwargs["ok_exit_codes"] == (0, 1)


async def test_gitleaks_captures_raw_stdout() -> None:
    cap = CaptureOutput(tool="gitleaks", stdout='{"runs": []}', exit_code=0)
    with patch("code_review.adapters.gitleaks.shutil.which", return_value="/x"), \
         patch("code_review.adapters.gitleaks.run_and_capture", new=AsyncMock(return_value=cap)):
        out = await GitleaksAdapter().run(_req((".",)))
    assert out is cap
    assert out.stdout == '{"runs": []}'


async def test_gitleaks_unavailable_when_binary_absent() -> None:
    with patch("code_review.adapters.gitleaks.shutil.which", return_value=None):
        out = await GitleaksAdapter().run(_req((".",)))
    assert out.status == "unavailable"
    assert out.error is not None


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("gitleaks") is None, reason="gitleaks not installed")
async def test_gitleaks_integration_detects_secret(tmp_path: Path) -> None:
    # A clean tree exits 0; planting a high-entropy AWS-style key makes gitleaks report a
    # leak (exit 1, tolerated) — the raw capture must carry the finding (coverage discipline).
    (tmp_path / "leak.py").write_text(
        'aws_secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"\n'
    )
    out = await GitleaksAdapter().run(_req((str(tmp_path),)))
    assert out.status == "ok", out.error
    blob = out.stdout + out.stderr
    assert "leak" in blob.lower() or "secret" in blob.lower()
