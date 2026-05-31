"""s1-t1 — pydeps invoke-and-capture contract (ADR-0020).

Pins the load-bearing invocation flags, the raw-stdout passthrough, and the
empty-target availability pre-flight. SARIF/metrics parsing is gone.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from code_review.adapters.pydeps import PydepsAdapter
from code_review.capture import CaptureOutput
from code_review.contracts import Analyzer, ReviewRequest

PACKAGE = Path(__file__).parent.parent.parent / "code_review"


def _req(paths: tuple[str, ...]) -> ReviewRequest:
    return ReviewRequest(scope="per-task", diff_range=None, target_paths=paths,
                         languages=frozenset(), config={})


def test_pydeps_protocol_conformance() -> None:
    assert isinstance(PydepsAdapter(), Analyzer)
    assert PydepsAdapter.name == "pydeps"


async def test_pydeps_invocation_pins_flags() -> None:
    mock = AsyncMock(return_value=CaptureOutput(tool="pydeps"))
    with patch("code_review.adapters.pydeps.run_and_capture", new=mock):
        await PydepsAdapter().run(_req(("pkg/mod.py",)))
    args = mock.call_args.args
    assert args[0] == "pydeps"
    assert "--show-deps" in args
    assert "--noshow" in args
    assert "pkg/mod.py" in args


async def test_pydeps_captures_raw_stdout() -> None:
    cap = CaptureOutput(tool="pydeps", stdout='{"mod": {"imports": []}}', exit_code=0)
    with patch("code_review.adapters.pydeps.run_and_capture", new=AsyncMock(return_value=cap)):
        out = await PydepsAdapter().run(_req(("x.py",)))
    assert out is cap  # ties the concrete return to CaptureOutput (no parsing)
    assert out.stdout == '{"mod": {"imports": []}}'
    assert out.status == "ok"


async def test_pydeps_unavailable_on_empty_targets() -> None:
    out = await PydepsAdapter().run(_req(()))
    assert out.status == "unavailable"
    assert out.stdout == ""


@pytest.mark.integration
async def test_pydeps_integration_real_run() -> None:
    out = await PydepsAdapter().run(_req((str(PACKAGE),)))
    assert out.status == "ok", out.error
    assert out.stdout.strip()  # the dependency map landed on stdout verbatim
