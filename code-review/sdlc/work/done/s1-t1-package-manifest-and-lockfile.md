---
id: s1-t1-package-manifest-and-lockfile
kind: task
project: code-review
status: done
parent: s1-js-toolchain-manifest
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-29
updated: 2026-05-30
tags: [node, npm, packaging, setup]
notes: |
  Committed package.json + package-lock.json (npm-generated, 5318 lines) at the
  skill root pinning eslint^9 (9.39.4), knip^5 (5.0.0), jscpd^4 (4.0.5),
  dependency-cruiser^16 (16.0.0, F1 candidate — s3 bumps), @microsoft/
  eslint-formatter-sarif^3 (3.1.0). node_modules gitignored. New
  tests/test_js_toolchain_manifest.py (manifest + manifest↔lock drift guard).

  Manual verification (AC scenario 2/3): `npm install` populated node_modules;
  `npm ci --dry-run` passes (lockfile↔manifest consistent); `cli --capabilities`
  shows eslint/knip/jscpd/depcruiser all status=available. setup.sh:74 guard now
  satisfied → takes the npm ci branch (skip message gone).

  Verify PASS. Review MINOR-ONLY:
  - [APPLIED] Minor x2: drift-guard test hardened — anchored the pin regex and
    made unrecognised pin forms fail loudly (no silent no-op), so a later s3
    depcruiser range/tag rewrite can't slip the guard. Docstring corrected to
    "shares the locked major".
  - [APPLIED] Minor: added a `//dependency-cruiser` tracking marker in
    package.json flagging ^16 as the F1-broken candidate s3 must bump.
  - [APPLIED] (verifier smell) fixed stale setup.sh comment ("toolchain lands in s3").
---

# s1-t1 — Commit package.json + lockfile; setup.sh vendors the toolchain

## Outcome

A committed `package.json` + `package-lock.json` at the skill root pin the five
npm packages per ADR-0017. `scripts/setup.sh` (already wired for `npm ci` from
those files) now installs `node_modules` into `cache_root()/node_modules` on a
clean checkout — no "skipped — no package.json" message — and all four Node
analyzers probe `available`. Implements story scenarios 1 & 2. Depends on s1-t0.

## Acceptance criteria

### Scenario: committed manifest + lockfile pin the five tools
- **Given** the repo after this task
- **When** `.claude/skills/code-review/package.json` + `package-lock.json` are read
- **Then** they pin `eslint`, `knip`, `jscpd`, `dependency-cruiser`, and
  `@microsoft/eslint-formatter-sarif` to the ADR-0017 versions, and the lockfile
  is internally consistent (`npm ci` succeeds against it).

### Scenario: setup.sh vendors without the "skipped" branch
- **Given** a clean checkout (empty `node_modules`)
- **When** `./scripts/setup.sh` runs
- **Then** it takes the `npm ci` branch (not `scripts/setup.sh:85`'s "skipped"
  message) and populates `cache_root()/node_modules/.bin` with the four tools.

### Scenario: capabilities reports the four Node analyzers available
- **Given** setup.sh has run
- **When** `polyreview --capabilities` runs
- **Then** `eslint`, `knip`, `jscpd`, `depcruiser` each report `available`
  (via `js_base.probe_js_adapter` resolving `node_modules/.bin/<tool>`).

## Test specification

Write first, confirm red, then implement:

1. `test_package_manifest_pins_node_tools`: read `package.json` at the skill
   root; assert the five packages are present in `dependencies`/`devDependencies`
   at the ADR-0017 versions. (Red until the manifest is committed.)
2. `test_lockfile_present_and_pins_match`: assert `package-lock.json` exists and
   its top-level pins for the five tools match `package.json` (drift guard at the
   manifest↔lock level; the capabilities↔lock guard is s1-t2).
3. Manual (recorded in close notes, since it needs npm + network): on a clean
   `cache_root()`, run `setup.sh`, confirm the `npm ci` branch ran and
   `--capabilities` shows the four Node analyzers `available`.
