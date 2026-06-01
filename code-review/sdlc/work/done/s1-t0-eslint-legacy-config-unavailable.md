---
id: s1-t0-eslint-legacy-config-unavailable
kind: task
project: code-review
status: done
parent: s1-eslint-legacy-config-unavailable
sources: [s1-eslint-legacy-config-unavailable.md]
created: 2026-06-01
updated: 2026-06-01
tags: [analyzer, eslint, availability, adr-0019]
---

# Task — eslint: legacy-only config → `unavailable`, not `error`

## Outcome

The eslint adapter reports `unavailable` (clean skip, ADR-0019) when a target's only
discoverable ESLint config is a legacy `.eslintrc*` that the vendored ESLint v9
(flat-config-only) cannot consume — instead of running eslint and surfacing its
exit-2 crash as `error`.

## Acceptance criteria

- JS target with only a legacy `.eslintrc*` (no flat config on the upward path) →
  `unavailable`, reason names the cause (e.g. "ESLint v9 requires a flat config
  (eslint.config.*); target ships only legacy .eslintrc — unsupported").
- JS target with a discoverable flat config → runs normally (exit 0/1 → `ok`).
- JS target with no config of any kind → `unavailable` (unchanged behaviour).
- A genuine eslint crash (exit 2) with a **flat** config present → still `error`
  (the ADR-0019 boundary is preserved; we don't over-swallow real failures).

## Test specification (write first, confirm RED)

In `tests/` (adapter-level, async). Fixtures under `tests/fixtures/eslint-config/`:

1. `legacy-only/` — one `.js` file + `.eslintrc.json`, no `eslint.config.*`.
   Assert adapter returns `status == "unavailable"` and reason mentions flat-config.
   **RED today:** returns `error` (eslint exits 2).
2. `flat/` — one `.js` file + minimal `eslint.config.js`. Assert `status == "ok"`
   (regression guard — real run; mark as needing the vendored eslint binary, in line
   with existing JS-adapter integration tests).
3. `no-config/` — one `.js` file, no config. Assert `unavailable` (unchanged).
4. Unit: the config-detection helper distinguishes *flat present* from *legacy-only*;
   legacy-only does not count as "lintable" for vendored v9.

## Implementation notes

- `code_review/adapters/eslint.py`: split `_has_eslint_config` into flat-vs-legacy
  detection (the `_FLAT_CONFIG_NAMES` / `_LEGACY_CONFIG_NAMES` split already exists).
  Decision branch at the call site (line ~88): flat found → proceed; legacy-only →
  `unavailable`; none → `unavailable` (current message).
- Update the adapter's lead comment (lines 11-14) which currently assumes legacy
  configs work ("a project with none and no legacy .eslintrc exits 2") — that
  assumption is the bug.
- Keep the message actionable (host can add a flat config). Don't attempt to *support*
  legacy configs — ESLint v9 dropped them; `ESLINT_USE_FLAT_CONFIG=false` is gone.
- Gates: `.venv/bin/pytest`, `.venv/bin/ruff check .`, `.venv/bin/mypy code_review`
  (uv run panics under sandbox — use .venv/bin directly).
