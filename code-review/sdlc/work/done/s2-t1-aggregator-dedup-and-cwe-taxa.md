---
id: s2-t1-aggregator-dedup-and-cwe-taxa
kind: task
project: code-review
status: done
parent: s2-aggregator-and-severity-mapping
created: 2026-05-26
updated: 2026-05-26
---

# s2-t1 — aggregator.py: dedup, CWE taxa, and severity tagging

## Outcome

`code_review/aggregator.py` exposes an `aggregate(outputs: list[AnalyzerOutput], line_tolerance: int = 3) -> dict[str, Any]` function that merges multiple per-analyzer SARIF outputs into a single consolidated SARIF document. Dedup uses `(uri, CWE)` as the merge key with ±`line_tolerance` line proximity; severity tagging applies `map_severity` from t0 to every consolidated finding; CWE references appear in `taxa` arrays (SARIF 2.1.0), not in free-form `tags`.

## Acceptance criteria

- **Same-line merge:** two findings at `src/auth.py:47` from different analyzers with the same CWE produce exactly one consolidated `result`; `properties.sources` lists both analyzer names; the higher SARIF `level` of the two is preserved.
- **Near-line merge:** findings at lines 47 and 49 in the same file with the same CWE merge (line tolerance = 3 by default); lower line number wins; `properties.original_locations` records both original line numbers.
- **CWE anchors merge:** two findings share a CWE only if the CWE id is identical; partial-string overlap is not a match.
- **Different-CWE no-merge:** two findings at `src/auth.py:47` with distinct CWE values remain separate `result` entries even though they share file and line.
- **No CWE, no merge:** findings without a CWE tag are treated as non-mergeable and are never merged with any other finding, even at the same line.
- **sdlc_severity tagged:** every `result` in the consolidated SARIF gains a `properties.sdlc_severity` field produced by `map_severity(level, properties.severity)`.
- **CWE via taxa:** any finding whose source SARIF carries a CWE in free-form `tags` or `ruleId` has that CWE reference moved to `result.taxa` (per SARIF 2.1.0 `reportingDescriptorReference`); the run's `tool.driver.supportedTaxonomies` declares the CWE taxonomy; no duplicate CWE appears in `tags`.
- **Empty input:** `aggregate([])` returns a valid minimal SARIF document (empty `runs` or a single run with empty `results`).
- **Error-status passthrough:** an `AnalyzerOutput` with `status="error"` is skipped for findings aggregation but its `error` field is carried into the consolidated output's `properties.analyzer_errors` list.

## Test specification

`tests/test_aggregator.py`:

- **Dedup correctness suite** (parametrised) — build fixture `AnalyzerOutput`s with pre-planned overlaps matching the three scenarios above (same-line/same-CWE, near-line/same-CWE, same-line/different-CWE). Assert exact `result` counts, `properties.sources` content, and winning line numbers.
- **CWE taxonomy reference test** — fixture with a known CWE-89-tagged finding whose source puts the CWE in `tags`; after aggregation assert: `result.taxa` has an entry referencing CWE-89; `tool.driver.supportedTaxonomies` declares the CWE taxonomy; `tags` does not contain a CWE id.
- **sdlc_severity tagging test** — fixture with findings at three distinct SARIF levels (`error`, `warning`, `note`); assert each consolidated finding's `properties.sdlc_severity` matches the expected SDLC label.
- **Empty input test** — `aggregate([])` returns a dict with a `runs` key and no exception.
- **Error passthrough test** — mix one error-status `AnalyzerOutput` with one normal one; assert consolidated output has results from the normal one and `properties.analyzer_errors` contains the error entry.

Green-bar: `pytest tests/test_aggregator.py` passes; `mypy --strict code_review/aggregator.py` clean; `ruff check code_review/aggregator.py` clean.

## Dependencies

- s2-t0 must be done (imports `map_severity` from `code_review.severity`).
