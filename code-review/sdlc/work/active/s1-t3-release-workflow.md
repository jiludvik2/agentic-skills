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

A workflow file at `.github/workflows/release.yml` triggers on tag push `v*` and publishes the built wheel to PyPI (or TestPyPI for release candidates) using repository secrets. No manual steps after the operator pushes the tag.

## Acceptance criteria

- `.github/workflows/release.yml` exists at the monorepo root (`agentic-skills/.github/workflows/`), not inside the `code-review/` subdir — GitHub Actions reads workflows from the repo root.
- The workflow:
  - Triggers on `push: tags: ['v*']`.
  - Has a `concurrency:` block with `group: release-${{ github.ref }}` and `cancel-in-progress: false` to prevent parallel releases of the same tag.
  - Runs on `ubuntu-latest`.
  - Steps, in order:
    1. `actions/checkout@v4`
    2. Set up Python 3.12 (or the floor + one) via `actions/setup-python@v5`.
    3. Install uv via the official action or curl-pipe-sh.
    4. `cd code-review && uv sync --frozen`
    5. `cd code-review && uv build` — produces `dist/code_review-X.Y.Z-py3-none-any.whl` and `.tar.gz`.
    6. Determine target: if `github.ref` matches `refs/tags/v*-rc*` → TestPyPI; else → PyPI.
    7. `cd code-review && uv publish --index <test|prod> --token ${{ secrets.PYPI_API_TOKEN or secrets.TESTPYPI_API_TOKEN }}`.
  - Fails fast on any non-zero exit; no retry; operator inspects the workflow log on failure.
- Repository secrets `PYPI_API_TOKEN` and `TESTPYPI_API_TOKEN` exist on the `jiludvik2/agentic-skills` repo (created by the operator out-of-band; documented in `s1-t5-release-runbook`).

## Test specification

- **No self-test of the workflow** — exercised by the first real release. The runbook (`s1-t5`) covers verification.
- **Lint**: optionally run `actionlint` locally on the workflow file to catch syntax errors before tagging. Out of scope for AC pass/fail.

## Notes

- The workflow lives at `agentic-skills/.github/workflows/release.yml` — outside the `code-review/` subdir, at the monorepo root. This is a sandbox-write-blocked path for Claude Code; the operator may need to apply the change via the file system directly. **Flag this to the operator before commit.** The workflow file can be drafted in `/tmp` and the operator copies it into place.
- `uv publish` reads the token from `UV_PUBLISH_TOKEN` env var if `--token` isn't given. The workflow can use either; pick one and document it.
- TestPyPI index URL: `https://test.pypi.org/legacy/`. PyPI default URL is the production index.
- Pin action versions to a specific SHA or major (e.g., `@v4`) — never `@main`. Matches the project's exact-pin discipline.
- The first-time release flow:
  1. Operator creates `PYPI_API_TOKEN` and `TESTPYPI_API_TOKEN` on the repo (Settings → Secrets and variables → Actions).
  2. Operator bumps version in `code-review/pyproject.toml` to e.g. `0.1.0-rc1`.
  3. Operator commits + tags: `git commit -am "release: 0.1.0-rc1" && git tag v0.1.0-rc1 && git push --tags`.
  4. Workflow runs; uploads to TestPyPI; operator verifies via `pip install --index-url https://test.pypi.org/simple/ code-review` in a clean venv.
  5. If green, operator bumps to `0.1.0`, tags `v0.1.0`, pushes; workflow uploads to PyPI.
- After the first successful release, the workflow runs on every subsequent tag with no further action — assuming token rotation hasn't expired the secrets.
