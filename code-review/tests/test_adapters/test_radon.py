"""s1-t1b — radon invoke-and-capture contract (ADR-0020).

radon migrates from an in-process ``cc_visit``/``MetricSet`` adapter to a thin subprocess
invocation. These tests pin the load-bearing ``cc --json`` invocation, the raw
passthrough, and the empty-targets availability pre-flight.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from code_review.adapters.radon import RadonAdapter
from code_review.capture import CaptureOutput
from code_review.contracts import Analyzer, ReviewRequest

FIXTURE = Path(__file__).parent.parent / "fixtures" / "python-with-known-issues"


def _req(paths: tuple[str, ...]) -> ReviewRequest:
    return ReviewRequest(scope="per-task", diff_range=None, target_paths=paths,
                         languages=frozenset(), config={})


def test_radon_protocol_conformance() -> None:
    assert isinstance(RadonAdapter(), Analyzer)
    assert RadonAdapter.name == "radon"


async def test_radon_invocation_pins_flags() -> None:
    mock = AsyncMock(return_value=CaptureOutput(tool="radon"))
    with patch("code_review.adapters.radon.run_and_capture", new=mock):
        await RadonAdapter().run(_req(("a.py", "b.py")))
    args = mock.call_args.args
    assert args[0] == "radon"                       # capture label
    assert args[1:4] == (sys.executable, "-m", "radon")  # pinned-dep module invocation
    # `cc --json` is the load-bearing default: per-file cyclomatic complexity as JSON
    assert "cc" in args and "--json" in args
    assert "a.py" in args and "b.py" in args


async def test_radon_captures_raw_stdout() -> None:
    cap = CaptureOutput(tool="radon", stdout='{"a.py": []}', exit_code=0)
    with patch("code_review.adapters.radon.run_and_capture", new=AsyncMock(return_value=cap)):
        out = await RadonAdapter().run(_req(("a.py",)))
    assert out is cap
    assert out.stdout == '{"a.py": []}'


async def test_radon_unavailable_on_empty_targets() -> None:
    out = await RadonAdapter().run(_req(()))
    assert out.status == "unavailable"


@pytest.mark.integration
async def test_radon_integration_reports_complexity() -> None:
    out = await RadonAdapter().run(_req((str(FIXTURE / "complex.py"),)))
    assert out.status == "ok", out.error
    # the raw cc --json report must carry the high-CC function and its complexity
    assert "classify" in out.stdout
    assert "complexity" in out.stdout
