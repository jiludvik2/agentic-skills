---
id: s1-t1b-migrate-library-adapters
kind: task
project: code-review
status: done
parent: s1-migrate-adapters-and-emit-bundle
sources: [adr-0020-thin-invocation-runner.md, adr-0019-analyzer-unavailable-vs-error.md, s1-migrate-adapters-and-emit-bundle.md]
created: 2026-05-30
updated: 2026-05-31
tags: [migration, adapters, python, library-to-cli, capture]
notes: |
  DONE 2026-05-31. Verify PASS, Review MINOR-ONLY (no Critical/Important).

  Implementation deviations from the spec's Design (both Verify-accepted):
  - **Invocation: `python -m <module>` not the console script.** The spec said console
    scripts + a `required_binary`/`shutil.which` pre-flight; that would have forced
    radon/vulture/cohesion to report `unavailable` in capabilities when off PATH, breaking
    `test_capabilities_runtime` (documented intent: "radon is library-based … stays
    available"). radon/vulture/cohesion are pinned deps that ship with the package and
    cannot be "missing", so they follow the bandit/pydeps `python -m` pattern, keep only the
    empty-targets → unavailable pre-flight, and stay capability-available. AC#2's availability
    test is the empty-targets branch of its "(missing console script / empty targets)" OR.
  - **vulture `ok_exit_codes=(0, 3)` not (0, 1).** vulture's real ExitCode enum is
    NoDeadCode=0 / InvalidInput=1 / InvalidCmdlineArguments=2 / DeadCode=3. Success = found
    dead code = 3; the spec's (0,1) text would have masked exit 1 (InvalidInput, an error).

  Pinned invocations: radon `cc --json <paths>`; vulture `<paths>` (tolerate 0,3);
  cohesion `-d <dir>` for a single directory target XOR `-f <files...>` otherwise (cohesion
  errors on `-f <dir>`).

  Review Minors (opportunistic, not fix tasks):
  - **cohesion multi-directory dispatch** (`cohesion_.py`): the `-d` guard fires only for a
    *single* directory target; 2+ directory targets fall to `-f <dir...>` and surface
    cohesion's own error as a non-ok status. Cohesion's CLI architecturally can't take
    multiple dirs in one call → formalise the target contract (single-dir-or-file-list) when
    s1-t3 reworks CLI target derivation.
  - **Shared `python -m` rationale comment** is duplicated across radon/vulture/cohesion (and
    bandit/pydeps); consider hoisting the cross-adapter "why pinned-dep, no PATH gating"
    rationale to one place (e.g. capture.py / adapter-package note) in a later cleanup.
  - Test-docstring "missing console script" overstatement — fixed in this task.

  `sarif_utils.collect_python_files` is now orphaned in source (no remaining consumer) but
  its deletion stays deferred to s1-t3 while the CLI still imports `sarif_utils`.

  Gate: full suite 450 passed (3 new integration real-runs), ruff + `mypy code_review` clean.
---

# Task s1-t1b — migrate radon / vulture / cohesion (library → CLI subprocess)

## Outcome

The three in-process library adapters become thin subprocess invocations of their tool's
console script, returning a raw `CaptureOutput` via `run_and_capture`. All in-process
analysis (`cc_visit`, `Vulture().scavenge`, `cohesion.module.Module`), `MetricSet` building,
and `_to_sarif` are deleted. The CLI invocation contract is **pinned by test** for each tool.

## Why this is its own task

The story's original s1-t1 assumed "keep the invocation half." These three have **no
subprocess to keep** — they call a Python library in-process. Migrating to the thin-runner
model means *choosing* the CLI invocation that pins each tool's scanning behaviour (a
load-bearing default), which the story's re-split decision (2026-05-30) isolated here.

## Design

Each adapter's `run()` becomes: empty-target short-circuit → availability pre-flight →
`run_and_capture(name, <console-script>, *args, timeout_s=..., ok_exit_codes=...)`. The
console scripts ship in the venv (`radon`, `vulture`, `cohesion`).

Chosen CLI invocations (pin by test):

- **radon** — `radon cc --json <paths...>` (cyclomatic complexity as JSON on stdout). MI can
  be added as a second capture later if needed; cc is the load-bearing one. Tolerated exit
  `(0,)`. Delete the `cc_visit`/`MetricSet` path.
- **vulture** — `vulture <paths...>` (dead-code report as text on stdout, `file:line: unused
  …`). vulture exits non-zero when it finds dead code → tolerate `(0, 1)`. Delete
  `_vulture_to_sarif`.
- **cohesion** — `cohesion -d <dir>` (or `-f <file>` per target shape); LCOM-style cohesion
  report as text on stdout. Tolerated exit `(0,)`. Delete the `Module.from_file`/`MetricSet`
  path and the low-cohesion threshold/SARIF building.

Targets: reuse the existing target-path handling. If a tool needs a directory rather than a
file list, derive it from `request.target_paths` (document the choice in close notes).

## Acceptance criteria

- radon/vulture/cohesion each return a `CaptureOutput`; no `cc_visit` / `Vulture` /
  `cohesion.module` / `MetricSet` / `_to_sarif` remains in them (`grep` clean).
- Per adapter, an **invocation** test pins the built argv (radon `cc --json`; vulture target
  args; cohesion `-d`/`-f`), a **raw-capture** test (known stdout verbatim, status `ok`), and
  an **availability** test (missing console script / empty targets → `unavailable`/`error`).
- One `integration`-marked real run per adapter on a Python fixture asserting a **non-empty**
  raw capture that actually contains findings/metrics (analyzer-coverage discipline — not
  just `status==ok`).
- `uv run pytest`, `uv run ruff check .`, `uv run mypy code_review` clean.

## Test specification (write first, confirm RED)

Rewrite `tests/test_adapters/test_radon.py`, `test_vulture.py`, `test_cohesion.py`:

1. `test_<tool>_invocation_pins_flags` — patch `run_and_capture`, assert the built argv.
2. `test_<tool>_captures_raw_stdout` — patched primitive feeds known stdout → verbatim on
   `CaptureOutput.stdout`, status `ok`.
3. `test_<tool>_unavailable_preflight` — console-script absent / empty targets → no exception.
4. One `integration` real-run test per adapter (assert findings present, not just ok).

## Notes

- After this task, `sarif_utils.collect_python_files` may have no remaining Python-adapter
  consumer — check; if dead, it's deleted in s1-t3 (don't delete here while the CLI still
  imports `sarif_utils`).
- Keep `run_and_capture` as enhanced in s1-t1 (with `env=`); these three don't need `env`.
