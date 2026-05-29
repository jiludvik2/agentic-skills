---
id: s1-js-toolchain-manifest
kind: story
project: code-review
status: active
parent: epic-analyzer-ga-hardening
children: [s1-t0-adr-node-range-and-js-pins, s1-t1-package-manifest-and-lockfile, s1-t2-version-drift-and-eslint-formatter, s1-t3-ci-node-integration-and-xfail-gating]
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-29
updated: 2026-05-29
tags: [javascript, typescript, node, packaging, setup, ga-readiness]
---

# s1 — JS toolchain manifest & pins

## Summary

The four Node analyzers (eslint, knip, jscpd, dependency-cruiser) are neither
version-pinned nor vendored. `setup.sh` logs `Node dependencies (skipped — no
package.json/package-lock.json yet)`, and the only record of intended versions is
the `version` strings in `capabilities.json`. Installing "latest" drifts from
what the adapters assume — knip's JSON schema changed (F4) and
dependency-cruiser 16 breaks on modern Node (F1) — so the JS toolchain is
effectively unshippable (FINDINGS.md F5).

This story establishes the manifest, lockfile, and vendoring so a clean
`setup.sh` produces a known-good, reproducible Node toolchain. It is foundational
for **s3** (the dependency-cruiser pin lands in this lockfile).

## Use case

- **As a** host operator who ran `setup.sh`
- **I want** the JS/TS analyzers installed at known-good, pinned versions
- **so that** TypeScript coverage works reproducibly instead of depending on
  whatever npm resolves "latest" to today.

## Acceptance criteria

### Scenario: committed manifest + lockfile
- **Given** the repo after this story
- **When** the skill root is inspected
- **Then** a committed `package.json` + lockfile pins `eslint`, `knip`, `jscpd`,
  `dependency-cruiser`, and `@microsoft/eslint-formatter-sarif` (plus transitive
  deps) to versions compatible with the supported Node range, and the supported
  Node range is recorded in `stack-pins.md`.

### Scenario: setup.sh vendors the toolchain
- **Given** a clean checkout
- **When** `./scripts/setup.sh` runs
- **Then** it installs `node_modules` from the lockfile (no "skipped — no
  package.json" message) and all four Node analyzers probe `available` via
  `polyreview --capabilities`.

### Scenario: capabilities versions match the lockfile
- **Given** the pinned lockfile
- **When** `capabilities.json` analyzer `version` fields are compared to the
  installed versions
- **Then** they agree (no drift between advertised and installed).

### Scenario: smoke test runs the JS analyzers from a clean setup
- **Given** setup.sh has run
- **When** the analyzer-coverage smoke test runs
- **Then** the eslint and knip cases pass without the harness installing pinned
  versions by hand. (jscpd and depcruiser still require s2/s3 to pass.)

### Scenario: CI runs the Node-analyzer integration tests (F9)
- **Given** the vendored toolchain from this story
- **When** CI runs the fast-tier suite
- **Then** CI installs the Node toolchain and the Node-analyzer integration tests
  (`test_depcruiser_integration`, `test_jscpd_integration`,
  `test_eslint_integration_*`) **run rather than skip** — so F1/F2/F8 regressions
  are caught. The `skipif(binary missing)` is dropped or gated on a CI flag set
  once the toolchain is vendored. (Until s2/s3/s4 land, these tests legitimately
  fail; this scenario closes only when the toolchain is present AND those fixes
  are in — i.e. it gates at the story-boundary alongside s2/s3/s4.)

## Notes

- The eslint SARIF formatter must resolve at runtime regardless of the adapter's
  cwd — confirm whether `NODE_PATH`, a formatter-path argument, or install
  layout is the right mechanism (the smoke harness uses `NODE_PATH` as a stopgap).
- Decide whether the lockfile lives at the skill root or the package root, and
  how it interacts with the wheel (Node tooling is not shipped in the wheel).

## Plan (2026-05-29; operator-approved decisions: Node 20+22 matrix, xfail-gate)

1. **s1-t0 — ADR-0017 + stack-pins: Node range & JS pins.** Records supported
   Node range (20 LTS + 22 LTS, matrix-tested), the five npm pins working across
   both, lockfile location (skill root), wheel-exclusion. Hard-stop runtime
   decision; operator approves the ADR. Foundational for t1.
2. **s1-t1 — package.json + lockfile; setup.sh vendors.** Commit the manifest +
   lockfile; `setup.sh`'s existing `npm ci` branch then populates
   `node_modules`; the four Node analyzers probe `available`. (Story scenarios
   1 & 2.)
3. **s1-t2 — version-drift guard + eslint formatter cwd-independence.** Add a
   version source that matches the lockfile (capabilities currently has none);
   make the SARIF formatter resolve regardless of cwd, replacing the harness's
   NODE_PATH stopgap. (Story scenario 3 + formatter note.)
4. **s1-t3 — CI runs Node integration tests (F9), xfail-gated.** Node 20+22
   matrix `npm ci` + run the integration tests (not skip); jscpd/depcruiser/
   eslint xfail(strict) → flip in s2/s3/s4 respectively. (Story scenario 5 / F9.)

**Deferrals:** jscpd findings → s2 (F2); depcruiser-on-both-Nodes → s3 (F1);
eslint findings robustness → s4 (F8). Their integration tests xfail until then.
