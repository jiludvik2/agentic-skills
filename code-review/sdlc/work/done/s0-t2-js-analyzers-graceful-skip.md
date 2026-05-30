---
id: s0-t2-js-analyzers-graceful-skip
kind: task
project: code-review
status: active
parent: s0-analyzer-adapter-robustness
sources: [post-ga-self-review-findings.md, code_review/adapters/eslint.py, code_review/adapters/knip.py, adr-0019-analyzer-unavailable-vs-error.md]
status: done
created: 2026-05-30
updated: 2026-05-30
tags: [eslint, knip, adapter, graceful-skip, minor]
notes:
  - "Verify Minor (applied in-green-bar): knip integration assertion tightened from a 3-way disjunction to `== unavailable` (fixture deterministically lacks top-level package.json; guard returns before invoking knip)."
  - "Review MINOR (deferred): knip and eslint compute 'containing project dir' by different idioms (knip: dirname; eslint: commonpath+dirname fallback). Consider a shared js_base `target_dir(path)` helper."
  - "Review MINOR (deferred): knip inspects only target_paths[0]; eslint's has_js_files scans all target_paths — multi-target disagreement. Pre-existing (cwd was already target_paths[0]); knip is whole-project by nature. Document single-root or scan for first package.json dir."
  - "Review MINOR (pre-existing, not introduced here): empty_sarif(tool) vs sarif={} convention across non-ok statuses is inconsistent project-wide. Pick one and document on AnalyzerOutput.sarif."
  - "Review FORWARD-LOOKING (out of scope for t2): ADR-0019 §Decision names jscpd as a third JS-only tool that should report `unavailable` on no-JS targets; jscpd.py does not yet use has_js_files. Surface at story s0 boundary as a candidate follow-up task (the shared has_js_files helper makes it a small change)."
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
