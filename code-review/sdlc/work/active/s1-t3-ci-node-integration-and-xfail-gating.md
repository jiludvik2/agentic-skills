---
id: s1-t3-ci-node-integration-and-xfail-gating
kind: task
project: code-review
status: active
parent: s1-js-toolchain-manifest
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-29
updated: 2026-05-29
tags: [ci, node, integration-tests, f9, xfail]
---

# s1-t3 — CI runs the Node-analyzer integration tests (F9), xfail-gated per story

## Outcome

CI installs the vendored Node toolchain on a **Node 20 + 22 matrix** and **runs**
the Node-analyzer integration tests instead of skipping them — so F1/F2/F8
regressions become visible. The three still-broken tests are `xfail(strict)`
referencing their fixing story, so CI stays green while the tests genuinely run;
each fix-story flips its test to a real pass. Implements story scenario 5 / F9.
Depends on s1-t1 (toolchain must be installable in CI).

## Acceptance criteria

### Scenario: CI installs the toolchain and runs (not skips) the integration tests
- **Given** the committed manifest + lockfile from s1-t1
- **When** CI runs
- **Then** a CI step/job runs `npm ci` (from the skill-root lockfile) on a Node
  **20 and 22** matrix, then runs the Node-analyzer integration tests — they are
  **collected and executed**, not `skipif`-skipped. The existing
  `skipif(node_binary missing)` is dropped or gated on a CI flag set once the
  toolchain is vendored.

### Scenario: broken analyzers xfail referencing their fixing story
- **Given** jscpd (F2/s2), depcruiser (F1/s3), eslint (F8/s4) are not yet fixed
- **When** their integration tests run in CI
- **Then** each is marked `@pytest.mark.xfail(strict=True, reason="<story>")` so
  CI is green, an **unexpected pass fails** (forcing the flip), and `knip`'s
  integration test passes outright.

### Scenario: F9 closes at the s4 story boundary
- **Given** xfail-gating
- **Then** this task's own AC is met when CI runs the tests; the *full* F9
  intent (all Node integration tests passing) closes as s2/s3/s4 each flip their
  xfail. Recorded as a cross-story dependency, not a blocker on s1 close.

## Test specification

Write first, confirm red, then implement:

1. Add `xfail(strict=True, reason=...)` markers to `test_jscpd_integration`,
   `test_depcruiser_integration`, `test_eslint_integration_detects_console_log`,
   each naming its fixing story. Replace/gate their `skipif` so they run when the
   toolchain is present.
2. `test_node_integration_tests_run_when_vendored`: a meta-test (or collection
   assertion) confirming the three are collected (not skipped) when
   `node_binary` resolves — i.e. the skip→xfail conversion took effect.
3. CI change (`.github/workflows/ci.yml`): add a Node-matrix job (or step) that
   `npm ci`s the toolchain and runs `pytest -m integration` for the Node
   adapters. Verified by the workflow run (manual/CI verification in close notes;
   the YAML is not unit-testable here).

## Deferred (BDD)

- jscpd integration flips xfail→pass in **s2**; depcruiser in **s3**; eslint in
  **s4**. Each fix-story owns removing its xfail.
