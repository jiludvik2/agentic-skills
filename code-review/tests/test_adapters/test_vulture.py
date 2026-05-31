"""s1-t1b — vulture invoke-and-capture contract (ADR-0020).

vulture migrates from an in-process ``Vulture().scavenge``/``_to_sarif`` adapter to a thin
subprocess invocation. These tests pin the invocation, the tolerated dead-code exit code,
the raw passthrough, and the empty-targets availability pre-flight.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from code_review.adapters.vulture import VultureAdapter
from code_review.capture import CaptureOutput
from code_review.contracts import Analyzer, ReviewRequest

FIXTURE = Path(__file__).parent.parent / "fixtures" / "python-with-known-issues"


def _req(paths: tuple[str, ...]) -> ReviewRequest:
    return ReviewRequest(scope="per-task", diff_range=None, target_paths=paths,
                         languages=frozenset(), config={})


def test_vulture_protocol_conformance() -> None:
    assert isinstance(VultureAdapter(), Analyzer)
    assert VultureAdapter.name == "vulture"


async def test_vulture_invocation_pins_flags() -> None:
    mock = AsyncMock(return_value=CaptureOutput(tool="vulture"))
    with patch("code_review.adapters.vulture.run_and_capture", new=mock):
        await VultureAdapter().run(_req(("a.py", "b.py")))
    args = mock.call_args.args
    assert args[0] == "vulture"                       # capture label
    assert args[1:4] == (sys.executable, "-m", "vulture")  # pinned-dep module invocation
    assert "a.py" in args and "b.py" in args
    # vulture exits 3 (ExitCode.DeadCode) when it finds dead code, 0 when clean — both are
    # success. Exit 1/2 are real errors (InvalidInput / InvalidCmdlineArguments).
    assert mock.call_args.kwargs["ok_exit_codes"] == (0, 3)


async def test_vulture_captures_raw_stdout() -> None:
    cap = CaptureOutput(tool="vulture", stdout="x.py:1: unused function 'f'", exit_code=3)
    with patch("code_review.adapters.vulture.run_and_capture", new=AsyncMock(return_value=cap)):
        out = await VultureAdapter().run(_req(("x.py",)))
    assert out is cap
    assert out.stdout == "x.py:1: unused function 'f'"


async def test_vulture_unavailable_on_empty_targets() -> None:
    out = await VultureAdapter().run(_req(()))
    assert out.status == "unavailable"


@pytest.mark.integration
async def test_vulture_integration_flags_dead_code() -> None:
    out = await VultureAdapter().run(_req((str(FIXTURE / "dead.py"),)))
    assert out.status == "ok", out.error
    # the raw report must carry the unused function (exit 3 tolerated as success)
    assert "never_called" in out.stdout
    assert "unused" in out.stdout
