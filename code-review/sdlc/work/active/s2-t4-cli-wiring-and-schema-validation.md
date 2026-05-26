---
id: s2-t4-cli-wiring-and-schema-validation
kind: task
project: code-review
status: active
parent: s2-aggregator-and-severity-mapping
created: 2026-05-26
updated: 2026-05-26
---

# s2-t4 — CLI wiring: aggregation step + response schema

## Outcome

The CLI's `_run_analyzers` fanout is followed by an aggregation step that calls `aggregate()` and `compute_hotspots()` from s2-t1/t2, producing a consolidated response document. The document is validated against a new `review-response.json` JSON Schema (created in this task at `.claude/skills/code-review/schemas/review-response.json`) before being written to disk or echoed to stdout.

## Acceptance criteria

- **Aggregation in CLI:** after the analyzer fanout completes, `aggregate()` is called on the per-analyzer outputs; `compute_hotspots()` is called with the consolidated SARIF and `diff_files` derived from `--diff` (per-task) or `None` (no diff = story-level).
- **Consolidated output shape:** the final JSON has keys: `sarif` (consolidated SARIF), `metrics` (merged MetricSet or `null`), `ranked_hotspots` (list from t2), `analyzers` (per-analyzer status, duration, error — same as before but now nested under the top-level key).
- **Config loaded from skill dir:** `load_config(_SKILL_DIR)` is called once at CLI startup; the resulting `Config` is passed to `aggregate()` and `compute_hotspots()`.
- **Schema file:** `.claude/skills/code-review/schemas/review-response.json` exists and is a valid JSON Schema (draft-07). It declares required top-level keys (`sarif`, `metrics`, `ranked_hotspots`, `analyzers`). The `sarif` value must match the structural contract: object with `version` (string) and `runs` (array).
- **Validation at runtime:** the CLI validates the consolidated output against `review-response.json` using `jsonschema`. If validation fails, it logs a warning to stderr (non-fatal) and continues — validation failure is observability, not a crash gate, because the schema is expected to evolve in s3/s4.
- **Schema checked in:** `schemas/review-response.json` is committed as a repo artefact (not generated at runtime).
- **Existing CLI tests stay green:** all tests in `tests/test_cli.py` and `tests/test_scope_dispatch.py` continue to pass with the new output shape (update fixture assertions if needed — the shape change is deliberate and expected).

## Test specification

`tests/test_cli_aggregation.py` (new file):

- **End-to-end shape test** — call the CLI with two mock analyzers (monkeypatched to return fixture SARIFs with known findings). Assert the output JSON contains `sarif`, `metrics`, `ranked_hotspots`, and `analyzers` at the top level; `sarif.runs` is a list; `ranked_hotspots` is a list.
- **Aggregation applied test** — monkeypatch two analyzers to return overlapping findings (same file, same line, same CWE). Assert the consolidated `sarif.runs[0].results` has one entry, not two (dedup happened).
- **Per-task vs story-level hotspot scope test** — with `--diff` set: assert `ranked_hotspots` contains only files from the diff. Without `--diff`: assert `ranked_hotspots` may contain additional files.
- **Response-schema validation test** — round-trip the CLI output through `jsonschema.validate` against `review-response.json`; assert no `ValidationError`.
- **Schema warning non-fatal test** — monkeypatch `jsonschema.validate` to raise `ValidationError`; assert the CLI exits 0 (or 1 only due to analyzer errors, not schema), and stderr contains "schema validation warning" (or similar).

Update `tests/test_cli.py` fixture assertions for the new top-level output shape where needed.

Green-bar: full `pytest` suite (74+ tests) passes; mypy strict clean; ruff clean.

## Dependencies

- s2-t1 (aggregator).
- s2-t2 (hotspots).
- s2-t3 (config loader).
- `jsonschema` must be added to `pyproject.toml` dependencies if not already present (check before adding).
