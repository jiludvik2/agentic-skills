---
id: release-runbook
kind: runbook
project: code-review
parent: s1-package-publication
created: 2026-05-28
updated: 2026-05-28
verified-on: null
---

# Release runbook — `polyreview`

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
- Edit `pyproject.toml` (at the `code-review/` package root): change `version = "..."`.
- Update `CHANGELOG.md` (operator-maintained at the `code-review/` package root) with the new version's notes — created at the first release if it doesn't exist yet.
- Commit: `git commit -am "release: vX.Y.Z[-rc1]"`.

### 3. Tag the release candidate

```bash
git tag code-review-vX.Y.Z-rc1
git push --tags
```

GitHub Actions runs `release.yml`, builds the wheel, and uploads to TestPyPI. Watch the workflow run at [GitHub Actions](https://github.com/jiludvik2/agentic-skills/actions).

### 4. Verify on TestPyPI

In a fresh, clean venv:

```bash
pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  polyreview==X.Y.Zrc1
polyreview --capabilities
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
pip install polyreview==X.Y.Z
polyreview --capabilities
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

Authentication is via **PyPI Trusted Publishers (OIDC)**. There are no long-lived secrets stored in the GitHub repository. The trust relationship lives on each registry's side and binds: project name, GitHub repo, workflow filename, environment.

The workflow declares `permissions: id-token: write` scoped to the `publish` job only. The publish step uses `pypa/gh-action-pypi-publish@release/v1` (the official PyPA action); the action exchanges the GitHub OIDC identity for a short-lived registry upload token at runtime.

### Workflow shape (post s2-t3)

`release.yml` is three sequential jobs:

1. **`build`** — `uv sync --frozen` → `uv build` → upload `dist/` as an artifact. No special permissions.
2. **`test-dist`** (`needs: build`) — download the artifact, create a fresh venv, `pip install` the wheel, run `polyreview --capabilities`, assert the output parses as JSON. This catches packaging defects (missing data files, broken entry points) BEFORE publication, against the installed wheel rather than the source tree. No special permissions.
3. **`publish`** (`needs: test-dist`) — validates the tag matches `code-review-vX.Y.Z[-rcN]` (rejects ambiguous tags like `-rcdraft`), downloads the artifact, calls `pypa/gh-action-pypi-publish@release/v1` with the appropriate registry URL. `permissions: id-token: write` at job level; `environment: pypi` (or `testpypi` for `-rc` tags).

The `environment:` binding is now **mandatory** for the Trusted Publisher configuration — see the per-registry sections below.

### PyPI Trusted Publisher (one-time)

`https://pypi.org/manage/account/publishing/` → **Add a new pending publisher** (before the project exists) or **Add a new publisher** under an existing project.

- PyPI Project Name: `polyreview`
- Owner: `jiludvik2`
- Repository name: `agentic-skills`
- Workflow filename: `release.yml`
- Environment name: `pypi` (**required** — the workflow's `publish` job declares `environment: pypi` for final releases since s2-t3)

### TestPyPI Trusted Publisher (one-time)

`https://test.pypi.org/manage/account/publishing/` → same form, separate registry. Use the same project name; environment name: `testpypi` (**required** — the workflow's `publish` job declares `environment: testpypi` for `-rc` tags since s2-t3).

### Troubleshooting

If a workflow fails with `Trusted publisher not configured` / `not authorized`, the trust relationship is missing on the registry side or one of the bindings (repo / workflow filename / environment) doesn't match the workflow's actual identity. Fix on the PyPI/TestPyPI side — **no repository secret changes needed.**

## First-release checklist

Run this list once before the very first release. Subsequent releases skip it.

- PyPI account `jiludvik2` exists.
- TestPyPI account `jiludvik2` exists (separate signup from PyPI).
- PyPI distribution name `polyreview` is available (verified 2026-05-29) — reserve it by configuring a "pending publisher" (PyPI lets you do this before the project is published, and auto-creates the project on the first successful upload). The distribution was renamed from `claude-code-review` per ADR-0014; see **Rename history** below.
- Pending publishers configured on both PyPI and TestPyPI per the **Trusted Publishers** section.
- `permissions: id-token: write` is declared on the publish job in `release.yml` (set up in `s1-t3`; the three-job split in `s2-t3` keeps it scoped to `publish` only).
- The `pypi` and `testpypi` GitHub environments exist on the `agentic-skills` repo (`Settings → Environments`). Names must match exactly — they're the discriminator in the Trusted Publisher bindings.

## Rename history

- **2026-05-29 — `claude-code-review` → `polyreview`** (ADR-0014). The distribution and console binary were renamed before the first PyPI release to drop the vendor prefix: the tool is agent-agnostic (its Agent Skill bundle is read by Copilot/Cursor/Codex and others, not only Claude). The Python import name `code_review`, the skill bundle path, and the **release-tag prefix `code-review-v*`** were deliberately kept — each names the capability, not the vendor.
- **Deferred follow-up:** publish a `claude-code-review` 0.x.y redirect meta-package depending only on `polyreview`, so anyone who typed the old name still lands on the tool. Do this once `polyreview` has its first successful publish (it depends on `polyreview` existing on the index).
