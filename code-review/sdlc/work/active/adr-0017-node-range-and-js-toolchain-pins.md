---
id: adr-0017-node-range-and-js-toolchain-pins
kind: decision
project: code-review
status: accepted
parent: s1-t0-adr-node-range-and-js-pins
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md, s1-js-toolchain-manifest.md]
created: 2026-05-29
updated: 2026-05-29
tags: [node, javascript, typescript, pins, packaging, ga-readiness]
---

# ADR-0017: Node version range & JS toolchain pins

## Status

Accepted. Resolves FINDINGS.md F5 (no JS/TS toolchain manifest or lockfile)
under `epic-analyzer-ga-hardening` / s1, and sets the runtime range that
F1 (depcruiser/Node, s3) must satisfy.

## Context

The four Node analyzers (`eslint`, `knip`, `jscpd`, `dependency-cruiser`) and the
eslint SARIF formatter (`@microsoft/eslint-formatter-sarif`) are neither
version-pinned nor vendored. `scripts/setup.sh` logs `Node dependencies (skipped
— no package.json/package-lock.json yet)` and only takes its `npm ci` branch when
a manifest + lockfile exist at the skill root (`scripts/setup.sh:74-83`).
Installing "latest" drifts from what the adapters assume — `dependency-cruiser`
16 breaks on modern Node (F1 observed the `R_OK` `SyntaxError` on Node 24; the
exact lower break boundary is unconfirmed), and knip's JSON schema changed
across majors (F4).
There is no recorded supported Node range; `stack-pins.md` only says "Node | via
`npm ci`".

A clean `setup.sh` must produce a known-good, reproducible Node toolchain, and
that toolchain must work on the Node versions operators actually run.

## Decision

1. **Supported Node range: 20 LTS and 22 LTS, matrix-tested** (operator-confirmed
   2026-05-29). Both majors are supported and CI exercises both (s1-t3). Node 20
   is chosen for breadth (it is still in maintenance); Node 22 is the current LTS
   and the forward target. Tool versions are selected to install and run on
   **both** majors. Recorded in `stack-pins.md`.

2. **`package.json` carries caret (`^N`) major pins; exact patches are locked in
   `package-lock.json`** — mirroring the *spirit* of the Python policy (ADR-0013:
   resolvable range in the manifest, exact patch in the lock). Note the npm idiom
   differs deliberately from Python's unbounded `>=X.Y`: `^9` means "the 9.x
   major" (`>=9 <10`), a major-bounded floor — s1-t1 must keep the caret form,
   not rewrite it to `>=9`. The five packages:

   | Package | manifest pin | locked patch | notes |
   |---|---|---|---|
   | `eslint` | `^9` | resolved in s1-t1 | flat-config era; supports Node 20+22 |
   | `knip` | `^5` | resolved in s1-t1 | JSON output schema the adapter targets (F4) |
   | `jscpd` | `^4` | resolved in s1-t1 | output plumbing fix is s2 (F2) |
   | `dependency-cruiser` | `^16.10.4` | `16.10.4` (s3-t0) | 16.0.0 broke on modern Node (F1, seen on Node 24); s3-t0 bumped to 16.10.4 in-place — stays in major 16 (caret intent) and floors at the fix |
   | `@microsoft/eslint-formatter-sarif` | `^3` | resolved in s1-t1 | SARIF formatter compatible with eslint 9 |

   The exact patch versions are whatever `npm install` resolves into the
   committed `package-lock.json` in s1-t1; the lockfile — not `capabilities.json`
   — is the single source of truth for installed versions (s1-t2 adds a
   drift guard between the two).

3. **depcruiser cross-Node validation, resolved in s3-t0.** s1-t1 pinned a
   candidate (`16.0.0`) so `npm ci` resolved a complete lockfile; s3-t0 bumped it
   to **`16.10.4`** within the same lockfile (F1). **Empirical Node-fs/constants
   floor = `16.10.2`:** up to and including `16.10.1`,
   `src/cli/utl/assert-file-existence.mjs` does
   `import { accessSync, R_OK } from "node:fs"`, which Node ≥22 rejects (`R_OK`
   lives on `fs.constants`, not as a named export of `node:fs`); `16.10.2`
   switched to `import { accessSync, constants } from "node:fs"`. Boundary
   confirmed against the npm tarballs on Node 24 (`16.10.1` broken, `16.10.2`
   fixed) — correcting the earlier "≈16.3" estimate in the FINDINGS/story. The
   pin floors at `16.10.4` (latest 16.x) and stays inside the `^16` caret. The
   full circular-dependency integration test stays `xfail(strict)` until s3-t1
   supplies the cruise config; s3-t0 only clears the `R_OK` SyntaxError.

4. **Lockfile location: the skill root** — `package.json` + `package-lock.json`
   under `.claude/skills/code-review/`. `setup.sh` already copies both into
   `cache_root()` and runs `npm ci` there, so binaries land in
   `cache_root()/node_modules/.bin` where `js_base.node_binary()` resolves them.

5. **Node tooling is NOT shipped in the wheel.** The PyPI wheel carries only the
   Python package; the Node toolchain is a source-checkout / `setup.sh`
   prerequisite. The `package.json`/lock are bundle files, not wheel data.

## Consequences

- A clean `setup.sh` produces a reproducible Node toolchain; the four Node
  analyzers probe `available` (s1-t1), closing F5's manifest/lockfile gap.
- CI gains a Node 20+22 matrix that runs the Node-analyzer integration tests
  rather than skipping them (s1-t3 / F9); F1/F2/F8 regressions become visible.
- `dependency-cruiser` is pinned to `^16.10.4` (s3-t0) — past the F1 `R_OK`
  break on modern Node. The cruise-config + circular-detection work is s3-t1.
- Node-tool version freshness is a deliberate, reviewed lockfile bump (like
  `uv.lock`), reconciled into `stack-pins.md` in the same commit (SDLC rule #1b).
- All five packages must clear the `stack-pins.md` license floor (no AGPL); the
  license audit (`scripts/license_audit.py`) covers them.
