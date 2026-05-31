---
id: s1-t1-migrate-python-adapters
kind: task
project: code-review
status: done
parent: s1-migrate-adapters-and-emit-bundle
sources: [adr-0020-thin-invocation-runner.md, adr-0019-analyzer-unavailable-vs-error.md]
created: 2026-05-30
updated: 2026-05-31
tags: [migration, adapters, python, capture]
notes: |
  Verify PASS, Review MINOR-ONLY (no Critical/Important). Full suite 447 passed (incl. 5
  real-tool integration tests: bandit/gitleaks/pydeps/trivy/semgrep all ran); ruff + mypy
  code_review clean.
  - 5 subprocess adapters now return CaptureOutput via run_and_capture; all _to_sarif /
    JSON-parse / MetricSet building deleted (grep clean). run_and_capture gained env=.
  - ADR-0019 alignment: pre-flight failures (missing binary via shutil.which, semgrep
    missing/bad rules, trivy missing DB, empty target_paths) now return .unavailable, not
    error (was error). Updated test_cache_path_unification accordingly.
  - Output-sink decisions (deviation from spec's literal "redirect to stdout"): /dev/stdout
    is NOT writable under the OS sandbox ("permission denied") and is fragile in
    containers, so file-output tools avoid it entirely — trivy writes SARIF to stdout
    natively (dropped --output); gitleaks captures native finding output (dropped
    --report-path/SARIF; bundle carries both stdout+stderr). No temp files.
  - Transitional cli.py _capture_to_legacy/_safe_run shim wraps CaptureOutput -> empty-SARIF
    AnalyzerOutput so the legacy aggregate path holds green; DELETE in s1-t3.
  - capture.py imports run_subprocess lazily (function-level) to break the
    contracts/capture/adapters import cycle.
  Minor (opportunistic, not blocking — captured per SDLC Review rules):
  - FIXED here: env-merge coverage gap (added test_run_and_capture_merged_env_preserves_
    inherited); gitleaks stream-clarity docstring/comment.
  - OPEN: test_sandbox_compatibility gitleaks/trivy no-temp-file tests are now near-trivial
    (adapters create no scratch files + run_and_capture mocked) — consider converting them
    in s1-t3 to assert no --report-path/--output/temp arg is constructed, or dropping them.
  Nit (dropped): cross-adapter /dev/stdout rationale duplicated in gitleaks+trivy comments;
  gitleaks/trivy scope to target_paths[0] only (pre-existing single-path behaviour) — note
  for the bundle/scoping work if multi-path is ever wanted.
---

# Task s1-t1 — migrate the 5 subprocess Python adapters to invoke-and-capture

## Outcome

Each of the 5 **subprocess-based** Python adapters (bandit, semgrep, gitleaks, trivy,
pydeps) invokes its tool with the **same effective argv** as today and returns a raw
`CaptureOutput` via `run_and_capture`, with its ADR-0019 availability pre-flight preserved.
All output parsing (`_to_sarif`, JSON parsing, temp-file SARIF reads) is deleted. The
`run_and_capture` primitive gains an `env=` parameter (semgrep needs it now; the JS adapters
need it in s1-t2).

The 4 in-process library adapters are **out of scope** here — radon/vulture/cohesion move in
s1-t1b, schemathesis in s1-t1c (see the story's re-split decision).

## Design

**Primitive enhancement (`capture.py`):** add `env: dict[str, str] | None = None` to
`run_and_capture` and thread it to `run_subprocess` (which already accepts `env`). Covered by
a new `test_capture` test asserting the env reaches the subprocess.

For each adapter: keep the **invocation half** (argv construction, cwd, tolerated exit codes,
the empty-target short-circuit, the availability pre-flight) and replace the **output half**
(`run_subprocess` + parse + `_to_sarif`) with a single `run_and_capture(name, *argv,
timeout_s=..., env=..., ok_exit_codes=...)` call returning the capture verbatim. Adapters
that returned `unavailable` via the `empty_sarif` pattern now return
`CaptureOutput.unavailable(name, reason)`.

**File-output tools must redirect to stdout** (so the raw capture carries the findings):

- **bandit** — already stdout JSON (`-f json`); `--quiet`, tolerated exit `(0, 1)`. The F3
  progress-bar-on-stdout concern disappears (no parsing). Delete `_bandit_to_sarif`.
- **semgrep** — **`--x-ignore` is load-bearing** (without it semgrep silently skips `tests/`
  and returns zero findings — see memory); Python-only vendored ruleset from config; uses
  `env=`. Emit SARIF to stdout (`--sarif`) instead of a temp file; tolerated exit `(0, 1)`.
  Delete `_semgrep_to_sarif`.
- **gitleaks** — currently `--report-path <tmpfile>`; switch to `--report-path /dev/stdout`
  (keep `--report-format sarif`, `--no-git`) so the report lands on stdout; drop the
  temp-dir/file read. Preserve diff/target scoping. Tolerate the leaks-found exit code.
- **trivy** — **offline** (provisioned DB cache, no network egress); currently temp-file
  output → redirect to stdout. Preserve the offline invocation. Delete the temp-file read.
- **pydeps** — coupling/cycles JSON on stdout; delete `_pydeps_to_sarif` + metrics building.

## Acceptance criteria

- All 5 adapters return a `CaptureOutput`; no `_to_sarif` / temp-file SARIF read remains in
  any of them (`grep` clean within `adapters/` for this set).
- `run_and_capture` accepts `env=` and threads it to the subprocess (test-asserted).
- Per adapter, a test asserts the **built argv** contains its load-bearing flags
  (bandit `--quiet`; semgrep `--x-ignore` + `--sarif`; gitleaks `/dev/stdout`; trivy offline
  marker; pydeps invocation) — pinned so a future refactor cannot silently drop them.
- Per adapter, a **raw-capture** test (stdout captured verbatim, status `ok` on tolerated
  exit) and an **availability** test (`unavailable` / `error` when the pre-flight fails:
  missing binary / empty targets) pass.
- `uv run pytest`, `uv run ruff check .`, `uv run mypy code_review` clean.

## Test specification (write first, confirm RED)

`tests/test_capture.py`: add `test_run_and_capture_threads_env` — env passed to
`run_and_capture` is visible to the child (e.g. echo an env var).

Rewrite each `tests/test_adapters/test_<tool>.py` for bandit/semgrep/gitleaks/trivy/pydeps to
the new contract (old SARIF assertions deleted, not adapted):

1. `test_<tool>_invocation_pins_flags` — patch `run_and_capture` (or `run_subprocess`), run
   the adapter, assert the captured argv/env contains the load-bearing flags for that tool.
2. `test_<tool>_captures_raw_stdout` — feed a known stdout via the patched primitive; assert
   it lands verbatim on the returned `CaptureOutput.stdout`, status `ok`.
3. `test_<tool>_unavailable_preflight` — missing binary / empty target → `unavailable`
   (or `error` per the adapter's pre-flight), no exception.
4. Keep one **real-invocation** integration test per adapter (marked `integration`) that runs
   the actual tool on a fixture and asserts a non-empty raw capture — assert findings/output,
   not just `status==ok` (analyzer-coverage discipline).

## Notes

- Migrate in ascending risk: pydeps/gitleaks first, then bandit/trivy, then semgrep.
- Do NOT delete `aggregator`/`severity`/`hotspots`/`sarif_utils` here — the CLI still imports
  them until s1-t3. This task only empties these adapters' output half. (`sarif_utils`'
  `collect_python_files` may still be used by radon/vulture/cohesion until s1-t1b — leave it.)
- The protocol/adapter return-type agreement guard flagged in s1-t0 Verify: once these 5
  return `CaptureOutput`, add at least one assertion tying a concrete adapter return to the
  type (so the consolidation can't silently regress).
