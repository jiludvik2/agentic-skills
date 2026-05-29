---
id: qa-analyzer-coverage-findings
kind: runbook
project: code-review
created: 2026-05-29
updated: 2026-05-29
verified-on: 2026-05-29
tags: [qa, findings, ga-readiness]
sources: [sdlc/docs/qa/analyzer-coverage/run_smoke.py]
---

# Analyzer-coverage findings — 2026-05-29

Defects surfaced by the analyzer-coverage smoke test (`run_smoke.py`). Severity
uses the SDLC taxonomy (Critical / Important / Minor). **11/13 analyzers passed;
2 are broken by real defects.** Several findings bear directly on GA readiness.

The environment under test: macOS, Node 24.14.1, pinned Node tools
(knip 5.0.0, jscpd 4.0.5, dependency-cruiser 16.0.0, eslint 9), semgrep/gitleaks/
trivy on PATH, Trivy DB pre-fetched.

## Critical

### F1 — `depcruiser` does not run (pinned dep incompatible with Node ≥ 22)
`dependency-cruiser@16.0.0` does `import { R_OK } from "node:fs"`, which Node 24
rejects (`R_OK` is on `fs.constants`, not a named export of `node:fs`):

```
SyntaxError: The requested module 'node:fs' does not provide an export named 'R_OK'
  at .../dependency-cruiser/src/cli/utl/assert-file-existence.mjs:1
```

The TypeScript/JS coupling capability is dead on any modern Node. Fix: bump
dependency-cruiser to a version that imports `R_OK` from `node:fs/constants`
(≥ ~16.3) and pin it in a committed lockfile (see F5). The detection logic is
fine once it runs.

### F2 — `jscpd` adapter writes JSON to `/dev/stdout`, which jscpd `mkdir`s
The adapter runs `jscpd --reporters json --output /dev/stdout` and reads stdout.
jscpd treats `--output` as a **directory** and calls `mkdir` on it:

```
Error: EEXIST: file already exists, mkdir '/dev/stdout'
```

Reproduced on the **pinned** jscpd 4.0.5 — not a version-drift issue. jscpd
*detects the duplication correctly* when `--output` points at a real temp
directory (1 clone found); only the stdout plumbing is broken. Fix: write the
report to a `TemporaryDirectory` and read `<dir>/jscpd-report.json` (as the
trivy/gitleaks adapters already do), instead of `/dev/stdout`.

## Important

### F3 — `semgrep` has no working rule source out of the box
Two compounding problems:
1. `scripts/setup.sh`'s prefetch step writes **0** semgrep rules
   (`cache/semgrep/rules` is never populated).
2. With no local cache the adapter falls back to `--config auto`, but it also
   passes `--metrics off`, and semgrep refuses the combination:
   `Cannot create auto config when metrics are off`.

Net: a fresh install produces **zero** semgrep findings (it errors). The adapter
logic is correct — this test passes semgrep by provisioning a local ruleset
(`semgrep-rules/` → cache), proving the `--config <dir>` path works. Fix: make
the prefetch actually vendor a semgrep ruleset, and/or repair the `auto`
fallback (drop `--metrics off` when falling back to `auto`, or fail loudly
instead of silently). Also: `--x-ignore-semgrepignore-files` is not a recognized
flag in the installed semgrep (warning only, non-fatal).

### F5 — No JS/TS toolchain manifest or lockfile in the repo
`setup.sh` logs `Node dependencies (skipped — no package.json/package-lock.json
yet)`. The four Node analyzers (eslint, knip, jscpd, depcruiser) are neither
vendored nor version-pinned anywhere except the `version` strings in
`capabilities.json`. Installing "latest" drifts from what the adapters assume
(knip's JSON schema changed — see F4; depcruiser/Node compat — see F1). The JS
toolchain is effectively unshippable until a committed `package.json` +
lockfile pins these versions and `setup.sh` vendors them.

## Minor

### F4 — `knip` adapter drops unused-*export* findings (schema mismatch)
The adapter reads `data["exports"]`, but knip 5.0.0's JSON report is
`{"files": [...], "issues": [{... "exports": [...] ...}]}` — exports are nested
under `issues[]`, not top-level. Top-level `data["files"]` (unused files) maps
correctly, so the analyzer still reports (4 unused-file findings here), but every
unused-*export* is silently lost. Fix: read exports from `issues[].exports`.

### F6 — `pydeps` high-fan-out finding under-counts imports
`hub.py` imports 12 siblings, but pydeps' resolved graph reports `fan_out = 5`
for it, below the `_HIGH_FAN_OUT_THRESHOLD = 10`, so no finding fires. The
coupling **metrics** populate correctly (the analyzer's primary output), so this
test asserts metrics rather than the threshold finding. Worth confirming the
fan-out threshold is reachable with realistic code, or the finding may rarely
fire in practice.

### F7 — README install section omits the external-analyzer requirement
A bare `pip install polyreview` ships only the Python analyzers; the Node tools
and gitleaks/trivy are silently unavailable. A drafted fix to `README.md`'s
Install section is staged in the working tree (pending operator sign-off).

## Passing cleanly (8)

`bandit` (8), `gitleaks` (1), `trivy` (8), `vulture` (22), `cohesion` (2),
`radon` (metrics, max_cc=13), `eslint` (2), `schemathesis` (1) — all produced
their expected signal with no caveats. `semgrep`, `knip`, `pydeps` pass with the
caveats noted above.

## GA-readiness implication

The original GA question was "is `polyreview` ready to publish?" This test says:
**the Python analyzers and schemathesis are solid, but the JS/TS toolchain is not
shippable** (F1, F2, F5) and **semgrep is broken out of the box** (F3). A GA that
advertises TypeScript coverage and security scanning would mislead users until
F1–F3 and F5 are fixed.
