---
id: s0-fix1-empty-target-paths-guard
kind: task
project: code-review
status: done
parent: s0-analyzer-facade-and-two-adapters
sources: [story-level-review-s0]
created: 2026-05-26
updated: 2026-05-26
---

# s0-fix1 — Guard adapters against empty target_paths

## Outcome

When `resolve_diff_paths` returns an empty tuple (valid case: diff with no changed files, or git error), both `SemgrepAdapter.run` and `RadonAdapter.run` return an empty-result `AnalyzerOutput` immediately instead of scanning all of CWD by default.

## Acceptance Criteria

- If `request.target_paths` is an empty tuple, both adapters return `AnalyzerOutput(sarif={"runs": []}, status="ok")` without spawning any subprocess or running Radon.
- Non-empty `target_paths` behavior is unchanged — existing tests remain GREEN.

## Test specification

`tests/test_adapters/test_semgrep.py` and `tests/test_adapters/test_radon.py` additions:

- `test_semgrep_empty_target_paths_returns_empty_sarif` — build a `ReviewRequest` with `target_paths=()`, call `SemgrepAdapter().run(request)` in an async test, assert `output.status == "ok"` and `output.sarif.get("runs", []) == []`, assert no subprocess was spawned (use `monkeypatch` to assert `asyncio.create_subprocess_exec` is never called).
- `test_radon_empty_target_paths_returns_empty_metricset` — same structure for `RadonAdapter`; assert `output.metrics.per_file == {}` and `output.metrics.per_class == {}`.
