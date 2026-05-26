---
id: s0-t3-semgrep-adapter
kind: task
project: code-review
status: active
parent: s0-analyzer-facade-and-two-adapters
created: 2026-05-26
updated: 2026-05-26
---

# s0-t3 — Semgrep adapter

## Outcome

`SemgrepAdapter` implements the `Analyzer` Protocol, invokes Semgrep via `asyncio.create_subprocess_exec` with `--sarif` output, and returns a validated SARIF 2.1.0 document when run against the Python fixture. `adapters/base.py` provides shared subprocess helpers used by all future adapters.

## Acceptance Criteria

- `code_review/adapters/base.py` exports an async helper (e.g. `run_subprocess`) that: uses `asyncio.create_subprocess_exec`; wraps the call in `asyncio.wait_for(timeout_s)`; on timeout, kills the process group and returns a sentinel indicating timeout; captures stdout and stderr as bytes; never raises — errors surface as return values.
- `SemgrepAdapter` satisfies `isinstance(SemgrepAdapter(), Analyzer)`.
- `SemgrepAdapter.name == "semgrep"`, `SemgrepAdapter.kind == "deterministic"`.
- `tests/fixtures/python-with-known-issues/` contains at least one Python file with `subprocess.run(..., shell=True)` — a known Semgrep finding (rule `python.lang.security.audit.subprocess-shell-true` or equivalent).
- Running `await SemgrepAdapter().run(request)` against the fixture (with Semgrep on PATH) returns `AnalyzerOutput` whose `sarif` validates against `schemas/sarif-2.1.0.json` via `jsonschema.validate`.
- The SARIF output contains at least one `result` with a `ruleId` matching `subprocess-shell-true` (or the canonical Semgrep rule ID) and a `locations[0].physicalLocation.artifactLocation.uri` pointing into the fixture.
- Semgrep is invoked with `--sarif` (not `--json`) to get native SARIF; if the native SARIF does not validate, a minimal normalisation shim in the adapter corrects it before returning.
- If `semgrep` is not on PATH, `run` returns `AnalyzerOutput(status="error", error="semgrep not found: ...")` — no exception propagates to the caller.
- `mypy --strict` passes on `base.py` and `semgrep.py`.

## Test specification

`tests/test_adapters/test_semgrep.py` — written first:

- `test_semgrep_protocol_conformance` — `isinstance(SemgrepAdapter(), Analyzer)` is True; `SemgrepAdapter.name == "semgrep"`.
- `test_semgrep_produces_valid_sarif` — `@pytest.mark.integration`; skip if `shutil.which("semgrep") is None`; construct `ReviewRequest(scope="per-task", diff_range=None, target_paths=(str(fixture_path),), languages=frozenset(["python"]), config={})`; `output = asyncio.run(adapter.run(request))`; `jsonschema.validate(output.sarif, sarif_schema)`; assert at least one result with expected ruleId.
- `test_semgrep_missing_binary_returns_error` — monkeypatch `asyncio.create_subprocess_exec` to raise `FileNotFoundError`; assert `output.status == "error"`; assert `output.error` is a non-empty string; assert no exception propagates.
- `test_base_subprocess_timeout` — monkeypatch subprocess to return a mock process that never finishes; pass `timeout_s=0.05`; assert the helper returns within 2s; assert the returned exit-code sentinel indicates timeout.
