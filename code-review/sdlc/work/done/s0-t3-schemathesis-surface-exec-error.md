---
id: s0-t3-schemathesis-surface-exec-error
kind: task
project: code-review
status: done
parent: s0-analyzer-adapter-robustness
sources: [post-ga-self-review-findings.md, code_review/adapters/schemathesis_.py]
created: 2026-05-30
updated: 2026-05-30
tags: [schemathesis, adapter, error-handling, minor]
notes:
  - "Review MINOR (deferred, candidate follow-up): the sibling `h_find` strategy-generation swallow (`except Exception: return []`, schemathesis_.py ~line 145) is the SAME B110 false-clean class this task fixed for call_and_validate — a strategy-build crash also makes 'couldn't test it' read as 'conforms'. Out of t3's AC scope; surface at story s0 boundary as a candidate follow-up."
  - "Review NIT (dropped): ruleId suffix style mixed (response_schema_violation/server_error underscored vs execution-error hyphenated). The new hyphen is the CORRECT cross-adapter convention (depcruiser/jscpd/knip/vulture use hyphens) and the AC pins it; normalising the legacy entries would alter pinned ruleIds — out of scope."
---

# s0-t3 — schemathesis: surface unexpected execution errors as findings (F1)

## Outcome

When `call_and_validate` raises a non-`FailureGroup` exception for an operation, the
schemathesis adapter emits a `schemathesis.execution-error` finding naming the
operation instead of silently swallowing it (`except Exception: pass`) and reporting
the operation as conformant.

## Root cause

`code_review/adapters/schemathesis_.py:141` — `except Exception: pass` after
`call_and_validate` hides any non-`FailureGroup` error (connection error, validation
bug), so "couldn't test it" looks identical to "it conforms" — a false clean for a
contract tester. (bandit B110 flagged this.)

## Acceptance criteria

- **Given** `call_and_validate` raises a plain `RuntimeError` for an operation
- **When** `_run_operation` runs
- **Then** it yields one `schemathesis.execution-error` finding naming the operation
  (level `error`), not an empty list.
- **Given** a `FailureGroup` is raised
- **When** it runs
- **Then** existing behaviour is unchanged (failures extended as today).
- Do **not** re-raise (one bad operation must not fail the whole adapter run).

## Test specification (tests-first)

In `tests/test_adapters/test_schemathesis.py` (mirror the existing MagicMock style):
1. `test_unexpected_exception_becomes_execution_error_finding`: patch
   `call_and_validate` to raise `RuntimeError("boom")` → assert one
   `schemathesis.execution-error` finding naming the operation.
2. Regression: a `FailureGroup` path still produces the existing conformance findings.

Confirm RED first. Reuse `_failure_to_sarif_result`'s location/shape conventions for
the synthetic finding.
