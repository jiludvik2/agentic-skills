---
id: s2-t2-hotspots
kind: task
project: code-review
status: done
parent: s2-aggregator-and-severity-mapping
created: 2026-05-26
updated: 2026-05-26
---

# s2-t2 — hotspots: ranked per-file composite score

## Outcome

`aggregate()` (from t1) gains a companion `compute_hotspots(consolidated_sarif, metrics, diff_files, scope)` function (in `aggregator.py` or extracted to `hotspots.py`) that returns a `ranked_hotspots` list: `[{file, composite_score, factors}]` sorted descending. Per-task scope restricts the list to files in the diff; story-level scope may include files not directly modified. Weights are read from `capabilities.json` (default) or overridden in `code-review.toml` (picked up in t3).

## Acceptance criteria

- Each entry is `{file: str, composite_score: float, factors: dict}` where `factors` records the contributing components: `severity_weighted_findings`, `cyclomatic_complexity` (from `MetricSet.per_file`), `coupling` (fan-in + fan-out from `MetricSet.coupling`).
- List is sorted descending by `composite_score`.
- **Per-task scope:** `diff_files` is non-empty; `ranked_hotspots` contains only files that appear in `diff_files`. Files in the consolidated SARIF but not in `diff_files` are excluded.
- **Story-level scope:** `diff_files` is `None` (or empty); `ranked_hotspots` includes all files appearing in the consolidated SARIF (including unchanged files that appear only in MetricSet data).
- **No findings, no MetricSet:** a file that appears in `diff_files` but has no findings and no MetricSet data gets `composite_score = 0.0` and does not appear in the list (zero-score files are omitted).
- Weights default: `severity_weighted_findings` weight = 1.0, `cyclomatic_complexity` weight = 0.5, `coupling` weight = 0.3. These defaults live in `capabilities.json` under `hotspots.weights`, not hardcoded.
- Return type is a plain Python list (serialisable to JSON by the CLI); no custom dataclass required unless mypy --strict demands it.

## Test specification

`tests/test_hotspots.py`:

- **Composite score golden-file test** — build a known consolidated SARIF (3 files, known finding severities) and a known `MetricSet` (known complexity/coupling per file). Call `compute_hotspots` and assert the returned list matches a JSON golden fixture at `tests/fixtures/hotspots_golden.json` (checked in with the task). If the output doesn't match, print a diff.
- **Per-task scope restriction test** — same inputs, pass `diff_files={"src/auth.py"}` (only one of the three files); assert `ranked_hotspots` contains exactly one entry (`src/auth.py`) regardless of which file scored highest overall.
- **Story-level scope test** — same inputs, `diff_files=None`; assert all three files appear in `ranked_hotspots`.
- **Zero-score omission test** — a file in `diff_files` with no findings and no MetricSet data does not appear in the output list.

Green-bar: `pytest tests/test_hotspots.py` passes; mypy strict clean; ruff clean.

## Dependencies

- s2-t1 must be done (uses consolidated SARIF from `aggregate()`).
- `capabilities.json` weight defaults must be added in this task if not already present.
