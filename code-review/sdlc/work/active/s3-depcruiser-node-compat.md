---
id: s3-depcruiser-node-compat
kind: story
project: code-review
status: active
parent: epic-analyzer-ga-hardening
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-29
updated: 2026-05-29
tags: [dependency-cruiser, coupling, node, adapter, ga-readiness]
---

# s3 — dependency-cruiser Node compatibility

## Summary

The TypeScript/JS coupling analyzer does not run. The pinned
`dependency-cruiser@16.0.0` does `import { R_OK } from "node:fs"`, which Node ≥22
rejects (`R_OK` is on `fs.constants`, not a named export of `node:fs`):

```
SyntaxError: The requested module 'node:fs' does not provide an export named 'R_OK'
  at .../dependency-cruiser/src/cli/utl/assert-file-existence.mjs:1
```

So coupling detection is dead on any modern Node (FINDINGS.md F1). Separately,
the adapter passes **no** `--config`, and dependency-cruiser aborts without one
(`Can't open a config file ...`).

Fix: pin dependency-cruiser to a version that runs on the supported Node range
(imports `R_OK` from `node:fs/constants`, ≈ ≥16.3) **in s1's lockfile**, and have
the adapter supply (or the install provision) the cruise config it requires. The
detection logic is correct once it runs and a config is present (verified
manually: circular deps are flagged).

## Depends on

- **s1-js-toolchain-manifest** closed. The compatible version pin lands in s1's
  committed lockfile; s3 starts after s1 is in `/sdlc/work/done/`.

## Use case

- **As a** host operator analyzing a TypeScript project
- **I want** `polyreview --review maintainability --depth full` to report
  circular dependencies
- **so that** the advertised coupling capability actually works.

## Acceptance criteria

### Scenario: dependency-cruiser runs on the supported Node range
- **Given** the supported Node range from `stack-pins.md`
- **When** the depcruiser adapter runs after `setup.sh`
- **Then** dependency-cruiser executes without the `R_OK` SyntaxError (pinned to
  a compatible version in s1's lockfile).

### Scenario: the adapter supplies the required config
- **Given** a target with no `.dependency-cruiser.cjs`
- **When** the adapter runs
- **Then** it provides a config (bundled default, generated, or documented host
  requirement) so dependency-cruiser does not abort on a missing config file.

### Scenario: circular dependencies are reported
- **Given** the analyzer-coverage smoke test
- **When** the depcruiser case runs against `fixtures/js/src/cycle_a.ts` ↔
  `cycle_b.ts`
- **Then** it returns ≥1 circular-dependency finding and the case passes.

### Scenario: capabilities version matches
- **Given** the bumped pin
- **When** `capabilities.json`'s dependency-cruiser `version` is checked
- **Then** it matches the version pinned in s1's lockfile.
