---
id: s0-t5-concurrent-fanout
kind: task
project: code-review
status: active
parent: s0-analyzer-facade-and-two-adapters
created: 2026-05-26
updated: 2026-05-26
---

# s0-t5 — Concurrent fan-out, adapter registry, and FakeAnalyzer

## Outcome

`code_review/adapters/__init__.py` holds an explicit registry mapping names to adapter classes. The CLI fans out across `--analyzer <name>` selections via `asyncio.TaskGroup` and emits a single consolidated JSON document. `FakeAnalyzer` (test helper, lives in `tests/conftest.py`) drives end-to-end CLI tests without spawning any subprocess.

## Acceptance Criteria

- `code_review/adapters/__init__.py` exports `REGISTRY: dict[str, type[Analyzer]]` containing at least `"semgrep"` and `"radon"` entries; adding a new adapter is one import and one dict entry.
- `python -m code_review.cli --analyzer semgrep --analyzer radon --target <fixture>` fans both adapters out concurrently via `asyncio.TaskGroup` and emits a single JSON document with top-level `analyzers` key containing `"semgrep"` and `"radon"` sub-keys.
- Each sub-key contains `{sarif, metrics, duration_s, status, error}` (fields from `AnalyzerOutput`).
- Wall-clock for the concurrent run (measured with two sleep-based `SlowFakeAnalyzer` instances, each sleeping 0.2 s) is less than `0.35 s` — i.e. closer to `max(t1, t2)` than to `t1 + t2`.
- `FakeAnalyzer` implements the `Analyzer` Protocol and returns canned `AnalyzerOutput` without spawning any subprocess; it is registered under `"fake"` in `REGISTRY` for test use.
- Running `--analyzer fake --target .` via `FakeAnalyzer` exercises the full CLI path (arg parsing → registry lookup → TaskGroup → JSON output → stdout) without touching any real tool.
- `mypy --strict` passes on `adapters/__init__.py`.

## Test specification

`tests/test_facade.py` — written first:

- `test_fake_adapter_no_subprocess` — monkeypatch `asyncio.create_subprocess_exec` to raise `AssertionError("subprocess spawned")`; run CLI with `--analyzer fake`; assert the patch was never triggered; assert output is a valid consolidated JSON with `analyzers.fake` present.
- `test_fake_adapter_end_to_end` — run full CLI path with `--analyzer fake --target .`; assert exit 0; load stdout as JSON; assert `"analyzers"` key exists with `"fake"` sub-key.

`tests/test_cli.py` additions:

- `test_concurrent_execution_faster_than_sequential` — register two `SlowFakeAnalyzer(sleep_s=0.2)` instances under names `"slow1"` and `"slow2"`; run `python -m code_review.cli --analyzer slow1 --analyzer slow2 --target .`; assert total elapsed time < `0.35 s`.
- `test_consolidated_output_shape` — run with `--analyzer fake --analyzer fake2` (two distinct fakes with canned different outputs); load stdout JSON; assert both appear as keys under `"analyzers"`.
