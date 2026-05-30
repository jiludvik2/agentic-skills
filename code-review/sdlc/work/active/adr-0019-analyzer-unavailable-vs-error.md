---
id: adr-0019-analyzer-unavailable-vs-error
kind: decision
project: code-review
status: proposed
parent: s0-analyzer-adapter-robustness
sources: [post-ga-self-review-findings.md]
created: 2026-05-30
updated: 2026-05-30
tags: [adr, analyzer, contract, status, unavailable, error]
---

# ADR-0019: `unavailable` vs `error` — the analyzer "can't run here" contract

## Status

**Proposed** — needs operator ratification before s0-t1/s0-t2 implement against it.

## Context

`AnalyzerOutput.status` today is effectively `ok | error | timeout`. Adapters
conflate two very different situations under `error`:

1. **The analyzer cannot meaningfully run against this target** — e.g. eslint on a
   project with no flat config, or eslint/knip on a target with no JS at all, or a
   tool whose required binary isn't installed.
2. **The analyzer ran and failed unexpectedly** — a crash, an output-parse failure,
   a timeout, a non-zero exit it didn't anticipate.

The post-GA dogfood showed the cost: eslint `exited 2` (no flat config) and
eslint/knip erroring on a pure-Python target both surface as `error`, polluting an
otherwise-clean review with red analyzers and reading as "polyreview is broken" when
in fact there was simply nothing for that analyzer to do. (The capability probe
already has a third notion — `unavailable` — for a missing binary; this ADR extends
it to "nothing to analyze here.")

## Decision (proposed)

**Introduce a first-class `unavailable` outcome for "this analyzer cannot meaningfully
run against this target," distinct from `error` ("it tried and failed").**

- `status: "unavailable"` carries a human-readable `error`/reason string (e.g.
  "no ESLint flat config found under <target>", "no JavaScript/TypeScript files in
  target"). It is a **clean skip**: the aggregator treats it like a not-selected
  analyzer — no findings, does **not** mark the run failed, does **not** set a
  non-zero CLI exit on its own.
- `status: "error"` stays for genuine failures (crash, parse failure, timeout-as-error)
  and continues to be surfaced as a real problem.
- Adapters detect "can't run here" **at run time** (cheapest correct spot — the
  selector has no per-target language signal for `--target`), before invoking the
  external tool where possible:
  - **eslint**: no `eslint.config.*` / `.eslintrc` discoverable under the target →
    `unavailable`. *(Chosen over synthesizing a default flat config: linting a
    project with rules it never opted into produces opinionated noise. A future
    `--eslint-default-config` opt-in could add the run-anyway behaviour.)*
  - **eslint / knip / jscpd (JS-only)**: target has no JS/TS files (and, for knip,
    no `package.json`) → `unavailable`.

## Consequences

- s0-t1 (eslint no-flat-config) and s0-t2 (JS-on-no-JS) implement this contract.
- The consolidated output and any consumer gating must treat `unavailable` as
  benign. Update the response schema/contract docs if `status` is enumerated there.
- A genuinely broken adapter still reports `error` and is still loud — the signal
  that matters is preserved.

## Alternatives considered

- **(a) eslint synthesizes a default flat config and runs anyway.** Rejected as the
  default (noise); recorded as a possible future opt-in.
- **Detect language in the selector and never select JS analyzers for non-JS
  targets.** Rejected for now: `--target <path>` carries no language signal until the
  files are walked, and `--diff` language detection is a separate concern; run-time
  detection in the adapter is the smaller, correct change.

## Open question for the operator

Ratify the core decision (introduce `unavailable` as a clean skip) and the eslint
choice (graceful skip vs default-config). t1/t2 are blocked on this.
