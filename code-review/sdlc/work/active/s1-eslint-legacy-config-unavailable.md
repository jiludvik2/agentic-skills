---
id: s1-eslint-legacy-config-unavailable
kind: story
project: code-review
status: active
parent: epic-analyzer-correctness
sources: [dogfood-2026-06-01-analyzer-defects.md]
created: 2026-06-01
updated: 2026-06-01
tags: [analyzer, eslint, availability, adr-0019, flat-config]
---

# Story — eslint reports `error` on legacy-config repos (should be `unavailable`)

## Discovered

2026-06-01 dogfooding. `polyreview run --analyzer eslint --target express/lib`
returns **status: error, exit 2** with stderr:

> ESLint couldn't find an eslint.config.(js|mjs|cjs) file. From ESLint v9.0.0, the
> default configuration file is now eslint.config.js. If you are using a .eslintrc.*
> file, please follow the migration guide...

So a real, mainstream repo (express) produces a spurious red in an otherwise-green
review — the exact outcome ADR-0019 and the eslint adapter's `unavailable` handling
were built to prevent.

## Problem

The adapter's `_has_eslint_config(anchor)` (`code_review/adapters/eslint.py`) walks
upward looking for **either** a flat config (`eslint.config.*`) **or** a legacy
config (`.eslintrc`, `.eslintrc.js`, `.eslintrc.json`, …). Its comment assumes legacy
configs still work ("a project with none **and no legacy .eslintrc** exits 2").

But the vendored ESLint is **v9.39.4**, which **dropped legacy `.eslintrc*` support
entirely** (flat config only). So a target that ships only a legacy `.eslintrc*`
(express) passes the availability check → the adapter runs eslint → v9 can't consume
the legacy config → exits 2 → mapped to `error` (the adapter tolerates only 0/1).

The availability check and the vendored ESLint's actual capabilities are out of sync:
legacy-config presence is treated as "lintable" when v9 cannot lint it.

## Acceptance criteria

- A target whose only ESLint config is legacy `.eslintrc*` (no flat config
  discoverable) → eslint reports **`unavailable`** with an actionable reason (e.g.
  "ESLint v9 requires flat config (eslint.config.*); target ships only legacy
  .eslintrc — unsupported"), **not** `error`.
- A target with a discoverable flat config still runs normally (0/1 → ok).
- A target with no config of any kind still reports `unavailable` (unchanged).
- A genuine eslint crash with a *flat* config present still surfaces as `error`
  (don't over-swallow real failures — the ADR-0019 boundary is preserved).

## Test specification (defined before implementation)

- RED: a fixture dir containing JS + only a `.eslintrc.json` (no flat config); assert
  the adapter returns `unavailable`, not `error`. Today this returns error (exit 2).
- A fixture with a valid `eslint.config.js` → asserts `ok` (regression guard).
- A fixture with JS and no config at all → asserts `unavailable` (unchanged).
- Unit: `_has_eslint_config` (or its replacement) distinguishes flat-only from
  legacy-only; legacy-only does not count as "lintable" for vendored v9.

## Notes

- Small, single-adapter fix. Likely: drop `_LEGACY_CONFIG_NAMES` from the
  availability gate (or report legacy-only as unavailable with a distinct reason).
- Decide whether to mention the migration path in the unavailable reason (the host
  could add a flat config). Keep the message actionable.
- Ties to the broader truth that vendored-tool *capabilities* must match adapter
  *availability* assumptions (cf. the ESLint-needs-ts-parser limitation in s4).
