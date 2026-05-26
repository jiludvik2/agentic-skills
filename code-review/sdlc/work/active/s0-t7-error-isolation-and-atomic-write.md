---
id: s0-t7-error-isolation-and-atomic-write
kind: task
project: code-review
status: active
parent: s0-analyzer-facade-and-two-adapters
created: 2026-05-26
updated: 2026-05-26
---

# s0-t7 — Error isolation, atomic write, and CWD output guard

## Outcome

An adapter whose binary is missing produces `status="error"` without crashing the CLI or suppressing sibling adapters' output. `--output` writes via `.tmp`-then-rename (both files in the same directory, so rename is atomic). Output paths outside CWD are rejected before analysis begins with a clear sandbox explanation.

## Acceptance Criteria

- When `semgrep` is absent and `radon` is available, the CLI exits non-zero; consolidated output contains `analyzers.semgrep.status == "error"` with a non-empty `error` string; `analyzers.radon.status == "ok"` (or `"timeout"`) with usable metrics; no Python traceback appears on stderr.
- `--output <path inside CWD>`: consolidated JSON is written atomically — a `<path>.tmp` sibling is created and written first, then `os.rename`d to `<path>`; no partial content is ever observable at the final path.
- When `--output` is supplied, stdout contains exactly the one-line summary (`analyzers: N | findings: M | duration: T s`) and no JSON blob.
- `--output /tmp/x.json`, `--output ~/x.json`, `--output /etc/anything` each cause the CLI to exit non-zero before any adapter runs; the error message contains `"sandbox"` (case-insensitive); no file is written outside CWD.
- The CWD guard resolves symlinks (`Path.resolve()`) before comparing, so a symlinked output path that resolves inside CWD is accepted, not rejected.
- `.tmp` sibling is created in the same directory as the final output path (same filesystem, same sandbox-writable region) — never in `/tmp` or any path outside the output file's parent directory.

## Test specification

`tests/test_cli.py` additions — written first:

- `test_adapter_error_does_not_crash_cli` — configure `FakeAnalyzer("ok_adapter")` returning `status="ok"` and `FakeAnalyzer("err_adapter")` returning `AnalyzerOutput(status="error", error="missing binary: semgrep", sarif=<minimal valid sarif>, ...)`; run CLI with both; assert returncode != 0; load consolidated output; assert both adapter keys present; assert `"ok_adapter"` has `status == "ok"` and `"err_adapter"` has `status == "error"`; assert no traceback substring in stderr.
- `test_atomic_write_tmp_then_rename` — run CLI with `--output <tmp_path>/result.json`; assert `<tmp_path>/result.json` exists after the call; assert no `<tmp_path>/result.json.tmp` remains (rename completed); assert `json.load` succeeds on the file; assert the `.tmp` was written in the same directory as the final path (verified by checking the implementation's `parent` path — code review concern, not a runtime test, but assert the implementation uses `output_path.parent / (output_path.name + ".tmp")`).
- `test_stdout_summary_only_when_output_flag` — run CLI with `--output <tmp_path>/result.json`; assert stdout matches `r"analyzers: \d+ \| findings: \d+ \| duration: .+s"` (case-insensitive) and does not contain `"{"` (no JSON blob on stdout).
- `test_output_outside_cwd_rejected_all_cases` — parametrize over `/tmp/x.json`, `~/x.json`, `/etc/x`; for each: assert returncode != 0; assert `"sandbox"` (case-insensitive) in combined output; assert target path does not exist after the call.
- `test_cwd_guard_accepts_symlink_inside_cwd` — create `tmp_path/subdir/`; symlink `tmp_path/link` → `tmp_path/subdir/`; run CLI with `--output tmp_path/link/result.json`; assert the error is NOT about CWD/sandbox (may still fail because no adapter is wired, which is acceptable — the guard must pass).
