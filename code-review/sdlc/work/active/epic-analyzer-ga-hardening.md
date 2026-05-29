---
id: epic-analyzer-ga-hardening
kind: epic
project: code-review
status: active
children:
  - s0-semgrep-rule-source
  - s1-js-toolchain-manifest
  - s2-jscpd-output-plumbing
  - s3-depcruiser-node-compat
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-29
updated: 2026-05-29
tags: [ga-readiness, analyzers, semgrep, javascript, typescript, qa]
---

# Epic: Analyzer GA Hardening

Make every analyzer `polyreview` advertises actually work on a fresh install,
before the GA publish. The analyzer-coverage smoke test
(`sdlc/docs/qa/analyzer-coverage/`) ran all 13 adapters against synthetic code on
2026-05-29 and found **11/13 working, 2 broken, and semgrep broken out of the
box** — see `FINDINGS.md`. This epic fixes the four ship-blockers (F1, F2, F3,
F5). The two Minor caveats (F4 knip unused-export mapping, F6 pydeps fan-out
threshold) and the README install note (F7, already staged) are out of scope —
recorded in FINDINGS.md for opportunistic cleanup.

## Why this is an epic, not a single story

The four fixes split along two independent axes and one has a hard dependency:

- **Python side (independent):** s0 — semgrep has no working rule source on a
  fresh install (prefetch ships 0 rules; the `--config auto` fallback is
  incompatible with the adapter's own `--metrics off`).
- **JS/TS side (sequenced):** s1 — there is no committed `package.json`/lockfile,
  so the four Node analyzers are unpinned and unvendored and `setup.sh` skips
  them entirely. s1 establishes the manifest + lockfile + vendoring. s2 (jscpd
  adapter writes to `/dev/stdout`, which jscpd `mkdir`s) is an adapter-code fix
  independent of s1. s3 (dependency-cruiser 16.0.0 crashes on Node ≥22) is a
  version bump that lands in **s1's lockfile**, so s3 depends on s1.

Together they answer: "does a fresh `polyreview` install actually deliver the
TypeScript coverage and security scanning the capabilities advertise?"

## What's in scope

- A real semgrep rule source shipped by `setup.sh` (or a fixed/loud `auto`
  fallback) so security scanning produces findings on a clean install (F3).
- A committed JS/TS toolchain manifest + lockfile pinning eslint, knip, jscpd,
  dependency-cruiser, and the SARIF formatter, vendored by `setup.sh` (F5).
- jscpd adapter reads its JSON report from a temp file, not `/dev/stdout` (F2).
- dependency-cruiser pinned to a Node-≥22-compatible version + the adapter
  supplying (or documenting) the required cruise config (F1).
- The analyzer-coverage smoke test reaching **13/13 without the harness manually
  provisioning anything** — i.e. a clean `setup.sh` is sufficient.

## What's intentionally not in scope

- F4 (knip unused-export mapping) and F6 (pydeps fan-out threshold) — Minor;
  FINDINGS.md notes them.
- F7 (README install prerequisites) — already drafted in the working tree.
- New analyzers, new languages, or LLM review (sibling `intent-review`).
- The `ccglass-traffic-analysis` branch's `analyze_ccglass.py` lint debt
  (pre-existing, unrelated).

## Validation

This epic is plumbing, not a hypothesis: the deliverables are settled by AC
pass/fail. The cross-cutting acceptance gate is the analyzer-coverage smoke test
going green at 13/13 from a clean checkout + `setup.sh`, with no manual rule
provisioning, pinned-version installs, or per-analyzer cwd hacks needed by the
harness.

## Stories

- **s0 — semgrep rule source.** Ship a working offline ruleset; fix/guard the
  `auto` + `--metrics off` incompatibility; drop the unsupported `--x-` flag.
- **s1 — JS toolchain manifest.** Committed `package.json` + lockfile + setup.sh
  vendoring + `stack-pins.md` Node range. Foundational for s3.
- **s2 — jscpd output plumbing.** Temp-dir report read instead of `/dev/stdout`.
- **s3 — depcruiser Node compat.** Node-≥22-compatible pin + cruise config.
  Depends on s1.
