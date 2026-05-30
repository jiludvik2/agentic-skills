---
id: s3-depcruiser-node-compat
kind: story
project: code-review
status: done
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

## Plan

Two tasks (depend on s1 closed):

- **s3-t0-pin-depcruiser-node-compatible** — bump the pin in s1's lockfile to a
  Node-fs/constants-compatible version + capabilities version match (past the
  `R_OK` SyntaxError).
- **s3-t1-cruise-config-and-circular-detection** — adapter supplies the cruise
  config + circular-dependency detection green. Depends on s3-t0.

## Closure (2026-05-30)

**CLOSED.** F1 resolved — the dependency-cruiser coupling analyzer runs on the
supported Node range and reports circular dependencies. Two tasks: s3-t0 (pin
16.0.0→16.10.4, `6d0e3b0`) + s3-t1 (adapter self-supplies config + vendor
typescript@^5 + circular detection, `6d75084`). All four story ACs met:
depcruiser runs without the `R_OK` SyntaxError; the adapter supplies the config;
circular deps are reported on the cycle fixture; capabilities version matches the
lockfile. The integration test flipped from `xfail(strict)` to a real pass
(`must_xfail` False in the meta-test). Full suite 381 passed / 1 xfailed (only
eslint/s4 remains); ruff + mypy clean.

**Story-level Review: MINOR-ONLY** (0 Critical/0 Important).
- *Minor (fixed)* — tempdir pattern diverged from jscpd's; added a comment
  explaining the intentional early release + a `prefix=` for parity.
- *Nit (fixed)* — annotated `doNotFollow` in the cruise config.
- *Minor (recorded)* — `capabilities.json` `languages.typescript.version_range`
  (`>=5.0,<6.0`) is hand-maintained with no drift guard. It is a **supported-
  language** claim (what TS *code* polyreview analyses), not a mirror of the
  vendored typescript tool version — so no guard was added (it would conflate two
  concepts). Note: s3 is what makes that `"verified"` claim actually true; the
  vendored `typescript@^5` is what backs `>=5,<6`.
- The known *Minor* — depcruiser's hardcoded SARIF driver-version literal with no
  drift guard (from s3-t0) — carries a keep-in-sync breadcrumb; durable fix
  (derive from capabilities, or extend the guard across all adapters) deferred.

**Supply-chain (rule #26):** the project defines **no** dependency-audit gate
(no `make audit`/Makefile, no pip-audit/npm-audit in CI) → rule #26 is skipped
per its "no gate ⇒ skip until introduced" clause. For the record, `npm audit` on
the vendored JS toolchain reports 5 **pre-existing** transitive vulns (1 high
picomatch ReDoS, micromatch ReDoS, smol-toml DoS) — present in the HEAD lockfile
before s3; not introduced by the pin bumps. The toolchain is wheel-excluded and
runs offline against local code. **Follow-up:** decide before GA whether to wire
an npm-audit gate and/or `npm audit fix` these (own task — out of s3 scope).
