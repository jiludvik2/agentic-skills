---
id: s4-t0-eslint-formatter-and-config-discovery
kind: task
project: code-review
status: active
parent: s4-eslint-adapter-robustness
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-30
updated: 2026-05-30
tags: [eslint, adapter, sarif-formatter, node, cwd]
---

# s4-t0 — eslint formatter resolution + config-discovery robustness

## Outcome

The eslint adapter resolves `@microsoft/eslint-formatter-sarif` itself from the
vendored `node_modules` (absolute formatter path, or `NODE_PATH` set by the adapter
on the subprocess env — not by the caller), and its integration test runs without
the smoke harness's `NODE_PATH`/cwd scaffolding. The formatter-resolution half is a
real adapter defect (F8); the config-discovery half is a robustness/test fix.
Single coherent adapter change implementing all three s4-story scenarios. Depends on
s1 (vendored toolchain).

## Acceptance criteria

(The s4-story scenarios are the contract; restated as the per-task gate.)

### Scenario: SARIF formatter resolves regardless of cwd
- **Given** the adapter run from any cwd with the vendored toolchain
- **When** it builds its command
- **Then** the SARIF formatter resolves (absolute path or adapter-set `NODE_PATH`)
  and eslint does not error on formatter loading.

### Scenario: integration test runs without harness scaffolding
- **Given** `tests/test_adapters/test_eslint.py::test_eslint_integration_*`
- **When** it runs with the toolchain present (no external `NODE_PATH`, no manual
  cwd change)
- **Then** it returns `status=ok` and valid SARIF with the expected finding.

### Scenario: smoke harness drops the eslint NODE_PATH stopgap
- **Given** the analyzer-coverage harness after this task
- **Then** `run_smoke.py` no longer sets `NODE_PATH` (or special-cases eslint's cwd)
  for the eslint case to pass.

## Test specification

Write first, confirm red, then implement. Extend
`tests/test_adapters/test_eslint.py`:

1. `test_eslint_formatter_resolves_from_arbitrary_cwd`: run the adapter from a cwd
   that is **not** the fixture dir, with a fixture flat config supplied to the
   target; assert `status=ok` and SARIF parses (no "problem loading formatter" /
   "couldn't find eslint.config" error).
2. Fix `test_eslint_integration_detects_console_log` to run without external
   `NODE_PATH` and to point eslint at a fixture with a discoverable flat config;
   assert it detects the planted rule violation.

## Notes

- Coordinates with **s1-t2**, which guarantees formatter *resolution* as a
  precondition; this task owns the adapter-side production mechanism and the
  self-sufficient integration test (F8). If s1-t2 already moved formatter
  resolution into the adapter, this task narrows to config-discovery robustness +
  dropping the harness stopgap — reconcile at execution.
- After this task the harness `NODE_PATH` stopgap is removed; confirm the smoke
  eslint case stays green without it.
