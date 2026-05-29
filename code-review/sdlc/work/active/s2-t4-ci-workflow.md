---
id: s2-t4-ci-workflow
kind: task
project: code-review
status: active
parent: s2-packaging-hardening
created: 2026-05-29
updated: 2026-05-29
---

# s2-t4 — CI workflow on push / PR

## Outcome

`.github/workflows/ci.yml` (new file at the monorepo root) runs the green-bar checks — pytest + ruff + mypy — on every push to `main` and on every PR against `main` that touches `code-review/`. Before this story the only workflow is `release.yml`, which only fires on tags. A broken commit currently reaches `main` undetected until either the operator runs the suite locally or a release tag is pushed.

The workflow uses `astral-sh/setup-uv@v5` with cache enabled, runs `uv sync --frozen` to enforce the lockfile, and runs the same green-bar steps the verifier and reviewer agents run. Path filter `code-review/**` so edits to sibling packages in the monorepo don't fan out.

## Acceptance criteria

- `.github/workflows/ci.yml` exists at the monorepo root.
- Triggers: `push` to `main` AND `pull_request` against `main`, both with path filter `code-review/**` plus `.github/workflows/ci.yml` itself.
- Single job named `test` (no matrix) on `ubuntu-latest` with `defaults.run.working-directory: code-review`.
- Job steps in order:
  1. `actions/checkout@v4`
  2. `astral-sh/setup-uv@v5` with `enable-cache: true` and `cache-dependency-glob: "code-review/uv.lock"`
  3. `uv sync --frozen`
  4. `uv run pytest -m "not slow and not integration"`
  5. `uv run ruff check .`
  6. `uv run mypy code_review`
- No `permissions:` block elevated beyond GitHub's default (no `id-token`, no `contents: write`, etc.). The CI workflow is read-only.
- No `secrets:` references.
- A workflow-level `concurrency:` block cancels in-progress runs for the same ref (`group: ci-${{ github.ref }}`, `cancel-in-progress: true`) — appropriate for CI (unlike release.yml which sets `cancel-in-progress: false` for safety).

## Test specification

- **New: `tests/test_ci_workflow.py`** with structural assertions:
  1. `test_ci_workflow_exists` — `.github/workflows/ci.yml` is present.
  2. `test_triggers_are_push_main_and_pr_main` — both `push.branches` and `pull_request.branches` include `main`.
  3. `test_path_filter_covers_code_review` — both triggers have `paths` filter that includes `code-review/**` and `.github/workflows/ci.yml`.
  4. `test_single_test_job` — `jobs.keys() == {"test"}`.
  5. `test_no_elevated_permissions` — neither workflow-level nor job-level `permissions` declares anything beyond defaults (specifically no `id-token`, no `contents: write`).
  6. `test_steps_run_pytest_ruff_mypy_in_order` — find the run-strings, assert they appear in the documented order.
  7. `test_setup_uv_v5_with_cache` — same setup-uv config check as the release workflow test.
  8. `test_concurrency_with_cancel_in_progress` — workflow-level concurrency block; `cancel-in-progress: true`.
- **Regression**: existing pytest green bar + ruff + mypy continue.

## Notes

- The CI workflow does NOT trigger on `push` to non-`main` branches — feature branches use PRs against `main` to surface CI checks. This is a deliberate choice and the operator's existing branch-protection settings are orthogonal.
- pytest filter `-m "not slow and not integration"` matches the local + verifier convention; CI keeps the run under ~45s. The slow wheel-build tests don't run in CI; they are exercised by the release workflow's `test-dist` job.
- Path filter on the workflow file itself (`.github/workflows/ci.yml`) means edits to the CI definition trigger their own validation run — standard practice.
- `defaults.run.working-directory: code-review` applies to `run:` steps but not `uses:` steps; this is the same pattern release.yml uses.
- Cache key derivation: `setup-uv@v5` with `cache-dependency-glob` automatically invalidates the cache when `code-review/uv.lock` changes. No manual cache key needed.
