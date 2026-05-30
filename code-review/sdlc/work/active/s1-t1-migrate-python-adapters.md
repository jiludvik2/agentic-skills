---
id: s1-t1-migrate-python-adapters
kind: task
project: code-review
status: active
parent: s1-migrate-adapters-and-emit-bundle
sources: [adr-0020-thin-invocation-runner.md, adr-0019-analyzer-unavailable-vs-error.md]
created: 2026-05-30
updated: 2026-05-30
tags: [migration, adapters, python, capture]
---

# Task s1-t1 — migrate the 9 Python adapters to invoke-and-capture

## Outcome

Each Python adapter invokes its tool with the **exact same argv** as today and returns a
raw `CaptureOutput` via `run_and_capture`, with its ADR-0019 availability pre-flight
preserved. All output parsing (`_to_sarif`, JSON parsing, `MetricSet` building) is deleted.

## Design

For each adapter: keep the **invocation half** (argv construction, cwd, tolerated exit
codes, the empty-target short-circuit, the availability pre-flight) and replace the
**output half** (`run_subprocess` + parse + `_to_sarif`/metrics) with a single
`run_and_capture(name, *argv, timeout_s=..., cwd=..., ok_exit_codes=...)` call returning
the capture verbatim. Adapters that previously returned `unavailable` via the
`empty_sarif`/`js_unavailable` pattern now return `CaptureOutput.unavailable(name, reason)`.

Adapters (load-bearing invocation detail to PRESERVE and pin by test):

- **bandit** — `--quiet`, tolerated exit `(0, 1)`; the F3 progress-bar-on-stdout concern
  disappears (no parsing). Delete `_bandit_to_sarif`.
- **semgrep** — **`--x-ignore` is load-bearing** (without it semgrep silently skips `tests/`
  and returns zero findings — see memory); Python-only vendored ruleset path from config.
- **gitleaks** — diff/target scoping; SARIF passthrough becomes raw capture.
- **trivy** — **offline** (uses the provisioned DB cache, no network egress).
- **radon** — cc/mi invocation; `MetricSet` building deleted, raw stdout captured.
- **vulture** — dead-code; delete `_vulture_to_sarif`.
- **pydeps** — coupling/cycles; delete `_pydeps_to_sarif` + metrics building.
- **cohesion_** — LCOM4 invocation; metrics building deleted.
- **schemathesis_** — contract testing (full-scope, largest adapter ~10.4K); delete its
  SARIF builder; preserve auth/sandbox-isolation invocation and `story-level` scope
  restriction. **This is the highest-risk migration — do it last and carefully.**

## Acceptance criteria

- All 9 Python adapters return a `CaptureOutput`; no `_to_sarif` / `MetricSet` building
  remains in any of them (`grep` clean within `adapters/` for the Python set).
- Per adapter, a test asserts the **built argv** contains its load-bearing flags
  (e.g. bandit `--quiet`; semgrep `--x-ignore`; trivy offline marker) — pinned so a future
  refactor cannot silently drop them.
- Per adapter, a **raw-capture** test (stdout captured verbatim, status `ok` on tolerated
  exit) and an **availability** test (`unavailable` when the pre-flight fails:
  missing binary / empty targets) pass.
- `uv run pytest`, `uv run ruff check .`, `uv run mypy code_review` clean. (The SARIF-
  correctness tests for these adapters are deleted in this task or in s1-t3 — name which.)

## Test specification (write first, confirm RED)

Rewrite each `tests/test_adapters/test_<tool>.py` to the new contract (the old SARIF
assertions are deleted, not adapted):

1. `test_<tool>_invocation_pins_flags` — patch `run_and_capture` (or `run_subprocess`),
   run the adapter, assert the captured argv contains the load-bearing flags for that tool.
2. `test_<tool>_captures_raw_stdout` — feed a known stdout via the patched primitive; assert
   it lands verbatim on the returned `CaptureOutput.stdout`, status `ok`.
3. `test_<tool>_unavailable_preflight` — missing binary / empty target → `status=="unavailable"`
   (or `error` per the adapter's pre-flight), no exception.
4. Keep one **real-invocation** integration test per adapter (marked `integration`) that runs
   the actual tool on a fixture and asserts a non-empty raw capture — the analyzer-coverage
   discipline (assert findings/output, not just `status==ok`).

## Notes

- Migrate in ascending risk: gitleaks/radon/vulture/cohesion first, then bandit/semgrep/
  pydeps/trivy, then **schemathesis_ last**.
- Do NOT delete `aggregator`/`severity`/`hotspots`/`sarif_utils` here — the CLI still imports
  them until s1-t3. This task only empties the adapters' output half.
- `js_base.js_unavailable` migration is s1-t2 (JS adapters); the Python set uses
  `required_binary` / library-availability pre-flight.
