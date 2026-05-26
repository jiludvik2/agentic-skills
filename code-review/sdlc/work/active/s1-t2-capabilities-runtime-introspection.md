---
id: s1-t2-capabilities-runtime-introspection
kind: task
project: code-review
status: active
parent: s1-reviewer-skill-and-capabilities
created: 2026-05-26
updated: 2026-05-26
---

# s1-t2 — --capabilities runtime introspection + analyzer-registry round-trip

## Outcome

`python -m code_review.cli --capabilities` emits a JSON document combining the static `capabilities.json` content with recomputed runtime per-analyzer availability checks. A new analyzer added to the registry + capabilities.json appears in the output and is accepted as `--analyzer <name>` with no other code change.

## Acceptance Criteria

- `--capabilities` output contains the static section (matching `capabilities.json` file content) plus a runtime section with one entry per analyzer: `status == "available"` if the analyzer's binary resolves on PATH (or, for library-based analyzers like radon, if importable), `status == "unavailable"` with a non-empty `error` field otherwise.
- The runtime section is recomputed each invocation (not cached from file).
- For a missing binary (e.g. semgrep not on PATH), `analyzers.semgrep.status == "unavailable"` with a clear error message.
- A synthetic adapter added to `REGISTRY` plus an entry in `capabilities.json` appears in `--capabilities` output and is accepted as `--analyzer <name>` without further code change.

## Test specification

Additions to `tests/test_cli.py` (and/or new `tests/test_capabilities_runtime.py`):

- `test_capabilities_static_section_matches_file` — run `--capabilities`; assert the static portion of the output equals the parsed `capabilities.json`.
- `test_capabilities_runtime_marks_missing_binary_unavailable` — monkeypatch `shutil.which` (and/or the import probe) so semgrep resolves to None; run `--capabilities` in-process; assert `analyzers.semgrep.status == "unavailable"` and `error` non-empty.
- `test_capabilities_runtime_marks_present_binary_available` — monkeypatch so the probe succeeds; assert `status == "available"`.
- `test_analyzer_registry_round_trip` — monkeypatch `REGISTRY` with a synthetic `FakeAnalyzer` and a matching capabilities entry; assert it appears in `--capabilities` output and that `--analyzer <fake>` is accepted (exit code not the "unknown analyzer" path).

## Notes / deferrals

- `--review-scope {lite,standard,full}` CLI flag acceptance (consumed by the reviewer in s1-t4) is added here as a no-op-passthrough option so the scope-dispatch contract has a CLI surface to target; the behavioural wiring lives in s1-t4.
