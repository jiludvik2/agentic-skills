---
id: s2-t3-release-workflow-three-job-split
kind: task
project: code-review
status: active
parent: s2-packaging-hardening
created: 2026-05-29
updated: 2026-05-29
---

# s2-t3 — Release workflow: build / test-dist / publish

## Outcome

The release workflow at `.github/workflows/release.yml` (in the monorepo root, not under `code-review/`) is restructured from one job into three sequential jobs: `build`, `test-dist`, `publish`. The `id-token: write` permission is scoped to `publish` only; `build` and `test-dist` have no elevated permissions. `publish` calls `pypa/gh-action-pypi-publish@release/v1` (the official PyPA action) instead of the in-job `uv publish`. The `astral-sh/setup-uv` action is upgraded `@v3` → `@v5` so the modern cache key derivation works.

`test-dist` does the smoke test the in-source tests can't catch: it downloads the built artifact, creates a clean venv, `pip install`s the wheel, and runs `claude-code-review --capabilities`, asserting the output parses as JSON. This is the safety net that would have caught the missing-LICENSE issue from s2-t0 *before* the publish step.

The existing TestPyPI (`-rc` tags) vs PyPI (final tags) routing is preserved.

## Acceptance criteria

- `release.yml` declares three jobs in order: `build`, `test-dist` (`needs: build`), `publish` (`needs: test-dist`).
- `build` uploads `dist/` as an artifact named `dist` via `actions/upload-artifact@v4`.
- `test-dist` downloads the artifact via `actions/download-artifact@v4`, creates a fresh venv, installs the wheel from `dist/`, runs `claude-code-review --capabilities`, asserts JSON validity (exit non-zero on failure).
- `publish`:
  - Declares `permissions: id-token: write` at the JOB level (not workflow level).
  - Uses `environment: pypi` (and `environment: testpypi` for the `-rc` route — branched by tag pattern or by a workflow-level conditional).
  - Calls `pypa/gh-action-pypi-publish@release/v1` with `packages-dir: dist/` for the final route, and `repository-url: https://test.pypi.org/legacy/` for the `-rc` route.
- All three jobs use `astral-sh/setup-uv@v5` (where uv is needed — `build` and `test-dist`; `publish` does not need uv since the official action handles upload).
- `setup-uv@v5` is configured with `enable-cache: true` and `cache-dependency-glob: "code-review/uv.lock"`.
- The existing `concurrency:` block at the workflow level is preserved.
- The existing `defaults.run.working-directory: code-review` is preserved where appropriate (`build` and `test-dist` need it; `publish` doesn't because it operates on the downloaded artifact).
- The existing tag-prefix routing (`code-review-v*` → PyPI; `code-review-v*-rc*` → TestPyPI) is preserved.
- The Trusted Publishers contract is preserved: no GitHub repository secrets used; OIDC-only.

## Test specification

- **New: `tests/test_release_workflow.py`** with structural assertions parsing the YAML:
  1. `test_workflow_has_three_jobs` — assert `jobs` keys equal `{"build", "test-dist", "publish"}`.
  2. `test_job_dependency_chain` — assert `test-dist.needs == "build"` and `publish.needs == "test-dist"`.
  3. `test_id_token_only_on_publish` — assert `permissions.id-token == "write"` is on `publish` only, NOT on `build`, `test-dist`, or the workflow root.
  4. `test_publish_uses_official_pypa_action` — find the step under `publish` using `pypa/gh-action-pypi-publish@release/v1`.
  5. `test_setup_uv_v5_with_cache` — every `astral-sh/setup-uv` reference uses `@v5` (no `@v3`) and at least one configures `enable-cache: true` + `cache-dependency-glob: "code-review/uv.lock"`.
  6. `test_concurrency_block_preserved` — workflow-level `concurrency` block exists.
  7. `test_tag_prefix_routing_preserved` — the `on.push.tags` glob still includes `code-review-v*`; TestPyPI routing still branches on `-rc` in the tag.
- **Regression**: existing pytest green bar + ruff + mypy continue.
- **No live workflow run** — the release workflow itself is exercised by the operator's first real release per s1's release runbook; this task only verifies structure statically.

## Notes

- `release.yml` lives at `/Users/jiri/Code/2026/agentic-skills/.github/workflows/release.yml`. The system sandbox blocks writes to that path (it's outside `code-review/`). I'll need to use `dangerouslyDisableSandbox: true` on the Bash write, OR have the operator place the new YAML, OR use the Edit tool which the memory note says is not subject to the same block.
- The Trusted Publisher binding on `pypi.org` and `test.pypi.org` is configured against (repo, workflow filename, environment). Keeping the filename `release.yml` means no PyPI-side reconfig is needed. Adding `environment: pypi` for the first time may require a PyPI-side update of the trust relationship — operator-side, not in this task.
- The YAML parsing test uses `yaml` from PyYAML — check whether it's already a dev dep before importing; if not, prefer `tomllib`-style stdlib alternatives (there are none for YAML) or skip the parse and use regex assertions. **Decision needed at execution time** — the simpler path is to add `pyyaml` to `[dependency-groups] dev` since it's a one-liner; the alternative is brittle regex parsing.
