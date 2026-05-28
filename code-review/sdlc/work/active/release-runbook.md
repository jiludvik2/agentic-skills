---
id: release-runbook
kind: runbook
project: code-review
parent: s1-package-publication
created: 2026-05-28
updated: 2026-05-28
verified-on: null
---

# Release runbook — `claude-code-review`

Publishes the wheel to PyPI (or TestPyPI for release candidates) via GitHub Actions on tag push. Authentication is via PyPI Trusted Publishers (OIDC) — no long-lived tokens.

`release.yml` lives at the monorepo root (`agentic-skills/.github/workflows/release.yml`). It triggers on tags matching `code-review-v*`. Tags containing `-rc` route to TestPyPI; everything else routes to PyPI.

## Procedure

Follow these steps in order. The first release also requires the one-time setup in **Trusted Publishers** and **First-release checklist** below — do those before step 1.

### 1. Pre-flight checks

- CI on `main` (or the branch being released) is green.
- All tests pass locally: `uv run pytest`.
- `git status` is clean.

### 2. Version bump

- Decide the new version per semver. Stay on `0.x.y` while pre-1.0 (no API stability guarantee).
- Edit `code-review/pyproject.toml`: change `version = "..."`.
- Commit: `git commit -am "release: vX.Y.Z[-rc1]"`.

### 3. Tag the release candidate

```bash
git tag code-review-vX.Y.Z-rc1
git push --tags
```

GitHub Actions runs `release.yml`, builds the wheel, and uploads to TestPyPI. Watch the workflow run at `https://github.com/jiludvik2/agentic-skills/actions`.

### 4. Verify on TestPyPI

In a fresh, clean venv:

```bash
pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  claude-code-review==X.Y.Zrc1
claude-code-review --capabilities
```

`--extra-index-url` is required so runtime deps (`typer`, `jsonschema`, etc.) resolve from real PyPI — TestPyPI doesn't host them. PEP 440 normalises the install spec from `X.Y.Z-rc1` to `X.Y.ZrcN` — note the absent hyphen.

Sanity-check the JSON output of `--capabilities`. If anything is broken, skip to **Rollback** below.

### 5. Tag the real release

```bash
git tag code-review-vX.Y.Z
git push --tags
```

GitHub Actions uploads to PyPI on this tag.

### 6. Verify on PyPI

In a fresh, clean venv:

```bash
pip install claude-code-review==X.Y.Z
claude-code-review --capabilities
```

### 7. Announce

Optional but recommended — gives a free changelog page and a GitHub Releases feed:

```bash
gh release create code-review-vX.Y.Z --notes-file CHANGELOG.md
```

Or write notes inline with `--notes "..."`.

## Rollback

PyPI does not allow re-uploading the same version. If a release is broken:

- Bump to `X.Y.Z+1` (patch) and re-tag.
- Mark the broken release "yanked" on PyPI: `Manage` → `Release` → `Yank` (UI-only).
- Note the yanked release in the next CHANGELOG entry so downstream consumers see the explanation.

## Expedited path

If TestPyPI staging isn't useful for a given release (typical for a hotfix), skip steps 3 and 4 and jump from step 2 straight to step 5. Document the omission in the release commit message so it's auditable.

## Trusted Publishers (no tokens to manage)

Authentication is via **PyPI Trusted Publishers (OIDC)**. There are no long-lived secrets stored in the GitHub repository. The trust relationship lives on each registry's side and binds: project name, GitHub repo, workflow filename, optional environment.

The workflow declares `permissions: id-token: write` on its publish job; `uv publish` exchanges the GitHub OIDC identity for a short-lived registry upload token at runtime.

### PyPI Trusted Publisher (one-time)

`https://pypi.org/manage/account/publishing/` → **Add a new pending publisher** (before the project exists) or **Add a new publisher** under an existing project.

- PyPI Project Name: `claude-code-review`
- Owner: `jiludvik2`
- Repository name: `agentic-skills`
- Workflow filename: `release.yml`
- Environment name (optional but recommended): `pypi`

### TestPyPI Trusted Publisher (one-time)

`https://test.pypi.org/manage/account/publishing/` → same form, separate registry. Use the same project name; environment name (if you use one): `testpypi`.

### Troubleshooting

If a workflow fails with `Trusted publisher not configured` / `not authorized`, the trust relationship is missing on the registry side or one of the bindings (repo / workflow filename / environment) doesn't match the workflow's actual identity. Fix on the PyPI/TestPyPI side — **no repository secret changes needed.**

## First-release checklist

Run this list once before the very first release. Subsequent releases skip it.

- PyPI account `jiludvik2` exists.
- TestPyPI account `jiludvik2` exists (separate signup from PyPI).
- PyPI distribution name `claude-code-review` is available — reserve it by configuring a "pending publisher" (PyPI lets you do this before the project is published, and auto-creates the project on the first successful upload). The bare `code-review` is taken on PyPI by an unrelated project and is **not** the target.
- Pending publishers configured on both PyPI and TestPyPI per the **Trusted Publishers** section.
- `permissions: id-token: write` is declared on the publish job in `release.yml` (already done in `s1-t3`).
