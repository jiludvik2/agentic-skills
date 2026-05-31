"""s0-t0 — CaptureOutput contract + run_and_capture primitive (ADR-0020 / ADR-0019).

Raw-capture rail that runs alongside the existing SARIF path. The primitive captures
stdout/stderr verbatim (no parsing), never raises, and classifies the outcome into the
ADR-0019 status taxonomy (ok | error | timeout | unavailable).
"""

from __future__ import annotations

import dataclasses
import sys

import pytest

from code_review.capture import CaptureOutput, run_and_capture


def test_capture_output_defaults() -> None:
    cap = CaptureOutput(tool="bandit")
    assert cap.tool == "bandit"
    assert cap.status == "ok"
    assert cap.stdout == ""
    assert cap.stderr == ""
    assert cap.exit_code is None
    assert cap.error is None
    assert cap.command == ()
    assert cap.duration_s == 0.0
    # frozen: mutation must raise
    with pytest.raises(dataclasses.FrozenInstanceError):
        cap.status = "error"  # type: ignore[misc]


def test_unavailable_constructor() -> None:
    cap = CaptureOutput.unavailable("eslint", "no config")
    assert cap.tool == "eslint"
    assert cap.status == "unavailable"
    assert cap.error == "no config"
    assert cap.stdout == ""
    assert cap.exit_code is None


async def test_run_and_capture_ok() -> None:
    cap = await run_and_capture("py", sys.executable, "-c", "print('hi')")
    assert cap.status == "ok", cap.error
    assert "hi" in cap.stdout
    assert cap.exit_code == 0
    assert cap.tool == "py"
    # the full argv is recorded for the agent to inspect
    assert cap.command[0] == sys.executable
    assert cap.command[-1] == "print('hi')"


async def test_run_and_capture_tolerated_nonzero() -> None:
    code = "import sys; sys.exit(1)"
    tolerated = await run_and_capture(
        "py", sys.executable, "-c", code, ok_exit_codes=(0, 1)
    )
    assert tolerated.status == "ok", tolerated.error
    assert tolerated.exit_code == 1

    untolerated = await run_and_capture("py", sys.executable, "-c", code)
    assert untolerated.status == "error"
    assert untolerated.exit_code == 1


async def test_run_and_capture_error_has_stderr() -> None:
    code = "import sys; sys.stderr.write('boom-on-stderr'); sys.exit(2)"
    cap = await run_and_capture("py", sys.executable, "-c", code)
    assert cap.status == "error"
    assert cap.exit_code == 2
    assert cap.error is not None
    assert "2" in cap.error
    assert "boom-on-stderr" in cap.error
    # raw stderr is preserved on the capture too
    assert "boom-on-stderr" in cap.stderr


async def test_run_and_capture_timeout() -> None:
    code = "import time; time.sleep(5)"
    cap = await run_and_capture("py", sys.executable, "-c", code, timeout_s=0.5)
    assert cap.status == "timeout"
    assert cap.error is not None


async def test_run_and_capture_missing_binary() -> None:
    # Must classify as error and never raise, even when the binary is absent.
    cap = await run_and_capture("ghost", "this-binary-does-not-exist-polyreview")
    assert cap.status == "error"
    assert cap.error is not None


async def test_run_and_capture_threads_env() -> None:
    # the env dict must reach the child process (semgrep + the JS adapters rely on this)
    code = "import os; print(os.environ.get('POLYREVIEW_ENV_PROBE', 'MISSING'))"
    cap = await run_and_capture(
        "py", sys.executable, "-c", code, env={"POLYREVIEW_ENV_PROBE": "reached"}
    )
    assert cap.status == "ok", cap.error
    assert "reached" in cap.stdout


async def test_run_and_capture_merged_env_preserves_inherited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Adapters pass the documented adapter-style merged env ({**os.environ, ...}); both the
    # injected key and an inherited var must survive (the real semgrep/JS usage shape).
    import os

    monkeypatch.setenv("POLYREVIEW_INHERITED", "from-parent")
    code = (
        "import os; "
        "print(os.environ.get('POLYREVIEW_INHERITED', 'MISSING'), "
        "os.environ.get('POLYREVIEW_INJECTED', 'MISSING'))"
    )
    cap = await run_and_capture(
        "py", sys.executable, "-c", code,
        env={**os.environ, "POLYREVIEW_INJECTED": "added"},
    )
    assert cap.status == "ok", cap.error
    assert "from-parent" in cap.stdout
    assert "added" in cap.stdout


async def test_stdout_preserved_verbatim() -> None:
    # Braces, non-JSON and Unicode must survive untouched — no accidental parsing.
    payload = '{not: "valid json"} ☃ <tag> end'
    cap = await run_and_capture("py", sys.executable, "-c", f"print({payload!r})")
    assert cap.status == "ok", cap.error
    assert cap.stdout.rstrip("\n") == payload
