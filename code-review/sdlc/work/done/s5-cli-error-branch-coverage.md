---
id: s5-cli-error-branch-coverage
kind: story
project: code-review
status: done
parent: epic-analyzer-ga-hardening
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-29
updated: 2026-05-30
tags: [cli, tests, error-handling, ga-readiness]
---

> **CLOSED 2026-05-30.** All three F10 branches locked by
> `tests/test_cli_error_branches.py` (unknown `--analyzer`, explicitly-selected
> disabled analyzer, empty post-filter selection) — each asserts non-zero exit
> **and** the specific stderr contract. Test-only: no production change needed;
> the branches already behaved (green on first run). Verify PASS (all 3 ACs
> traced to their intended `cli.py` branch, incl. the at-risk empty-selection
> path → `error=None` reaches cli.py:315). Single-task story, so the per-task
> Review **was** the cumulative-story-diff review (one new test file; no
> cross-cutting surface): verdict **MINOR-ONLY** — one Minor hardened in-task
> (positive control), one Minor deferred to the task `notes:`. Suite 387 passed,
> ruff + mypy clean.


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

## Plan

Single task — **s5-t0-cli-error-branch-tests** carries the outcome and the
authoritative test specification. Test-only; no dependency on other epic stories.
