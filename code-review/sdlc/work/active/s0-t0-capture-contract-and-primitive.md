---
id: s0-t0-capture-contract-and-primitive
kind: task
project: code-review
status: active
parent: s0-contract-inversion-and-bundle
sources: [adr-0020-thin-invocation-runner.md, adr-0019-analyzer-unavailable-vs-error.md]
created: 2026-05-30
updated: 2026-05-30
tags: [contract, capture, adr-0019]
---

# Task s0-t0 — CaptureOutput contract + run_and_capture primitive

## Outcome

A raw-capture output type (`CaptureOutput`) and a `run_and_capture` primitive that runs a
subprocess and classifies its outcome into the ADR-0019 status taxonomy — verbatim
capture, no parsing — both additive (the existing `AnalyzerOutput`/SARIF path untouched).

## Design

New module `code_review/capture.py` (keeps the additive boundary clean; s1 migrates
adapters onto it):

```python
@dataclass(frozen=True)
class CaptureOutput:
    tool: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    status: str = "ok"            # ok | error | timeout | unavailable (ADR-0019)
    error: str | None = None
    command: tuple[str, ...] = ()
    duration_s: float = 0.0

    @staticmethod
    def unavailable(tool: str, reason: str) -> "CaptureOutput": ...

async def run_and_capture(
    tool: str, *cmd: str, timeout_s: float = 60.0,
    cwd: str | None = None, ok_exit_codes: tuple[int, ...] = (0,),
) -> CaptureOutput: ...
```

- Wraps `code_review.adapters.base.run_subprocess`; decodes stdout/stderr with
  `errors="replace"`; stores them **verbatim** (no JSON parse, no normalisation).
- Status mapping: spawn error (`result.error`) → `error`; `result.timed_out` → `timeout`;
  `returncode in ok_exit_codes` → `ok`; otherwise → `error` (stderr summarised into
  `error`). `unavailable` is **not** produced here (adapter pre-flight decides it in s1).
- `ok_exit_codes` is the per-tool tolerated set (e.g. bandit tolerates `(0, 1)`).
- Never raises; always returns a `CaptureOutput`. Records `command` and `duration_s`.

## Acceptance criteria

- `CaptureOutput` is a frozen dataclass with the fields above and sensible defaults.
- `CaptureOutput.unavailable(tool, reason)` → `status="unavailable"`, empty stdout,
  `error == reason`, `exit_code is None`.
- `run_and_capture`:
  - tolerated exit (default `0`, or any in `ok_exit_codes`) → `status="ok"`, `stdout`
    captured verbatim, `exit_code` set.
  - untolerated exit → `status="error"`, `error` carries the exit code + stderr.
  - timeout → `status="timeout"`, `error` set.
  - missing binary / spawn failure → `status="error"`, `error` set (does not raise).
  - `stdout`/`stderr` are preserved byte-for-byte (modulo `errors="replace"` decode); no
    parsing or transformation occurs.
- No existing module imports change; the SARIF path and all current tests stay green.

## Test specification (write first, confirm RED)

`tests/test_capture.py` (new), using `pytest`/`pytest.mark.asyncio` as the repo does, run
via `uv run pytest`:

1. `test_capture_output_defaults` — construct with `tool` only; assert defaults
   (`status=="ok"`, empty stdout/stderr, `command==()`, frozen — assigning raises).
2. `test_unavailable_constructor` — `CaptureOutput.unavailable("eslint", "no config")` →
   status/`error`/empty-stdout/`exit_code is None` as specified.
3. `test_run_and_capture_ok` — run `python -c "print('hi')"`; status `ok`, `stdout`
   contains `hi`, `exit_code==0`, `command` recorded.
4. `test_run_and_capture_tolerated_nonzero` — a command exiting `1` with
   `ok_exit_codes=(0,1)` → `ok`; with default `(0,)` → `error`.
5. `test_run_and_capture_error_has_stderr` — a command writing to stderr and exiting `2`
   → `error`, `error` contains the code and stderr text.
6. `test_run_and_capture_timeout` — a `sleep`-style command with `timeout_s` small →
   `timeout`.
7. `test_run_and_capture_missing_binary` — invoke a non-existent binary → `error`, no
   exception raised.
8. `test_stdout_preserved_verbatim` — output containing braces/non-JSON/Unicode is
   captured unchanged (guards against any accidental parsing).

## Notes

- Mirror the existing async test style in `tests/test_adapters/` (e.g. `test_bandit.py`).
- `unavailable` here is the eventual replacement for `js_base.js_unavailable` and the
  `empty_sarif(...)`-based unavailable pattern; those are migrated/removed in s1.
