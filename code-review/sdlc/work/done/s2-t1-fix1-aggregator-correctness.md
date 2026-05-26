---
id: s2-t1-fix1-aggregator-correctness
kind: task
project: code-review
status: done
parent: s2-aggregator-and-severity-mapping
sources: [s2-t1-aggregator-dedup-and-cwe-taxa.md]
created: 2026-05-26
updated: 2026-05-26
---

# s2-t1-fix1 — aggregator correctness: level KeyError, mutation, ruleId CWE

## Findings (reviewer + verifier, round 1)

**Important A** — `aggregator.py:130`: `merged[i]["level"]` raises KeyError when a SARIF result omits `level` (permitted by SARIF 2.1.0; default is `warning`).

**Important B** — `aggregator.py:128-129`: near-line merge mutates the caller's `AnalyzerOutput.sarif` in-place. `loc` is a reference into the original dict chain; replacing `startLine` corrupts the source data.

**Important C** — `aggregator.py:55-71` / missing tests: `_normalise_taxa` only reads `properties.tags`; the spec AC also requires CWE ids found in `ruleId` to be moved to `taxa`. No implementation, no test.

**Minor** — `test_near_line_same_cwe_merges` asserts only keys of `original_locations`, not values. Stale comment on `merged` list.

## Fixes

A. `merged[i].get("level", "none")` at line 130.
B. Deep-copy `locations` when inserting a new entry (use `copy.deepcopy` on `result` at insertion, or at least on `locations`).
C. Add branch in `_normalise_taxa`: if `result.get("ruleId", "").startswith("CWE")`, append to `taxa` and clear `ruleId` (or blank it). Add a test fixture where CWE comes from `ruleId`.

Minor: add value assertions for `original_locations`; remove stale `merged` comment.

## Acceptance criteria

- `aggregate()` on a result with no `level` key completes without raising.
- Calling `aggregate()` twice on the same list of `AnalyzerOutput`s produces the same result both times (no mutation).
- A finding whose `ruleId` is a CWE id (e.g. `"CWE-89"`) has that CWE appear in `taxa` after aggregation.
- `test_near_line_same_cwe_merges` asserts `original_locations` values (line 47 for semgrep, line 49 for bandit).
