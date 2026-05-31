"""s1-t1b — cohesion invoke-and-capture contract (ADR-0020).

cohesion migrates from an in-process ``Module.from_file``/``MetricSet`` adapter to a thin
subprocess invocation. cohesion's CLI is ``-d <dir>`` XOR ``-f <files...>`` — these tests
pin the path-shape dispatch, the raw passthrough, and the empty-targets availability
pre-flight.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from code_review.adapters.cohesion_ import CohesionAdapter
from code_review.capture import CaptureOutput
from code_review.contracts import Analyzer, ReviewRequest

FIXTURE = Path(__file__).parent.parent / "fixtures" / "python-with-known-issues"


def _req(paths: tuple[str, ...]) -> ReviewRequest:
    return ReviewRequest(scope="per-task", diff_range=None, target_paths=paths,
                         languages=frozenset(), config={})


def test_cohesion_protocol_conformance() -> None:
    assert isinstance(CohesionAdapter(), Analyzer)
    assert CohesionAdapter.name == "cohesion"


async def test_cohesion_invocation_uses_f_for_files() -> None:
    mock = AsyncMock(return_value=CaptureOutput(tool="cohesion"))
    with patch("code_review.adapters.cohesion_.run_and_capture", new=mock):
        await CohesionAdapter().run(_req(("a.py", "b.py")))
    args = mock.call_args.args
    assert args[0] == "cohesion"                       # capture label
    assert args[1:4] == (sys.executable, "-m", "cohesion")  # pinned-dep module invocation
    # cohesion errors on `-f <dir>`; a file list dispatches to -f
    assert "-f" in args
    assert "a.py" in args and "b.py" in args


async def test_cohesion_invocation_uses_d_for_directory(tmp_path: Path) -> None:
    mock = AsyncMock(return_value=CaptureOutput(tool="cohesion"))
    with patch("code_review.adapters.cohesion_.run_and_capture", new=mock):
        await CohesionAdapter().run(_req((str(tmp_path),)))
    args = mock.call_args.args
    # a single directory target dispatches to -d (cohesion errors on `-f <dir>`)
    assert "-d" in args
    assert str(tmp_path) in args


async def test_cohesion_captures_raw_stdout() -> None:
    cap = CaptureOutput(tool="cohesion", stdout="File: x.py\n  Class: C", exit_code=0)
    with patch("code_review.adapters.cohesion_.run_and_capture", new=AsyncMock(return_value=cap)):
        out = await CohesionAdapter().run(_req(("x.py",)))
    assert out is cap
    assert out.stdout == "File: x.py\n  Class: C"


async def test_cohesion_unavailable_on_empty_targets() -> None:
    out = await CohesionAdapter().run(_req(()))
    assert out.status == "unavailable"


@pytest.mark.integration
async def test_cohesion_integration_reports_cohesion() -> None:
    out = await CohesionAdapter().run(_req((str(FIXTURE / "cohesive.py"),)))
    assert out.status == "ok", out.error
    # the raw report must carry the class and its cohesion breakdown
    assert "LowCohesionService" in out.stdout
