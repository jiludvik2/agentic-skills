---
id: s0-analyzer-adapter-robustness
kind: story
project: code-review
status: active
parent: epic-analyzer-polish
children:
  - s0-t0-bandit-stdout-progress-bar
  - s0-t1-eslint-no-flat-config
  - s0-t2-js-analyzers-graceful-skip
  - s0-t3-schemathesis-surface-exec-error
  - s0-fix1-jscpd-unavailable-on-no-js
  - s0-fix2-unavailable-end-to-end-coverage
sources: [post-ga-self-review-findings.md]
created: 2026-05-30
updated: 2026-05-30
tags: [analyzer, adapter, robustness, bandit, eslint, sast]
---

# s0 — analyzer adapter robustness on real-world repos

## Summary

Four adapter fixes so a full review of a real repository doesn't silently lose
coverage. Two are **Important** crashes (bandit, eslint); two are **Minor** cleanups
(JS-on-no-JS skip, schemathesis error-swallowing). The unavailable-vs-error contract
that t1 and t2 both rely on is settled in **ADR-0019** (co-located, this story).

## Acceptance criteria

### Scenario: bandit parses output despite a progress bar on stdout
- **Given** a bandit version that prints `Working... ━━━ 100%` to stdout before its JSON
- **When** the bandit adapter runs against a Python target
- **Then** it parses the findings (status `ok`), not `status: error` "invalid JSON".

### Scenario: eslint on a JS project with no flat config does not crash
- **Given** a JS target with no `eslint.config.*` and no `.eslintrc`
- **When** the eslint adapter runs
- **Then** per ADR-0019 it returns `status: unavailable` with a reason naming the
  missing flat config (or runs a built-in default config, if ADR-0019 chooses that) —
  never a bare `eslint exited 2`.

### Scenario: JS analyzers skip cleanly on a target with no JS
- **Given** a target tree with no JS/TS files (and/or no `package.json`)
- **When** eslint / knip run
- **Then** per ADR-0019 they return `status: unavailable` with a reason, not `error`.

### Scenario: schemathesis surfaces an unexpected execution error
- **Given** `call_and_validate` raises a non-`FailureGroup` exception for an operation
- **When** the schemathesis adapter runs
- **Then** it emits a `schemathesis.execution-error` finding naming the operation,
  rather than silently returning no failures for it.

### Scenario: a full review of a Python repo yields bandit findings; of a JS repo, no spurious analyzer errors
- **Given** a real Python repo (e.g. a vuln-app fixture) and a real JS repo
- **When** `polyreview run --depth full` runs
- **Then** bandit reports findings on the Python repo, and no analyzer reports
  `status: error` purely for "wrong language / no config" reasons.

## Tasks

- **s0-t0** — bandit: tolerate a progress-bar prefix on stdout (F3, Important).
- **s0-t1** — eslint: no-flat-config handling per ADR-0019 (F4, Important).
- **s0-t2** — JS analyzers: graceful `unavailable` on no-JS targets per ADR-0019 (F2, Minor).
- **s0-t3** — schemathesis: surface execution errors as findings (F1, Minor).

ADR-0019 (co-located) must be operator-ratified before t1/t2 implement against it.

## Deferred

- **F5 — semgrep ruleset breadth.** SAST coverage is thin; broadening the ruleset is
  an ADR-0016 revisit, tracked as candidate story s1 on the epic. Not in this story.
