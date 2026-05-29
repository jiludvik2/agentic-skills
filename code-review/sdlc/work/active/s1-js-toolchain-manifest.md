---
id: s1-js-toolchain-manifest
kind: story
project: code-review
status: active
parent: epic-analyzer-ga-hardening
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

## Notes

- The eslint SARIF formatter must resolve at runtime regardless of the adapter's
  cwd — confirm whether `NODE_PATH`, a formatter-path argument, or install
  layout is the right mechanism (the smoke harness uses `NODE_PATH` as a stopgap).
- Decide whether the lockfile lives at the skill root or the package root, and
  how it interacts with the wheel (Node tooling is not shipped in the wheel).
