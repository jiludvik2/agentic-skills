---
id: s0-t4-radon-adapter
kind: task
project: code-review
status: done
parent: s0-analyzer-facade-and-two-adapters
created: 2026-05-26
updated: 2026-05-26
---

# s0-t4 — Radon adapter

## Outcome

`RadonAdapter` implements the `Analyzer` Protocol, uses Radon as a Python library import (not a subprocess), and returns an `AnalyzerOutput` with a populated `MetricSet`. The Python fixture gains a function with cyclomatic complexity ≥ 10.

## Acceptance Criteria

- `RadonAdapter` satisfies `isinstance(RadonAdapter(), Analyzer)`.
- `RadonAdapter.name == "radon"`, `RadonAdapter.kind == "deterministic"`.
- Radon is invoked via library import (`from radon.complexity import cc_visit`, etc.) — not via subprocess. It is a direct Python dependency per `stack-pins.md` (`radon==6.0.1`), so subprocess isolation is not required.
- `tests/fixtures/python-with-known-issues/` contains a Python function with cyclomatic complexity ≥ 10 (added to an existing file in the fixture, or a new file there).
- `await RadonAdapter().run(request)` against the fixture returns `AnalyzerOutput` with `metrics` set to a non-None `MetricSet`; `metrics.per_file` contains at least one entry for the high-CC file; the maximum CC value in that entry is ≥ 10.
- `output.sarif` is a valid (possibly empty-results) SARIF 2.1.0 document — Radon produces metrics, not findings, so `results: []` is acceptable; the document must still validate against the schema.
- `mypy --strict` passes on `radon.py`.

## Test specification

`tests/test_adapters/test_radon.py` — written first:

- `test_radon_protocol_conformance` — `isinstance(RadonAdapter(), Analyzer)` is True; `RadonAdapter.name == "radon"`.
- `test_radon_produces_metric_set` — `ReviewRequest` targeting fixture; `output = asyncio.run(adapter.run(request))`; assert `output.metrics is not None`; assert `len(output.metrics.per_file) > 0`.
- `test_radon_high_cc_function_detected` — assert the fixture file containing the high-CC function appears in `output.metrics.per_file`; assert the maximum `cc` value in that entry is ≥ 10.
- `test_radon_sarif_is_valid` — `jsonschema.validate(output.sarif, sarif_schema)` passes; `results` key exists (may be an empty list).

High-CC fixture function is authored as part of this task (added to `tests/fixtures/python-with-known-issues/`).
