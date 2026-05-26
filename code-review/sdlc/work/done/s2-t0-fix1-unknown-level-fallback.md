---
id: s2-t0-fix1-unknown-level-fallback
kind: task
project: code-review
status: done
parent: s2-aggregator-and-severity-mapping
sources: [s2-t0-severity-mapping-table.md]
created: 2026-05-26
updated: 2026-05-26
---

# s2-t0-fix1 — correct unknown-level fallback and remove dead dict

## Finding (reviewer, round 1)

**Important** — `severity.py:46`: final fallback `_SDLC_SEVERITY_BY_PROPS.get(norm_props, "nit")` returns `"important"` for `(unknown_level, "high")`, contradicting the task AC: "Unknown `level` strings are treated as `none` (→ `nit`)". The `properties_severity=="critical"` guard at line 37 already handles the story-spec OR-rule, so unknown levels that reach line 46 should unconditionally return `"nit"`.

**Minor** — `_SDLC_SEVERITY_BY_LEVEL` (lines 3–8) is defined but never consulted.

## Fix

1. Replace line 46 with `return "nit"`.
2. Remove the unused `_SDLC_SEVERITY_BY_LEVEL` dict (lines 3–8).
3. Add a parametrised test case `("fatal", "high")` → `"nit"` asserting the corrected behaviour explicitly.

## Acceptance criteria

- `map_severity("fatal", "high")` → `"nit"` (unknown level, non-critical props → nit).
- `map_severity("fatal", "critical")` → `"critical"` (unknown level, but critical props → critical via OR-rule at line 37).
- `_SDLC_SEVERITY_BY_LEVEL` is removed.
- All 12 existing table + fuzz tests still pass.
