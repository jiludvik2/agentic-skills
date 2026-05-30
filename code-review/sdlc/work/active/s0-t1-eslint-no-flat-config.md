---
id: s0-t1-eslint-no-flat-config
kind: task
project: code-review
status: active
parent: s0-analyzer-adapter-robustness
sources: [post-ga-self-review-findings.md, code_review/adapters/eslint.py, adr-0019-analyzer-unavailable-vs-error.md]
created: 2026-05-30
updated: 2026-05-30
tags: [eslint, adapter, flat-config, important]
---

# s0-t1 — eslint: handle a JS project with no flat config (F4)

## Outcome

The eslint adapter stops returning a bare `eslint exited 2` on real JS projects that
have no ESLint-9 flat config (`eslint.config.*`) — the common case for un-migrated
projects. Per **ADR-0019**, it returns `status: unavailable` with a clear reason
(or runs a built-in default config, if the operator ratifies that variant).

**Blocked on ADR-0019 ratification** (graceful-skip vs default-config).

## Root cause (confirmed)

NodeGoat has no `eslint.config.*` and no `.eslintrc`; ESLint 9 requires a flat config
and exits 2. The adapter surfaces a bare `eslint exited 2:` (empty stderr) as
`status: error`.

## Acceptance criteria

- **Given** a JS target with no `eslint.config.*` and no `.eslintrc`
- **When** the eslint adapter runs
- **Then** per ADR-0019: `status: unavailable` with a reason naming the missing flat
  config (default branch), never a bare `eslint exited 2` error.
- **Given** a JS target WITH a valid `eslint.config.*`
- **When** the adapter runs
- **Then** it lints as today (no regression) — findings parsed to SARIF.
- A real eslint crash (config present but eslint errors unexpectedly) still → `error`.

## Test specification (tests-first)

In `tests/test_adapters/test_eslint.py`:
1. `test_eslint_no_flat_config_is_unavailable`: target dir with JS files but no
   eslint config → assert `status: unavailable`, reason mentions flat config; not error.
2. `test_eslint_with_flat_config_lints` (regression): target with a minimal
   `eslint.config.js` + a lint violation → finding parsed, status ok.
3. `test_eslint_unexpected_failure_is_error`: config present, eslint exits non-zero
   for a real reason → `status: error` preserved.

Confirm RED first. Detect "no flat config under target" before/around the eslint
invocation (the adapter already anchors cwd at the target root for config discovery —
add the no-config detection there).

## Dependency

ADR-0019 must be `accepted` (operator-ratified) before implementing — it decides the
graceful-`unavailable` vs default-config behaviour this task encodes.
