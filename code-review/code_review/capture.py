"""Raw-capture rail for the thin invocation runner (ADR-0020).

``CaptureOutput`` is the raw, un-normalised result of running one analyzer tool: its
stdout/stderr captured **verbatim** (no JSON parse, no SARIF normalisation) plus the
outcome classified into the ADR-0019 status taxonomy. ``run_and_capture`` wraps
``adapters.base.run_subprocess`` to produce one.

This is the analyzer layer's sole output type: every adapter returns a ``CaptureOutput``
and the CLI collects them into a ``ReviewBundle`` (ADR-0020). The former SARIF
normalisation layer was deleted in s1-t3.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

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
    env: dict[str, str] | None = None,
    ok_exit_codes: tuple[int, ...] = (0,),
) -> CaptureOutput:
    """Run ``cmd`` and return a ``CaptureOutput`` — verbatim, never raising.

    ``env``, when given, is the full environment for the child (adapters that need it,
    e.g. semgrep's settings-file redirect or the JS adapters' ``NODE_PATH``, pass a
    merged ``{**os.environ, ...}``). Status mapping: spawn failure → ``error``; timeout →
    ``timeout``; exit code in ``ok_exit_codes`` → ``ok``; any other exit code → ``error``
    (the code and stderr are summarised into ``error``). stdout/stderr are decoded with
    ``errors="replace"`` and otherwise left untouched — no parsing or normalisation.
    """
    # Imported lazily: adapters import this module, and ``adapters.base`` lives behind the
    # ``code_review.adapters`` package init (which imports every adapter) — a top-level
    # import here would close that cycle. By call time the package is fully initialised.
    from code_review.adapters.base import run_subprocess

    started = time.monotonic()
    result = await run_subprocess(*cmd, timeout_s=timeout_s, cwd=cwd, env=env)
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
