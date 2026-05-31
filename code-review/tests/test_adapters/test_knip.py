"""s1-t2 — knip invoke-and-capture contract (ADR-0020).

Pins the load-bearing invocation (``--reporter json`` so unused-export findings land on
stdout; cwd at the project dir because knip reads ./package.json from cwd), the raw stdout
passthrough (no parse / no _to_sarif), and the availability pre-flights (missing binary →
unavailable; no package.json → unavailable, ADR-0019).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from code_review.adapters.js_base import node_binary
from code_review.adapters.knip import KnipAdapter
from code_review.capture import CaptureOutput
from code_review.contracts import Analyzer, ReviewRequest

FIXTURE = Path(__file__).parent.parent / "fixtures" / "js-with-known-issues"


def _req(paths: tuple[str, ...]) -> ReviewRequest:
    return ReviewRequest(scope="per-task", diff_range=None, target_paths=paths,
                         languages=frozenset(), config={})


def test_knip_protocol_conformance() -> None:
    assert isinstance(KnipAdapter(), Analyzer)
    assert KnipAdapter.name == "knip"
    assert KnipAdapter.node_tool == "knip"


async def test_knip_invocation_pins_json_reporter_and_cwd(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}")
    mock = AsyncMock(return_value=CaptureOutput(tool="knip", stdout="{}", exit_code=0))
    with (
        patch("code_review.adapters.knip.node_binary", return_value=Path("/fake/knip")),
        patch("code_review.adapters.knip.run_and_capture", new=mock),
    ):
        await KnipAdapter().run(_req((str(tmp_path),)))
    args = mock.call_args.args
    kwargs = mock.call_args.kwargs
    assert args[0] == "knip"
    assert "node" in args
    assert args[args.index("--reporter") + 1] == "json"
    # knip reads ./package.json from its cwd, so cwd must be anchored at the project dir.
    assert kwargs["cwd"] == str(tmp_path)
    # knip exits 0 (clean) or 1 (findings) — both tolerated.
    assert kwargs.get("ok_exit_codes") == (0, 1)


async def test_knip_captures_raw_stdout(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}")
    cap = CaptureOutput(tool="knip", stdout='{"files": [], "exports": []}', exit_code=0)
    with (
        patch("code_review.adapters.knip.node_binary", return_value=Path("/fake/knip")),
        patch("code_review.adapters.knip.run_and_capture", new=AsyncMock(return_value=cap)),
    ):
        out = await KnipAdapter().run(_req((str(tmp_path),)))
    assert out is cap


async def test_knip_unavailable_when_vendored_binary_absent(tmp_path: Path) -> None:
    with patch("code_review.adapters.knip.node_binary", return_value=None):
        out = await KnipAdapter().run(_req((str(tmp_path),)))
    assert out.status == "unavailable"
    assert "setup.sh" in (out.error or "")


async def test_knip_empty_target_paths_unavailable() -> None:
    with patch("code_review.adapters.knip.node_binary", return_value=Path("/fake/knip")):
        out = await KnipAdapter().run(_req(()))
    assert out.status == "unavailable"


async def test_knip_unavailable_without_package_json(tmp_path: Path) -> None:
    """A Python-only target (no package.json) is 'nothing knip can run' — unavailable, and
    knip is never invoked (ADR-0019)."""
    (tmp_path / "app.py").write_text("x = 1\n")
    mock = AsyncMock(return_value=CaptureOutput(tool="knip"))
    with (
        patch("code_review.adapters.knip.node_binary", return_value=Path("/fake/knip")),
        patch("code_review.adapters.knip.run_and_capture", new=mock),
    ):
        out = await KnipAdapter().run(_req((str(tmp_path),)))
    assert out.status == "unavailable", out.error
    assert "package.json" in (out.error or "").lower()
    assert not mock.called, "knip must not be invoked when there is no package.json"


@pytest.mark.integration
@pytest.mark.skipif(
    node_binary("knip") is None,
    reason="knip not in node_modules (run scripts/setup.sh)",
)
async def test_knip_integration() -> None:
    request = ReviewRequest(
        scope="per-task", diff_range=None, target_paths=(str(FIXTURE),),
        languages=frozenset({"javascript", "typescript"}), config={},
    )
    out = await KnipAdapter().run(request)
    # The fixture ships no top-level package.json, so the guard returns `unavailable`
    # (a clean skip) deterministically — before knip is invoked.
    assert out.status == "unavailable", out.error
    assert "package.json" in (out.error or "").lower()
