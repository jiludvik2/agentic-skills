---
id: s1-t5-release-runbook
kind: task
project: code-review
status: active
parent: s1-package-publication
created: 2026-05-28
updated: 2026-05-28
---

# s1-t5 — Release runbook

## Outcome

A runbook at `sdlc/docs/runbooks/release.md` documents the full release flow end-to-end: version bump, TestPyPI rehearsal, real release, rollback. Future-operator-readable; covers every step the GitHub Actions workflow doesn't automate.

## Acceptance criteria

- `sdlc/work/active/release-runbook.md` (moves to `sdlc/docs/runbooks/release.md` at story close per the SDLC's co-locate-active-work convention). Frontmatter: `kind: runbook`, `parent: s1-package-publication`, `verified-on: <release date>`.
- Contents (numbered procedure, plus reference sections):

  ### Procedure (followed in order)

  1. **Pre-flight checks**
     - Green CI on `main` (or the branch being released).
     - All tests pass locally: `uv run pytest`.
     - `git status` clean.

  2. **Version bump**
     - Decide the new version per semver. `0.x.y` while pre-1.0.
     - Edit `pyproject.toml`: change `version = "..."`.
     - Commit: `git commit -am "release: vX.Y.Z[-rc1]"`.

  3. **Tag the release candidate**
     - `git tag vX.Y.Z-rc1`
     - `git push --tags`
     - GitHub Actions runs `release.yml`; uploads to TestPyPI.
     - Watch the workflow logs (link in the procedure).

  4. **Verify on TestPyPI**
     - In a clean venv: `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ code-review==X.Y.Zrc1`.
     - The `--extra-index-url` is needed to resolve runtime deps (`typer`, `jsonschema`, etc.) from real PyPI.
     - Run `code-review --capabilities`; sanity-check the JSON output.
     - If broken: skip to **Rollback** below.

  5. **Tag the real release**
     - `git tag vX.Y.Z`
     - `git push --tags`
     - GitHub Actions uploads to PyPI.

  6. **Verify on PyPI**
     - In a clean venv: `pip install code-review==X.Y.Z`.
     - `code-review --capabilities`.

  7. **Announce**
     - GitHub Release: `gh release create vX.Y.Z --notes-file CHANGELOG.md` (or write notes inline).

  ### Rollback

  - PyPI does not allow re-uploading the same version. Bump to `X.Y.Z+1` (patch) and re-tag.
  - Mark the broken release "yanked" on PyPI: `Manage` → `Release` → `Yank` (operator clicks; UI-only).
  - Document the yanked release in the next CHANGELOG entry.

  ### Token management

  - `PYPI_API_TOKEN`: created at https://pypi.org/manage/account/token/, scoped to project `code-review`. Stored as a GitHub repository secret on `jiludvik2/agentic-skills`.
  - `TESTPYPI_API_TOKEN`: created at https://test.pypi.org/manage/account/token/, same scoping. Stored same way.
  - Tokens rotate at the operator's discretion. If a workflow fails with auth errors, regenerate the token, update the repo secret.

  ### First-release checklist

  - PyPI account `jiludvik2` exists.
  - TestPyPI account `jiludvik2` exists (separate signup from PyPI).
  - Package name `code-review` reserved (publish a `0.0.1` placeholder if needed to claim the name before contested).
  - Both tokens generated and stored.

## Test specification

- **No automated test** — runbooks are prose; verification is reading + the first real release.
- The runbook itself can be smoke-tested by running through it for the very first release (`v0.1.0-rc1` → TestPyPI → verify → `v0.1.0` → PyPI).

## Notes

- The runbook lives in `/sdlc/docs/runbooks/` post-close. Active-period draft sits in `/sdlc/work/active/` per co-locate-active-work.
- The "first release checklist" exists because the very first release has setup steps (account creation, name reservation) that don't repeat. Subsequent releases skip those.
- `gh release create` is optional — operator's choice whether to create GitHub Releases alongside PyPI releases. Recommend yes (free changelog page, GitHub Releases feed).
- If the operator decides not to use TestPyPI for staging (e.g., for a hotfix), the procedure becomes shorter: skip steps 3–4, jump straight to step 5. Document this as an "expedited path".
