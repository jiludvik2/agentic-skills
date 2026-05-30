---
id: s0-fix2-unavailable-end-to-end-coverage
kind: task
project: code-review
status: active
parent: s0-analyzer-adapter-robustness
sources: [s0-analyzer-adapter-robustness.md, adr-0019-analyzer-unavailable-vs-error.md, code_review/aggregator.py, code_review/cli.py]
status: done
created: 2026-05-30
updated: 2026-05-30
tags: [test-coverage, unavailable, aggregator, cli, story-level-fix, important]
notes:
  - "Outcome: TEST-ONLY, no production change — aggregator.py:116 and cli.py:377 already gate strictly on status=='error', so unavailable threads through benignly as designed. Confirmed by a mutation check: broadening both gates to '!= ok' made exactly the two new characterization tests fail (the error-regression test stayed green), then reverted."
  - "Review MINOR (applied in-green-bar): _ErrorAnalyzer renamed bandit->semgrep and registered consistently so each fake's name matches its registry key."
  - "Review NIT (dropped): aggregator test's len(results)==1 assertion mirrors AC1 but the unavailable-specific binding is the analyzer_errors-exclusion assertion; docstring left as a faithful AC mirror."
---

# s0-fix2 — end-to-end test: `unavailable` threads benignly (story-level Review, Important)

## Origin

Round-1 fix task from the **s0 story-level Review** (Important #2). The story's
load-bearing invariant — an `unavailable` analyzer output is a *clean skip*: zero
findings, excluded from `analyzer_errors`, no non-zero CLI exit — is asserted only at
the adapter unit level. The aggregator (`aggregator.py:116`) and CLI
(`cli.py:377` `has_error`) gate strictly on `status == "error"`; the per-task reviews
verified `unavailable` threads through by code inspection only. A future refactor that
broadened either gate (e.g. `status != "ok"`) would silently re-pollute reviews with
green-skip noise and no test would catch it.

## Acceptance criteria

- **Given** a set of `AnalyzerOutput`s including one with `status="unavailable"`
  (empty SARIF + reason)
- **When** the aggregator merges them
- **Then** the unavailable output contributes **zero** merged findings and is **not**
  recorded in the consolidated `analyzer_errors`.
- **Given** a CLI run whose analyzers are all `ok`/`unavailable` (none `error`)
- **When** the exit status is computed
- **Then** `has_error` is `False` (exit 0).

## Test specification (tests-first / characterization)

These lock in already-correct behaviour (no production change expected). Confirm the
tests **fail if the gate is naively broadened** by spot-mutating locally, then commit
the passing tests.

1. In `tests/test_aggregator.py` (or nearest): build outputs `[ok-with-finding,
   unavailable-empty]`, run the merge, assert merged results == the ok output's
   findings only, and assert the unavailable analyzer is absent from `analyzer_errors`.
2. In the CLI tests: assert a run whose `analyzers_dict` statuses are all in
   `{ok, unavailable}` yields `has_error is False`; a run containing one `error`
   yields `True` (regression guard).

If production already satisfies these (expected), no source edit — the deliverable is
the regression test. Note in close that no behaviour change was needed.
