---
id: s4-fix3-hypothesis-env-restore
kind: task
project: code-review
status: active
parent: s4-contract-testing-adapters
sources: [s4-story-level-review]
created: 2026-05-27
updated: 2026-05-27
---

# s4-fix3 — Scope/restore HYPOTHESIS_STORAGE_DIRECTORY env var

## Context

Story-level review found an **Important**: the adapter sets the process-global
`os.environ["HYPOTHESIS_STORAGE_DIRECTORY"]` (schemathesis_.py:119) and never restores it. Because the
adapter runs **in-process** (ADR-0009), the mutation persists for the whole CLI process and leaks
across analyzers and across runs in the same process. Every subprocess cache-redirect adapter
(semgrep, gitleaks, trivy) builds a scoped `env` dict passed to the child and leaves the parent
`os.environ` untouched; the in-process adapter is the lone exception.

## Acceptance Criteria

- After `SchemathesisAdapter.run()` returns (success, error, or timeout), the process-global
  `os.environ["HYPOTHESIS_STORAGE_DIRECTORY"]` is restored to its prior value (or removed if it was
  previously unset) — the run leaves no residual env mutation.
- Hypothesis storage still resolves under the per-run `$TMPDIR` `TemporaryDirectory` during the run
  (the s4-t1 cache-redirect AC remains satisfied).

## Test specification

- `test_hypothesis_env_var_restored_after_run` — record `os.environ.get("HYPOTHESIS_STORAGE_DIRECTORY")`
  before; run the adapter (no-targets or unreachable path is sufficient); assert the value after equals
  the value before (including the unset case). Run a second variant with the var pre-set to a sentinel
  and assert the sentinel is restored.
- Existing `test_hypothesis_cache_redirected_to_tmpdir` must still pass (storage points under `$TMPDIR`
  *during* the run).
