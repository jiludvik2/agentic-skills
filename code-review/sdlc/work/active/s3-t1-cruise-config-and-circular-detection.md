---
id: s3-t1-cruise-config-and-circular-detection
kind: task
project: code-review
status: active
parent: s3-depcruiser-node-compat
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-30
updated: 2026-05-30
tags: [dependency-cruiser, coupling, adapter, config, circular-deps]
---

# s3-t1 — Adapter supplies the cruise config; circular deps reported

## Outcome

The depcruiser adapter no longer aborts on a missing config file: it supplies the
cruise config dependency-cruiser requires (bundled default / generated / documented
host requirement — the mechanism is decided and recorded here), so a target without
its own `.dependency-cruiser.cjs` is analysed, and circular dependencies are
reported. Implements the remaining s3-story scenarios (config + circular detection).
Depends on s3-t0 (the compatible pin).

## Acceptance criteria

### Scenario: adapter supplies the required config
- **Given** a target with no `.dependency-cruiser.cjs`
- **When** the adapter runs
- **Then** it provides a config so dependency-cruiser does not abort with
  `Can't open a config file ...`. (Record which mechanism: a config asset bundled
  with the skill and passed via `--config`, an in-memory/temp generated config, or a
  documented host-supplied file — and why.)

### Scenario: circular dependencies are reported (smoke)
- **Given** the analyzer-coverage smoke test
- **When** the depcruiser case runs against `fixtures/js/src/cycle_a.ts` ↔
  `cycle_b.ts`
- **Then** it returns ≥1 circular-dependency finding and the case passes.

## Test specification

Write first, confirm red, then implement:

1. `test_depcruiser_supplies_config_when_target_has_none` (unit/integration): run
   the adapter against a target dir with no cruise config; assert no
   "Can't open a config file" error and the run reaches analysis.
2. `test_depcruiser_integration_detects_circular_dependency`
   (`@pytest.mark.integration`, skip if not vendored): run against the
   `cycle_a.ts` ↔ `cycle_b.ts` fixtures; assert ≥1 circular-dependency finding and
   `status=ok`.

## Notes

- If a config asset is bundled with the skill, it joins the s6-t1 wheel/bundle
  manifest — flag that cross-reference so install ships it too.
- The smoke harness depcruiser case should pass without manual config provisioning
  after this task (the epic's "no harness hacks" acceptance gate).
