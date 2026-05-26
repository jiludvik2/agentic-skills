---
id: s2-t0-severity-mapping-table
kind: task
project: code-review
status: active
parent: s2-aggregator-and-severity-mapping
created: 2026-05-26
updated: 2026-05-26
---

# s2-t0 — severity.py: SARIF-to-SDLC severity mapping table

## Outcome

`code_review/severity.py` exists with a pure `map_severity(level, properties_severity)` function that maps SARIF `level` + `properties.severity` into the SDLC taxonomy (`critical`, `important`, `minor`, `nit`). All logic lives in this module; adapter code never encodes the mapping inline.

## Acceptance criteria

- `map_severity("error", None)` → `"critical"`
- `map_severity("error", "critical")` → `"critical"` (level takes precedence)
- `map_severity("warning", "important")` → `"important"`
- `map_severity("warning", "high")` → `"important"` (alias)
- `map_severity("warning", None)` → `"minor"` (warning with no extra severity)
- `map_severity("warning", "medium")` → `"minor"` (unrecognised severity string: fallback)
- `map_severity("note", None)` → `"nit"`
- `map_severity("note", "info")` → `"nit"`
- `map_severity("none", None)` → `"nit"` (lowest SARIF level)
- Unknown `level` strings are treated as `"none"` (→ `"nit"`); function never raises.
- The mapping table in `severity.py` is data (a dict or similar structure), not a chain of if/elif — future additions only touch the table.

## Test specification

`tests/test_severity.py` — table-driven test:

- A parametrised test covering every explicitly documented combination (the 10 rows above plus boundary cases: `level="error"` with `properties_severity="nit"`, `level="warning"` with `properties_severity="critical"` — document the expected result in the test fixture so the table is self-describing).
- A fuzz-boundary test: call `map_severity` with 10 random unknown string pairs; assert the return value is always one of `{"critical", "important", "minor", "nit"}` and never raises.

Green-bar: `pytest tests/test_severity.py` passes; `mypy --strict code_review/severity.py` clean; `ruff check code_review/severity.py` clean.
