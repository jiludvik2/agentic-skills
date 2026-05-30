---
id: s3-t0-pin-depcruiser-node-compatible
kind: task
project: code-review
status: active
parent: s3-depcruiser-node-compat
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md, adr-0017-node-range-and-js-toolchain-pins.md]
created: 2026-05-30
updated: 2026-05-30
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
