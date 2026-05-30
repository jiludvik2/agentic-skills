---
id: s3-t0-pin-depcruiser-node-compatible
kind: task
project: code-review
status: done
parent: s3-depcruiser-node-compat
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md, adr-0017-node-range-and-js-toolchain-pins.md]
created: 2026-05-30
updated: 2026-05-30
notes:
  - "Review Minor (pre-existing pattern): the SARIF driver `version` literal in
    depcruiser.py is hand-synced with the lockfile/capabilities and no drift
    guard reaches it (the s1-t2 guard covers capabilities.json only). Added a
    keep-in-sync breadcrumb; the durable fix (derive the driver version from
    capabilities at runtime, killing the class across all adapters) is deferred."
tags: [dependency-cruiser, node, pin, lockfile, capabilities]
---

# s3-t0 — Pin dependency-cruiser to a Node-compatible version

## Outcome

`dependency-cruiser` is pinned (in the s1 `package.json`/`package-lock.json`) to a
version that runs on the supported Node range (ADR-0017: Node 20 + 22) — i.e. one
that imports `R_OK` from `node:fs/constants`, not as a named export of `node:fs`
(≈ ≥16.3.0) — and `capabilities.json`'s advertised dependency-cruiser version
matches the locked version. After this task the adapter gets **past** the
`SyntaxError: ... does not provide an export named 'R_OK'` (it will then fail on the
missing cruise config, which s3-t1 supplies). Depends on **s1 closed**.

## Acceptance criteria

### Scenario: no R_OK SyntaxError on the supported Node range
- **Given** the supported Node range (`stack-pins.md` / ADR-0017) and the bumped pin
  installed via `setup.sh`
- **When** dependency-cruiser is invoked
- **Then** it no longer throws the `node:fs` `R_OK` SyntaxError at
  `assert-file-existence.mjs` (it loads and runs to the config check).

### Scenario: capabilities version matches the lockfile
- **Given** the bumped pin
- **When** `capabilities.json`'s dependency-cruiser `version` is compared to the
  locked version
- **Then** they agree (no drift) — consistent with the s1-t2 version-drift guard.

## Test specification

Write first, confirm red, then implement:

1. `test_depcruiser_pin_is_node_compatible` (unit): parse `package-lock.json`;
   assert the locked `dependency-cruiser` version is ≥ the agreed
   Node-fs/constants-compatible floor (record the exact floor in the test, derived
   from ADR-0017's Node range).
2. `test_capabilities_depcruiser_version_matches_lockfile` (unit): assert
   `capabilities.json`'s dependency-cruiser version equals the locked version
   (extends / parallels the s1-t2 drift guard).
3. `test_depcruiser_loads_without_r_ok_syntaxerror`
   (`@pytest.mark.integration`, skip if not vendored): invoke dependency-cruiser via
   the adapter; assert the failure mode (if any) is the missing-config error, **not**
   the `R_OK` SyntaxError. (Goes green here; circular-dep detection is s3-t1.)

## Notes

- The pin change lands in **s1's committed lockfile** (ADR-0017 named depcruiser 16
  a "candidate"); confirm the bumped version still satisfies the caret-major intent
  recorded there, or amend ADR-0017 if the range shifts.
- Verify the lower break boundary empirically if cheap — FINDINGS.md observed the
  break on Node 24 but the exact floor was unconfirmed.

## Closure notes (2026-05-30)

- **Pin bumped 16.0.0 → 16.10.4** in `.claude/skills/code-review/package.json`
  (`^16` → `^16.10.4`, stays inside the `^16` caret intent) + regenerated
  `package-lock.json`. Reconciled into `capabilities.json`, the `depcruiser.py`
  SARIF driver version, ADR-0017 §3, and `stack-pins.md` (SDLC rule #1b), all in
  this change.
- **Empirical floor = 16.10.2** (not the story's "≈16.3" estimate). Confirmed
  against the npm tarballs on Node 24: `16.10.1` still does
  `import { accessSync, R_OK } from "node:fs"` and dies with the `R_OK`
  SyntaxError; `16.10.2` switched to `import { accessSync, constants } from
  "node:fs"`. Recorded the corrected floor in ADR-0017, stack-pins, and the test
  constant `DEPCRUISER_NODE_FS_CONSTANTS_FLOOR=(16,10,2)`.
- **Tests.** New `test_depcruiser_pin_is_node_compatible` (lockfile ≥ floor) +
  `test_depcruiser_loads_without_r_ok_syntaxerror` (integration: adapter error
  no longer carries the `R_OK` SyntaxError). Test-spec item #2
  (`test_capabilities_depcruiser_version_matches_lockfile`) was **not** added —
  the pre-existing generic guard `test_capabilities_node_versions_match_lockfile`
  already asserts capabilities==lockfile for all four vendored Node analyzers
  including depcruiser (a depcruiser-specific copy would be a strictly-weaker
  duplicate). Verifier confirmed AC2 adequately covered.
- **Still xfail:** `test_depcruiser_integration` (full circular-dep detection)
  stays `xfail(strict)` — depcruise now loads but aborts on the missing cruise
  config, which **s3-t1** supplies. s3-t1 flips that xfail and its `must_xfail`
  entry in `test_node_integration_gating.py`.
- **Gates:** full suite 379 passed / 2 xfailed; ruff + mypy clean. Verifier
  **PASS**; per-task Review **MINOR-ONLY** (one Minor → notes above; Nits dropped).
- **Story-close follow-up (rule #26):** `npm audit` at the skill root reports 5
  vulns (1 high picomatch ReDoS, 4 moderate incl. smol-toml DoS). **Pre-existing**
  — both `picomatch` and `smol-toml` were already in the HEAD `16.0.0` lockfile;
  the bump did not introduce them (it moved depcruiser's own picomatch 3.0.1 →
  ^4.x). Transitive deps of the vendored, wheel-excluded toolchain that runs
  offline against local code. Assess/record at the **s3 story** close, not here.
