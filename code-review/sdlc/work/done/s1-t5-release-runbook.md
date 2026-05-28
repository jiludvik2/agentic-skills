---
id: s1-t5-release-runbook
kind: task
project: code-review
status: done
parent: s1-package-publication
created: 2026-05-28
updated: 2026-05-28
closed: 2026-05-28
verify: PASS (commit 5286804; all 17 spec'd Contents items covered; 303 passed/6 skipped; ruff clean; pre-existing mypy conftest dup carried)
review: round-1 commit 5286804 → 1 Important + 1 Minor + 1 Nit; remediated in s1-t5-fix1 commit 383349b; round-2 CLEAN (all three resolved, zero new defects)
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
     - `git tag code-review-vX.Y.Z-rc1`
     - `git push --tags`
     - GitHub Actions runs `release.yml`; uploads to TestPyPI.
     - Watch the workflow logs (link in the procedure).

  4. **Verify on TestPyPI**
     - In a clean venv: `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ claude-code-review==X.Y.Zrc1`.
     - The `--extra-index-url` is needed to resolve runtime deps (`typer`, `jsonschema`, etc.) from real PyPI.
     - Run `claude-code-review --capabilities`; sanity-check the JSON output.
     - If broken: skip to **Rollback** below.

  5. **Tag the real release**
     - `git tag code-review-vX.Y.Z`
     - `git push --tags`
     - GitHub Actions uploads to PyPI.

  6. **Verify on PyPI**
     - In a clean venv: `pip install claude-code-review==X.Y.Z`.
     - `claude-code-review --capabilities`.

  7. **Announce**
     - GitHub Release: `gh release create code-review-vX.Y.Z --notes-file CHANGELOG.md` (or write notes inline).

  ### Rollback

  - PyPI does not allow re-uploading the same version. Bump to `X.Y.Z+1` (patch) and re-tag.
  - Mark the broken release "yanked" on PyPI: `Manage` → `Release` → `Yank` (operator clicks; UI-only).
  - Document the yanked release in the next CHANGELOG entry.

  ### Trusted Publishers (no tokens to manage)

  Authentication is via **PyPI Trusted Publishers (OIDC)**. There are no long-lived secrets stored in the GitHub repository. The trust relationship lives on each registry's side and binds: project name, GitHub repo, workflow filename, optional environment.

  - **PyPI Trusted Publisher** (one-time): https://pypi.org/manage/account/publishing/ → **Add a new pending publisher** before the project exists, or **Add a new publisher** under an existing project. Fill in:
    - PyPI Project Name: `claude-code-review`
    - Owner: `jiludvik2`
    - Repository name: `agentic-skills`
    - Workflow filename: `release.yml`
    - Environment name (optional but recommended): `pypi`
  - **TestPyPI Trusted Publisher** (one-time): https://test.pypi.org/manage/account/publishing/ → same form, separate registry. Use the same project name; environment name (if you use one): `testpypi`.
  - If a workflow fails with `Trusted publisher not configured` / `not authorized`, the trust relationship is missing or the binding (repo, workflow, environment) doesn't match the workflow's actual identity. Fix on the PyPI/TestPyPI side; **no repo secret changes needed.**

  ### First-release checklist

  - PyPI account `jiludvik2` exists.
  - TestPyPI account `jiludvik2` exists (separate signup from PyPI).
  - PyPI distribution name `claude-code-review` available — confirmed before this story; reserve by configuring a "pending publisher" (PyPI lets you do this before the project is published, then auto-creates the project on the first successful upload). The bare `code-review` is already taken on PyPI by an unrelated project and is **not** the target.
  - Pending publishers configured on both PyPI and TestPyPI per the previous section.
  - `permissions: id-token: write` declared on the publish job in `release.yml`.

## Test specification

- **No automated test** — runbooks are prose; verification is reading + the first real release.
- The runbook itself can be smoke-tested by running through it for the very first release (`v0.1.0-rc1` → TestPyPI → verify → `v0.1.0` → PyPI).

## Notes

- The runbook lives in `/sdlc/docs/runbooks/` post-close. Active-period draft sits in `/sdlc/work/active/` per co-locate-active-work.
- The "first release checklist" exists because the very first release has setup steps (account creation, name reservation) that don't repeat. Subsequent releases skip those.
- `gh release create` is optional — operator's choice whether to create GitHub Releases alongside PyPI releases. Recommend yes (free changelog page, GitHub Releases feed).
- If the operator decides not to use TestPyPI for staging (e.g., for a hotfix), the procedure becomes shorter: skip steps 3–4, jump straight to step 5. Document this as an "expedited path".
