"""Raw-capture rail for the thin invocation runner (ADR-0020).

``CaptureOutput`` is the raw, un-normalised result of running one analyzer tool: its
stdout/stderr captured **verbatim** (no JSON parse, no SARIF normalisation) plus the
outcome classified into the ADR-0019 status taxonomy. ``run_and_capture`` wraps
``adapters.base.run_subprocess`` to produce one.

This module is purely additive (s0): it runs alongside the existing
``AnalyzerOutput``/SARIF path. s1 migrates the adapters onto it and deletes the
normalisation layer; the optional rename to ``AnalyzerOutput`` also lands then.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from code_review.adapters.base import run_subprocess
from code_review.status import Status


@dataclass(frozen=True)
class CaptureOutput:
    """The raw outcome of invoking one tool. ``stdout``/``stderr`` are verbatim."""

    tool: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    status: Status = Status.OK  # ADR-0019 taxonomy (see code_review.status)
    error: str | None = None
    command: tuple[str, ...] = ()
    duration_s: float = 0.0

    @staticmethod
    def unavailable(tool: str, reason: str) -> CaptureOutput:
        """Pre-flight 'tool not runnable' result (e.g. missing binary/config).

        Empty stdout, no exit code; the reason is carried in ``error``.
        """
        return CaptureOutput(
            tool=tool,
            status=Status.UNAVAILABLE,
            error=reason,
            exit_code=None,
        )


async def run_and_capture(
    tool: str,
    *cmd: str,
    timeout_s: float = 60.0,
    cwd: str | None = None,
    ok_exit_codes: tuple[int, ...] = (0,),
) -> CaptureOutput:
    """Run ``cmd`` and return a ``CaptureOutput`` — verbatim, never raising.

    Status mapping: spawn failure → ``error``; timeout → ``timeout``; exit code in
    ``ok_exit_codes`` → ``ok``; any other exit code → ``error`` (the code and stderr
    are summarised into ``error``). stdout/stderr are decoded with ``errors="replace"``
    and otherwise left untouched — no parsing or normalisation.
    """
    started = time.monotonic()
    result = await run_subprocess(*cmd, timeout_s=timeout_s, cwd=cwd)
    duration_s = time.monotonic() - started

    stdout = result.stdout.decode(errors="replace")
    stderr = result.stderr.decode(errors="replace")

    status: Status
    error: str | None
    exit_code: int | None
    if result.error is not None:
        # create_subprocess_exec / communicate raised (e.g. missing binary).
        status, error, exit_code = Status.ERROR, result.error, None
    elif result.timed_out:
        status = Status.TIMEOUT
        error = f"timed out after {timeout_s:g}s"
        exit_code = None
    elif result.returncode in ok_exit_codes:
        status, error, exit_code = Status.OK, None, result.returncode
    else:
        exit_code = result.returncode
        status = Status.ERROR
        summary = stderr.strip() or "(no stderr)"
        error = f"exited {exit_code}: {summary}"

    return CaptureOutput(
        tool=tool,
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        status=status,
        error=error,
        command=tuple(cmd),
        duration_s=duration_s,
    )
