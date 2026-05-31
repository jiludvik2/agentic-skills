"""s1-t2 — jscpd invoke-and-capture contract (ADR-0020) + G1 scope fold-in.

jscpd has no stdout-JSON reporter — its ``json`` reporter writes ``jscpd-report.json`` into
the ``--output`` directory. So the adapter runs it into a TemporaryDirectory and splices the
report file's contents onto ``CaptureOutput.stdout`` (verbatim, no parse).

**G1 (settled here):** jscpd is intentionally JS-scoped (``lang_select._JS_ADAPTERS``;
capabilities languages=[javascript, typescript]), but by default it auto-detects ~150
formats and leaks into HTML/CSS/etc. on real apps. The invocation pins
``--format javascript,jsx,typescript,tsx`` so the captured output covers exactly the
intended JS/TS set and nothing else.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from code_review.adapters.js_base import node_binary
from code_review.adapters.jscpd import JscpdAdapter
from code_review.capture import CaptureOutput
from code_review.contracts import Analyzer, ReviewRequest
from code_review.status import Status

FIXTURE = Path(__file__).parent.parent / "fixtures" / "js-duplication"

# The settled G1 scope (see module docstring): exactly the JS/TS format set.
_JS_FORMAT = "javascript,jsx,typescript,tsx"


def _req(paths: tuple[str, ...]) -> ReviewRequest:
    return ReviewRequest(scope="per-task", diff_range=None, target_paths=paths,
                         languages=frozenset(), config={})


def test_jscpd_protocol_conformance() -> None:
    assert isinstance(JscpdAdapter(), Analyzer)
    assert JscpdAdapter.name == "jscpd"
    assert JscpdAdapter.node_tool == "jscpd"


async def test_jscpd_invocation_pins_json_reporter_and_js_scope(tmp_path: Path) -> None:
    """Pins the report-to-tempdir invocation and the G1 JS/TS ``--format`` scope."""
    (tmp_path / "a.ts").write_text("const x = 1;\n")
    seen: dict[str, object] = {}

    async def fake(*args: str, **kwargs: object) -> CaptureOutput:
        seen["args"] = args
        out_dir = Path(args[args.index("--output") + 1])
        # jscpd treats --output as a directory it writes jscpd-report.json into; it must
        # be a real dir, alive during the call (never /dev/stdout).
        seen["output_is_dir"] = out_dir.is_dir()
        return CaptureOutput(tool="jscpd", exit_code=0)

    with (
        patch("code_review.adapters.jscpd.node_binary", return_value=Path("/fake/jscpd")),
        patch("code_review.adapters.jscpd.has_js_files", return_value=True),
        patch("code_review.adapters.jscpd.run_and_capture", new=fake),
    ):
        await JscpdAdapter().run(_req((str(tmp_path),)))

    args = seen["args"]
    assert isinstance(args, tuple)
    assert args[0] == "jscpd"
    assert "node" in args
    assert args[args.index("--reporters") + 1] == "json"
    assert args[args.index("--format") + 1] == _JS_FORMAT  # G1 scope pin
    assert "--silent" in args
    assert seen["output_is_dir"], "--output must be a real directory, not /dev/stdout"


async def test_jscpd_captures_report_file_as_stdout(tmp_path: Path) -> None:
    """jscpd's payload is the report file; the adapter splices it onto stdout verbatim."""
    (tmp_path / "a.ts").write_text("const x = 1;\n")
    report_json = json.dumps({
        "duplicates": [{"firstFile": {"name": "src/a.ts"}, "secondFile": {"name": "src/b.ts"}}],
        "statistics": {"formats": {"typescript": {}}},
    })

    async def fake(*args: str, **kwargs: object) -> CaptureOutput:
        out_dir = Path(args[args.index("--output") + 1])
        (out_dir / "jscpd-report.json").write_text(report_json)
        return CaptureOutput(tool="jscpd", stdout="", exit_code=0)

    with (
        patch("code_review.adapters.jscpd.node_binary", return_value=Path("/fake/jscpd")),
        patch("code_review.adapters.jscpd.has_js_files", return_value=True),
        patch("code_review.adapters.jscpd.run_and_capture", new=fake),
    ):
        out = await JscpdAdapter().run(_req((str(tmp_path),)))

    assert out.status == "ok"
    assert out.stdout == report_json, "report file contents must land verbatim on stdout"


async def test_jscpd_failure_passes_through_without_report(tmp_path: Path) -> None:
    """When the run failed (no report written), the raw capture passes through unchanged."""
    (tmp_path / "a.ts").write_text("const x = 1;\n")
    cap = CaptureOutput(tool="jscpd", status=Status.ERROR, error="exited 1: boom", exit_code=1)
    with (
        patch("code_review.adapters.jscpd.node_binary", return_value=Path("/fake/jscpd")),
        patch("code_review.adapters.jscpd.has_js_files", return_value=True),
        patch("code_review.adapters.jscpd.run_and_capture", new=AsyncMock(return_value=cap)),
    ):
        out = await JscpdAdapter().run(_req((str(tmp_path),)))
    assert out is cap


async def test_jscpd_missing_report_on_ok_is_error(tmp_path: Path) -> None:
    """jscpd exited 0 but wrote no report (e.g. a silent format mismatch): an empty stdout
    would read downstream as 'found nothing', so the adapter flips it to error rather than
    masking the anomaly."""
    (tmp_path / "a.ts").write_text("const x = 1;\n")
    # Mock returns ok but writes no jscpd-report.json into the --output dir.
    cap = CaptureOutput(tool="jscpd", status=Status.OK, stdout="", exit_code=0)
    with (
        patch("code_review.adapters.jscpd.node_binary", return_value=Path("/fake/jscpd")),
        patch("code_review.adapters.jscpd.has_js_files", return_value=True),
        patch("code_review.adapters.jscpd.run_and_capture", new=AsyncMock(return_value=cap)),
    ):
        out = await JscpdAdapter().run(_req((str(tmp_path),)))
    assert out.status == "error"
    assert "no report" in (out.error or "").lower()


async def test_jscpd_unavailable_when_vendored_binary_absent(tmp_path: Path) -> None:
    with patch("code_review.adapters.jscpd.node_binary", return_value=None):
        out = await JscpdAdapter().run(_req((str(tmp_path),)))
    assert out.status == "unavailable"
    assert "setup.sh" in (out.error or "")


async def test_jscpd_empty_target_paths_unavailable() -> None:
    with patch("code_review.adapters.jscpd.node_binary", return_value=Path("/fake/jscpd")):
        out = await JscpdAdapter().run(_req(()))
    assert out.status == "unavailable"


async def test_jscpd_unavailable_without_js(tmp_path: Path) -> None:
    """jscpd is intentionally JS-scoped — a no-JS target skips cleanly (unavailable) and
    jscpd is never invoked (ADR-0019)."""
    (tmp_path / "app.py").write_text("x = 1\n")
    mock = AsyncMock(return_value=CaptureOutput(tool="jscpd"))
    with (
        patch("code_review.adapters.jscpd.node_binary", return_value=Path("/fake/jscpd")),
        patch("code_review.adapters.jscpd.run_and_capture", new=mock),
    ):
        out = await JscpdAdapter().run(_req((str(tmp_path),)))
    assert out.status == "unavailable", out.error
    assert "javascript" in (out.error or "").lower()
    assert not mock.called, "jscpd must not be invoked when there is no JS to analyse"


@pytest.mark.integration
@pytest.mark.skipif(
    node_binary("jscpd") is None,
    reason="jscpd not in node_modules (run scripts/setup.sh)",
)
async def test_jscpd_integration() -> None:
    """End-to-end on the vendored toolchain: the js-duplication fixture is a genuine clone
    pair, so the captured report must carry a duplication — and, per G1, the detected
    formats must stay within the JS/TS set the ``--format`` pin allows."""
    request = ReviewRequest(
        scope="per-task", diff_range=None, target_paths=(str(FIXTURE),),
        languages=frozenset({"javascript", "typescript"}), config={},
    )
    out = await JscpdAdapter().run(request)
    assert out.status == "ok", out.error
    assert out.stdout, "expected a non-empty raw report capture"
    report = json.loads(out.stdout)
    assert len(report.get("duplicates", [])) >= 1, "expected the clone pair to be reported"
    # G1: the invocation's --format must confine detection to the JS/TS set.
    formats = report.get("statistics", {}).get("formats", {})
    assert set(formats) <= {"javascript", "jsx", "typescript", "tsx"}, formats
