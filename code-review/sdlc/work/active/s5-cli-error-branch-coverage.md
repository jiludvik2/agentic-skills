---
id: s5-cli-error-branch-coverage
kind: story
project: code-review
status: active
parent: epic-analyzer-ga-hardening
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-29
updated: 2026-05-29
tags: [cli, tests, error-handling, ga-readiness]
---

# s5 — CLI error-branch coverage

## Summary

The CLI option surface and most invalid-input paths are well covered by the
pytest suite (`CliRunner`, mocked analyzers): `--output` outside CWD, unknown
`--depth`, unknown `--review`, contradictory `--depth`, scope violations,
malformed/missing/invalid `--config`. But three error branches in `cli.py` have
**zero** test coverage (FINDINGS.md F10):

1. **unknown `--analyzer <name>`** → `cli.py` emits "unknown analyzer(s): …",
   exit 1.
2. **explicitly selecting a disabled analyzer** → "analyzer(s) disabled in
   code-review.toml: …", exit 1.
3. **no analyzers selected after filtering** (e.g. a `--review`/`--language`
   combination that matches nothing) → "no analyzers selected after filtering",
   exit 1.

These are small, mock-only gaps — but they are user-facing error contracts that
should not regress silently. Test-only story; no production code change expected
unless a branch is found to misbehave. No dependency on other epic stories.

## Acceptance criteria

### Scenario: unknown --analyzer rejected
- **Given** `--analyzer nonesuch`
- **When** the CLI runs
- **Then** exit code is non-zero and stderr names the unknown analyzer.

### Scenario: explicitly selected disabled analyzer rejected
- **Given** a `code-review.toml` disabling analyzer X and a CLI run selecting X
  (via `--analyzer X` or a review set that resolves to X)
- **When** the CLI runs
- **Then** exit code is non-zero and stderr states X is disabled in
  `code-review.toml`.

### Scenario: empty selection rejected
- **Given** a `--review`/`--language`/`--depth` combination that resolves to no
  analyzers
- **When** the CLI runs
- **Then** exit code is non-zero and stderr says no analyzers were selected.

## Test specification

Write first, confirm red (they should pass immediately if the branches already
behave correctly — the point is locking the contract), then implement only if a
branch misbehaves. Add to `tests/test_cli.py` or a new
`tests/test_cli_error_branches.py`, using `CliRunner(capture="fd")` and the
`FakeAnalyzer`/registry-patch pattern from `test_review_selection_validation.py`:

1. `test_unknown_analyzer_exits_nonzero_with_message`.
2. `test_disabled_analyzer_selected_exits_nonzero_with_message` (patch
   `load_config` to return a Config with `disabled_analyzers=["X"]`).
3. `test_empty_selection_exits_nonzero_with_message`.
