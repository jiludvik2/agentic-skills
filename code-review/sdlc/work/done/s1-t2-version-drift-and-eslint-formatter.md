---
id: s1-t2-version-drift-and-eslint-formatter
kind: task
project: code-review
status: done
parent: s1-js-toolchain-manifest
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-29
updated: 2026-05-30
tags: [node, capabilities, drift, eslint, sarif]
notes: |
  Closed 2026-05-30. Verify PASS, Review MINOR-ONLY. Both Minor findings folded
  in rather than deferred: (1) drift guard extended to cover the eslint SARIF
  formatter (@microsoft/eslint-formatter-sarif, via the eslint entry's
  sarif_formatter field); (2) the F8/s4 xfail on test_eslint_integration_detects
  _console_log set strict=True to self-retire when s4 lands (matches ADR-0017 §3
  depcruiser convention). Nit (NODE_PATH ternary) also addressed. Mechanism
  chosen for formatter resolution: adapter exports NODE_PATH to node_modules_dir()
  (verified empirically against vendored eslint 9.39.4 + formatter 3.1.0).
---

# s1-t2 — Version-drift guard + eslint SARIF formatter cwd-independence

## Outcome

Advertised Node-tool versions agree with the lockfile (no drift between what
`--capabilities` claims and what `setup.sh` installs), and the eslint SARIF
formatter (`@microsoft/eslint-formatter-sarif`) resolves at runtime regardless
of the adapter's working directory. Implements story scenario 3 + the formatter
note. Depends on s1-t1.

## Acceptance criteria

### Scenario: capabilities versions match the lockfile (no drift)
- **Given** the pinned lockfile and `capabilities.json`
- **When** the advertised Node-tool versions are compared to the locked versions
- **Then** they agree. (`capabilities.json` currently carries **no** version
  fields for the Node tools — this task adds them, or adds a lockfile-derived
  version source, so the drift guard has two sides to compare.)

### Scenario: eslint formatter resolves independent of cwd
- **Given** the eslint adapter invoked with a target outside the skill root
- **When** it runs `eslint --format @microsoft/eslint-formatter-sarif`
- **Then** the formatter resolves (no "Cannot find formatter" / module-resolution
  error). The mechanism (NODE_PATH set by the adapter vs. an absolute formatter
  path vs. install layout) is decided here and documented — the smoke harness's
  `NODE_PATH` stopgap is replaced by the chosen production mechanism.

## Test specification

Write first, confirm red, then implement:

1. `test_capabilities_node_versions_match_lockfile`: parse `package-lock.json`
   and `capabilities.json`; assert the advertised version of each of the four
   Node tools equals the locked version. (Red until version fields + the source
   of truth are added.)
2. `test_eslint_formatter_resolves_from_foreign_cwd` (integration; skip if
   eslint not vendored): run the eslint adapter from a cwd outside the skill
   root against a fixture, assert no formatter-resolution error in the result
   (status is `ok` or a *findings* error, not a module-not-found error).
3. If NODE_PATH is the chosen mechanism, a unit test asserting the adapter sets
   it to the vendored `node_modules` before invoking eslint.

## Deferred

- Full eslint *findings* correctness on un-scaffolded projects is **F8 / s4** —
  this task only guarantees formatter resolution, not eslint config robustness.
