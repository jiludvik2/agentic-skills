---
id: s0-t0-importlib-resources
kind: task
project: code-review
status: done
parent: s0-deployment-layout-fixup
created: 2026-05-28
updated: 2026-05-28
---

# s0-t0 — Load package data via `importlib.resources`

## Outcome

Replace every `Path(__file__).parent / "<json file>"` access in `code_review/` with `importlib.resources.files("code_review")`-based loading, so `capabilities.json` and `schemas/*.json` resolve correctly regardless of where the package is installed (source tree, nested skill dir, site-packages).

## Acceptance criteria

- `code_review/config.py:_load_caps_weights` uses `importlib.resources.files("code_review") / "capabilities.json"` (not `Path(__file__).resolve().parent / "capabilities.json"`).
- Any other call site that reads `capabilities.json` or a schema file (search `code_review/` for `capabilities.json`, `schemas/`, `Path(__file__)`) is updated the same way.
- The 4 schemas under `code_review/schemas/` (`capabilities.json`, `review-request.json`, `review-response.json`, `sarif-2.1.0.json`) are reachable via `importlib.resources.files("code_review") / "schemas" / "<name>.json"`.
- No new dependency: `importlib.resources` is in the stdlib for the supported Python floor (3.11+).
- `python -m code_review.cli --capabilities` works unchanged in the current dev layout (regression check).

## Test specification

- **New: `tests/test_package_data_resources.py`** — table-driven over the 5 bundled JSON files:
  - `importlib.resources.files("code_review")` returns a `Traversable` whose `joinpath("capabilities.json")` exists.
  - The same for `schemas/capabilities.json`, `schemas/review-request.json`, `schemas/review-response.json`, `schemas/sarif-2.1.0.json`.
  - Each loads as valid JSON.
  - The schemas validate as JSON-Schema draft 2020-12 (delegate to existing `jsonschema.Draft202012Validator.check_schema`).
- **Regression**: existing `test_capabilities.py`, `test_capabilities_runtime.py`, `test_skill_scaffold.py` continue to pass without modification.

## Notes

- Do **not** delete `_SKILL_DIR` or change `code-review.toml` lookup in this task — that's `s0-t2`. Keep this task narrowly about package-bundled data.
- Use `importlib.resources.files(...).joinpath(...).read_text(encoding="utf-8")` for the typical access pattern.
- For the schema files referenced from `jsonschema.Draft202012Validator`, decide whether to read into memory once at module load (cleaner) or per-call (closer to current behaviour); either is acceptable, but document the choice.

## Notes (post-review, MINOR-ONLY findings for opportunistic cleanup)

- `tests/test_package_data_resources.py:39` — `test_bundled_json_loads` asserts only `isinstance(data, dict)`, which is trivially true for all 5 bundled files. For `capabilities.json` specifically, asserting `'analyzers' in data` would catch real regressions; for schema files the assertion is redundant with `test_schema_is_valid_json_schema`.
- `code_review/adapters/semgrep.py:34` — `_schema()` reads the SARIF schema with `_SCHEMA_PATH.read_text()` (no `encoding="utf-8"`), inconsistent with every other call site touched in this commit. Trivial fix: `read_text(encoding="utf-8")`.
