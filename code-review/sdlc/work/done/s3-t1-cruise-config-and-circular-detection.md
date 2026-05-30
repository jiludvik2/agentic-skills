---
id: s3-t1-cruise-config-and-circular-detection
kind: task
project: code-review
status: done
parent: s3-depcruiser-node-compat
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-30
updated: 2026-05-30
notes:
  - "Per-task Review Minor (fixed): the config-supply unit test asserted only the
    --config file's presence, not its contents. Strengthened it to assert the
    written config contains enhancedResolveOptions + doNotFollow, so a refactor
    writing an empty/wrong config is caught without the vendored toolchain."
  - "Per-task Review Minor (deferred): _CRUISE_CONFIG is an inline JS-in-Python
    heredoc with no import-time validation. Acceptable for a 9-line config; a
    durable option is to ship it as a .cjs resource via importlib.resources
    (which also pre-empts the s6-t1 wheel/bundle question). Deferred."
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

## Closure notes (2026-05-30)

**Config mechanism = temp-generated (option b).** `depcruiser.py` writes a
`cruise-config.cjs` into a `tempfile.TemporaryDirectory` and passes it via
`--config` (mirrors s2's jscpd tempdir pattern). Chosen over a bundled asset
(option a, which the spec note flagged would join the s6-t1 wheel manifest) or a
host-supplied file (option c) because it is **self-contained** — ships nothing
extra, no packaging dependency, and works on any target. The config is minimal:
- `doNotFollow: { path: "node_modules" }`;
- `enhancedResolveOptions.extensions: [.js,.jsx,.ts,.tsx,.mjs,.cjs,.json]` —
  resolves bare `./foo` TS/JS imports **without** a target `tsConfig`/tsconfig.json
  (the QA harness's old config hard-required one);
- **no `forbidden` rules** — the adapter reads each dependency's `circular` flag
  from the JSON directly; a forbidden rule would make depcruise exit non-zero on a
  violation, which the adapter treats as an error.

**Second seam found + fixed: TypeScript transpiler.** depcruise only enumerates
`.ts`/`.tsx` in a **directory** target when a supported TypeScript (`>=2 <6`) is
installed. knip pulls `typescript@6` (out of range) → `.ts` disabled → depcruise
returned **zero modules** for the CLI's default `.` full-scan (explicit file args
still parsed, masking it). Fixed by vendoring **`typescript@^5`** (→ 5.9.3)
top-level; knip keeps its own nested `@6`. Without this, coupling silently
reported nothing on real TS projects — the GA-blocker class s3 exists to close.
Pinned in `package.json` + `stack-pins.md`; ADR-0017 §3 records the rationale.

**Tests.** New unit `test_depcruiser_supplies_config_when_target_has_none`
(asserts `--config` points at a real file at invocation). The spec's
`test_depcruiser_integration_detects_circular_dependency` was realised by
**strengthening the existing meta-tracked `test_depcruiser_integration`**:
repointed to a dedicated `tests/fixtures/js-circular/` cycle pair (a no-cycle
fixture would be zero-signal), removed its `xfail(strict)`, and added a
`len(results) >= 1` circular-finding assertion — avoiding a duplicate integration
test on the same fixture. `must_xfail` flipped False in
`test_node_integration_gating.py` (the s2/jscpd forcing-function pattern).

**No harness hacks.** Removed the scaffolded `.dependency-cruiser.cjs` from
`scaffold_fixtures.sh` and `git rm`'d the committed fixture copy — the smoke
harness now exercises the adapter's self-provisioning (it runs the polyreview CLI
→ adapter, which passes `--config` explicitly, overriding any auto-discovered
fixture config).

**Gates.** Full suite 381 passed / 1 xfailed (only eslint/s4 remains); ruff +
mypy clean.
