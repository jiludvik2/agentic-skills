---
id: s0-fix1-jscpd-unavailable-on-no-js
kind: task
project: code-review
status: done
parent: s0-analyzer-adapter-robustness
sources: [s0-analyzer-adapter-robustness.md, adr-0019-analyzer-unavailable-vs-error.md, code_review/adapters/jscpd.py, code_review/lang_select.py]
created: 2026-05-30
updated: 2026-05-30
tags: [jscpd, adapter, graceful-skip, story-level-fix, important]
---

# s0-fix1 — jscpd: graceful `unavailable` on no-JS targets (story-level Review, Important)

## Origin

Round-1 fix task from the **s0 story-level Review** (Important #1). ADR-0019 §Decision
names jscpd alongside eslint/knip as a JS-only tool that must report `unavailable`
on a no-JS target, but t2 updated only eslint+knip — jscpd was omitted.

## Why this is correct (operator-confirmed intent)

jscpd is a language-agnostic copy-paste detector *by capability* (it will detect
Python/Ruby/Java duplication), but in polyreview it is **intentionally scoped to
JavaScript/TypeScript**: `lang_select.py` groups it in `_JS_ADAPTERS`, and its
`capabilities.json` entry pins `languages: [javascript, typescript]`. Duplication
detection is a deliberately JS-only feature (the `_PYTHON_ADAPTERS` set has no
copy-paste detector) — the operator restricted scope to avoid functional overlap
between scanners. So suppressing jscpd on a no-JS target is **consistent with intent,
not a regression**: Python-duplication-via-jscpd was never an offered feature.

The selection layer already filters jscpd out for non-JS *language-driven* runs; this
task is the **adapter-level defense-in-depth** for the all-analyzer / `--target` path
that bypasses language selection (the path the post-GA dogfood used to run jscpd on
PyGoat). Mirrors exactly what s0-t2 did for eslint/knip via the shared `has_js_files`.

## Acceptance criteria

- **Given** a target tree with no JS/TS files
- **When** the jscpd adapter runs
- **Then** it returns `status: unavailable` with a reason ("no JavaScript/TypeScript
  files in target"), not `ok`-with-out-of-scope-Python-findings and not `error`.
- **Given** a target WITH JS files
- **When** it runs
- **Then** it behaves as today (no regression) — duplicates parsed to SARIF.

## Test specification (tests-first)

In `tests/test_adapters/test_jscpd.py`:
1. `test_jscpd_unavailable_without_js`: a target dir with only non-JS files (e.g. a
   `.py`) → `status: unavailable`, reason names JavaScript/TypeScript; jscpd not
   invoked.
2. Regression: existing JS-target tests still pass unchanged.

Confirm RED first. Add the `has_js_files` guard after the `not request.target_paths`
guard, returning `js_unavailable("jscpd", ...)` — same idiom as eslint.py.
