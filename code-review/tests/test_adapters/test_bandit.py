"""s1-t1 — bandit invoke-and-capture contract (ADR-0020).

Pins --quiet (F3) and the JSON-on-stdout invocation, the raw passthrough, the
tolerated-issue exit code, and the empty-target availability pre-flight.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from code_review.adapters.bandit import BanditAdapter
from code_review.capture import CaptureOutput
from code_review.contracts import Analyzer, ReviewRequest


def _req(paths: tuple[str, ...]) -> ReviewRequest:
    return ReviewRequest(scope="per-task", diff_range=None, target_paths=paths,
                         languages=frozenset(), config={})


def test_bandit_protocol_conformance() -> None:
    assert isinstance(BanditAdapter(), Analyzer)
    assert BanditAdapter.name == "bandit"


async def test_bandit_invocation_pins_flags() -> None:
    mock = AsyncMock(return_value=CaptureOutput(tool="bandit"))
    with patch("code_review.adapters.bandit.run_and_capture", new=mock):
        await BanditAdapter().run(_req(("a.py", "b.py")))
    args = mock.call_args.args
    assert args[0] == "bandit"
    assert "--quiet" in args  # F3: suppress the progress bar at source
    assert "json" in args
    assert "a.py" in args and "b.py" in args
    # bandit exits 1 when it reports issues — that must be tolerated as success
    assert mock.call_args.kwargs["ok_exit_codes"] == (0, 1)


async def test_bandit_captures_raw_stdout() -> None:
    cap = CaptureOutput(tool="bandit", stdout='{"results": []}', exit_code=1)
    with patch("code_review.adapters.bandit.run_and_capture", new=AsyncMock(return_value=cap)):
        out = await BanditAdapter().run(_req(("x.py",)))
    assert out is cap
    assert out.stdout == '{"results": []}'


async def test_bandit_unavailable_on_empty_targets() -> None:
    out = await BanditAdapter().run(_req(()))
    assert out.status == "unavailable"


@pytest.mark.integration
async def test_bandit_integration_flags_insecure_eval(tmp_path: Path) -> None:
    (tmp_path / "insecure.py").write_text("def f(x):\n    return eval(x)\n")
    out = await BanditAdapter().run(_req((str(tmp_path),)))
    assert out.status == "ok", out.error
    # B307 is bandit's eval rule — the raw report must carry the finding
    assert "B307" in out.stdout
