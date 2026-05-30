---
id: s0-t2-js-analyzers-graceful-skip
kind: task
project: code-review
status: active
parent: s0-analyzer-adapter-robustness
sources: [post-ga-self-review-findings.md, code_review/adapters/eslint.py, code_review/adapters/knip.py, adr-0019-analyzer-unavailable-vs-error.md]
created: 2026-05-30
updated: 2026-05-30
tags: [eslint, knip, adapter, graceful-skip, minor]
---

# s0-t2 — JS analyzers: graceful `unavailable` on no-JS targets (F2)

## Outcome

JS-only analyzers (eslint, knip) report `status: unavailable` with a reason — not
`status: error` — when run against a target with no JS/TS (and, for knip, no
`package.json`). A Python-only review stops showing spurious red analyzer errors.

**Per ADR-0019; share its contract with s0-t1.**

## Root cause (confirmed)

On a pure-Python target (PyGoat / our own `code_review`), `knip` errors "Unable to
find package.json" and `eslint` errors — both surface as `status: error` though
there is simply no JS to analyse.

## Acceptance criteria

- **Given** a target tree with no JS/TS files (and no `package.json`)
- **When** knip / eslint run
- **Then** each returns `status: unavailable` with a reason ("no package.json under
  target" / "no JavaScript/TypeScript files in target"), not `error`.
- **Given** a target WITH JS files
- **When** they run
- **Then** they behave as today (no regression).

## Test specification (tests-first)

In the respective adapter tests:
1. `test_knip_unavailable_without_package_json`: Python-only target → `unavailable`,
   reason names the missing package.json; not error.
2. `test_eslint_unavailable_without_js`: target with no JS/TS files → `unavailable`.
   (Coordinate with s0-t1's no-flat-config case — distinct reasons, both `unavailable`.)
3. Regression: a JS target still runs each analyzer normally.

Confirm RED first.

## Dependency

ADR-0019 ratified. Implement after / alongside s0-t1 (shared `unavailable` plumbing —
factor the detection so eslint's "no flat config" and "no JS files" reasons are
distinct but both map to `unavailable`).
