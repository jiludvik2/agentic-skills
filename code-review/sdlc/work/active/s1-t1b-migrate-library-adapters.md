---
id: s1-t1b-migrate-library-adapters
kind: task
project: code-review
status: active
parent: s1-migrate-adapters-and-emit-bundle
sources: [adr-0020-thin-invocation-runner.md, adr-0019-analyzer-unavailable-vs-error.md, s1-migrate-adapters-and-emit-bundle.md]
created: 2026-05-30
updated: 2026-05-30
tags: [migration, adapters, python, library-to-cli, capture]
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
