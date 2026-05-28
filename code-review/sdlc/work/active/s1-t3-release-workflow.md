---
id: s1-t3-release-workflow
kind: task
project: code-review
status: active
parent: s1-package-publication
created: 2026-05-28
updated: 2026-05-28
---

# s1-t3 — GitHub Actions release workflow

## Outcome

A workflow file at `.github/workflows/release.yml` triggers on tag push `code-review-v*` and publishes the built wheel to PyPI (or TestPyPI for release candidates) using **PyPI Trusted Publishers (OIDC)** — no long-lived secrets. No manual steps after the operator pushes the tag.

## Acceptance criteria

- `.github/workflows/release.yml` exists at the monorepo root (`agentic-skills/.github/workflows/`), not inside the `code-review/` subdir — GitHub Actions reads workflows from the repo root.
- The workflow:
  - Triggers on `push: tags: ['code-review-v*']`. The `code-review-` prefix isolates this subproject's releases from sibling subprojects sharing the monorepo's `.github/workflows/`.
  - Has a `concurrency:` block with `group: release-${{ github.ref }}` and `cancel-in-progress: false` to prevent parallel releases of the same tag.
  - Declares **`permissions: id-token: write`** on the publish job (required by GitHub Actions to mint the OIDC token PyPI exchanges for a short-lived upload token). No other write permissions granted.
  - Runs on `ubuntu-latest`.
  - Steps, in order:
    1. `actions/checkout@v4`
    2. Set up Python 3.12 (or the floor + one) via `actions/setup-python@v5`.
    3. Install uv via the official action or curl-pipe-sh.
    4. `cd code-review && uv sync --frozen`
    5. `cd code-review && uv build` — produces `dist/claude_code_review-X.Y.Z-py3-none-any.whl` and `.tar.gz` (PEP 503 normalises the distribution name `claude-code-review` to the wheel prefix `claude_code_review`).
    6. Determine target: if `github.ref` matches `refs/tags/code-review-v*-rc*` → TestPyPI; else → PyPI.
    7. `cd code-review && uv publish` (PyPI) **or** `cd code-review && uv publish --publish-url https://test.pypi.org/legacy/` (TestPyPI). No `--token` flag, no `UV_PUBLISH_TOKEN` env var — `uv publish` discovers and uses the GitHub OIDC token automatically when the job has `id-token: write`.
  - Fails fast on any non-zero exit; no retry; operator inspects the workflow log on failure.
- **No repository secrets required** for the publish path. The trust relationship lives on PyPI's side (project → Publishing → Trusted Publishers) and on TestPyPI's side, both binding to: GitHub repo `jiludvik2/agentic-skills`, workflow file `.github/workflows/release.yml`. Setup is one-time per registry; documented in `s1-t5-release-runbook`.

## Test specification

- **No self-test of the workflow** — exercised by the first real release. The runbook (`s1-t5`) covers verification.
- **Lint**: optionally run `actionlint` locally on the workflow file to catch syntax errors before tagging. Out of scope for AC pass/fail.

## Notes

- The workflow lives at `agentic-skills/.github/workflows/release.yml` — outside the `code-review/` subdir, at the monorepo root. This is a sandbox-write-blocked path for Claude Code; the operator may need to apply the change via the file system directly. **Flag this to the operator before commit.** The workflow file can be drafted in `/tmp` and the operator copies it into place.
- Trusted Publishers replaces the older `--token` / `UV_PUBLISH_TOKEN` flow. With `id-token: write` granted and the PyPI-side trust relationship configured, `uv publish` (and the upstream `twine`/`pypi-publish` actions) detects the OIDC token automatically. No `--token` flag, no `secrets.PYPI_API_TOKEN`.
- TestPyPI publish URL: `https://test.pypi.org/legacy/` (passed via `uv publish --publish-url`). PyPI is the default and needs no flag.
- Pin action versions to a specific SHA or major (e.g., `@v4`) — never `@main`. Matches the project's exact-pin discipline.
- The first-time release flow:
  1. Operator creates "pending publishers" on PyPI (https://pypi.org/manage/account/publishing/) and on TestPyPI (https://test.pypi.org/manage/account/publishing/), each binding: project name `claude-code-review`, repo `jiludvik2/agentic-skills`, workflow filename `release.yml`. Environment name optional but recommended (e.g., `pypi` / `testpypi`).
  2. Operator bumps version in `code-review/pyproject.toml` to e.g. `0.1.0-rc1`.
  3. Operator commits + tags: `git commit -am "release: 0.1.0-rc1" && git tag code-review-v0.1.0-rc1 && git push --tags`.
  4. Workflow runs; uploads to TestPyPI via OIDC; operator verifies via `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ claude-code-review==0.1.0rc1` in a clean venv.
  5. If green, operator bumps to `0.1.0`, tags `code-review-v0.1.0`, pushes; workflow uploads to PyPI via OIDC.
- After the first successful release, the workflow runs on every subsequent `code-review-v*` tag with no further action — no token to rotate or expire.
