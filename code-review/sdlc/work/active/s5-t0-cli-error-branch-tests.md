---
id: s5-t0-cli-error-branch-tests
kind: task
project: code-review
status: active
parent: s5-cli-error-branch-coverage
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-30
updated: 2026-05-30
tags: [cli, tests, error-handling]
---

# s5-t0 — CLI error-branch tests

## Outcome

The three untested `cli.py` error branches (F10) get locking tests: unknown
`--analyzer`, an explicitly-selected disabled analyzer, and an empty post-filter
selection. Test-only; no production change expected unless a branch misbehaves.
Implements all three s5-story scenarios. No dependency on other epic stories.

## Acceptance criteria

(The s5-story scenarios are the contract; restated as the per-task gate.)

### Scenario: unknown --analyzer rejected
- **Given** `--analyzer nonesuch`
- **Then** non-zero exit; stderr names the unknown analyzer.

### Scenario: explicitly selected disabled analyzer rejected
- **Given** a `code-review.toml` disabling analyzer X and a run selecting X
- **Then** non-zero exit; stderr states X is disabled in `code-review.toml`.

### Scenario: empty selection rejected
- **Given** a `--review`/`--language`/`--depth` combination that resolves to no
  analyzers
- **Then** non-zero exit; stderr says no analyzers were selected.

## Test specification

Write first, confirm red (they should pass immediately if the branches already
behave — the point is locking the contract), then implement only if a branch
misbehaves. New `tests/test_cli_error_branches.py` (or extend `tests/test_cli.py`),
`CliRunner(capture="fd")` + the `FakeAnalyzer`/registry-patch pattern from
`test_review_selection_validation.py`:

1. `test_unknown_analyzer_exits_nonzero_with_message`.
2. `test_disabled_analyzer_selected_exits_nonzero_with_message` (patch
   `load_config` to return a Config with `disabled_analyzers=["X"]`).
3. `test_empty_selection_exits_nonzero_with_message`.
