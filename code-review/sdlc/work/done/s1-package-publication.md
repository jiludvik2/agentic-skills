---
id: s1-package-publication
kind: story
project: code-review
status: done
parent: epic-deployment-readiness
sources: [adr-0001-publication.md, adr-0012-pypi-publication.md]
created: 2026-05-28
updated: 2026-05-28
closed: 2026-05-28
tags: [publication, pypi, github-actions, release, semver]
verify: all 6 tasks PASS (s1-t0 91142af, s1-t1 89bd120, s1-t2 c2a8c68, s1-t3 342eb7c, s1-t4 1f6a439, s1-t5 5286804+383349b)
review: 5 of 6 tasks CLEAN round-1 (s1-t0..t3, s1-t4 MINOR-ONLY); s1-t5 round-1 IMPORTANT remediated via s1-t5-fix1, round-2 CLEAN. Story-level review MINOR-ONLY (3 Minor + 1 Nit) — all three Minors resolved in this close commit; the Nit dropped.
---

# s1 — Package Publication

## Summary

Publish `code-review` to **PyPI** on tag-push via **GitHub Actions**, with **TestPyPI** for pre-release staging. Versioning: **semver, manual bumps** in `pyproject.toml` + git tag created in the same commit. After publication, `pip install claude-code-review`, `pipx install claude-code-review`, and `uv tool install claude-code-review` all work from a clean environment.

The PyPI **distribution name** is `claude-code-review` (the bare `code-review` is taken on PyPI). The **console-script binary** post-install is also `claude-code-review`. The Python **import name** stays `code_review` (e.g., `python -m code_review.cli …` still works from a source checkout). Tags use a `code-review-` prefix (e.g., `code-review-v0.1.0`) to isolate this subproject's releases from sibling subprojects sharing the monorepo's `.github/workflows/`.

This story extends ADR-0001 (which currently only names `github.com/jiludvik2/agentic-skills` as the source target with no package-registry target) via a new ADR-0012 documenting PyPI as the package registry.

## Depends on

- `s0-deployment-layout-fixup` closed. The wheel must build correctly and bundle all needed JSON files before there's anything worth publishing. s1 starts only after s0 is in `/sdlc/work/done/`.

## Use case

- **As a** host operator
- **I want to** install `code-review` with one of `pip install claude-code-review`, `pipx install claude-code-review`, or `uv tool install claude-code-review`
- **so that** I don't need to clone the dev repo or paste verbose direct-URL installs to use the skill.

## Design choices (locked)

- **Registry**: PyPI (with TestPyPI staging for release candidates).
- **Release mechanism**: GitHub Actions on tag push (`code-review-v*` → PyPI; `code-review-v*-rc*` → TestPyPI), authenticated via **PyPI Trusted Publishers (OIDC)** — no long-lived secrets. See ADR-0012.
- **Versioning**: semver, manual bumps. `pyproject.toml` version + `git tag code-review-vX.Y.Z` in the same commit. Pre-1.0 (`0.x.y`) carries no API stability guarantee.

## Acceptance criteria

### Scenario: PyPI-ready project metadata

- **Given** the `pyproject.toml` after this story
- **When** the package metadata is inspected
- **Then** it carries non-empty values for: `name = "claude-code-review"` (chosen because the bare `code-review` is taken on PyPI), `authors` (name only — email omitted by design), `readme = "README.md"`, `urls` (Homepage, Source, Issues), `classifiers` (including `License :: OSI Approved :: MIT License`, `Programming Language :: Python :: 3.11`, `Programming Language :: Python :: 3.12`, `Operating System :: OS Independent`, `Topic :: Software Development :: Quality Assurance`, `Development Status :: 3 - Alpha`), `keywords`, and `requires-python = ">=3.11"` (the last already present).

### Scenario: console script works post-install

- **Given** `pip install claude-code-review` ran successfully in a clean venv
- **When** the operator runs `claude-code-review --capabilities` (no `python -m` prefix)
- **Then** the command resolves via the `[project.scripts]` entry point (declared as `claude-code-review = "code_review.cli:app"`), runs, and prints valid JSON identical to `python -m code_review.cli --capabilities` from the source tree.
- **And** the same holds after `pipx install claude-code-review` and `uv tool install claude-code-review`.

### Scenario: PyPI publication ADR exists

- **Given** the repo after this story
- **When** `sdlc/work/active/adr-0012-pypi-publication.md` (or moved to `sdlc/docs/decisions/` at story close) is read
- **Then** it records: PyPI as the registry (extending ADR-0001's source target); distribution name `claude-code-review` and console-script binary `claude-code-review` (bare `code-review` taken); semver with manual bumps; GitHub Actions release workflow on tag push (`code-review-v*` → PyPI; `code-review-v*-rc*` → TestPyPI); authentication via **PyPI Trusted Publishers (OIDC)** with no long-lived secrets.

### Scenario: release workflow triggers on tag

- **Given** a `git tag code-review-vX.Y.Z && git push --tags` operation
- **When** GitHub Actions evaluates the trigger
- **Then** `.github/workflows/release.yml` matches `push: tags: ['code-review-v*']`, declares `permissions: id-token: write` on the publish job, and runs a job that (in order): checkout → set up Python 3.11+ → install uv → `uv sync --frozen` → `uv build` → `uv publish` to PyPI using **PyPI Trusted Publishers (OIDC)** — no long-lived secrets.
- **And** tags matching `code-review-v*-rc*` route to TestPyPI via the corresponding TestPyPI Trusted Publisher configuration (`--publish-url https://test.pypi.org/legacy/`).
- **And** a `concurrency:` block prevents parallel releases of the same tag.
- **And** the `code-review-` tag prefix isolates this subproject's releases from sibling subprojects sharing the monorepo's `.github/workflows/`.

### Scenario: pre-publish smoke test catches packaging mistakes

- **Given** the test suite after this story
- **When** `tests/test_console_script_install.py` runs
- **Then** it: builds the wheel with `uv build`; creates a fresh tmpdir venv; `pip install`s the built wheel into that venv; runs `<venv>/bin/claude-code-review --capabilities`; asserts the output is valid JSON and matches the source-tree invocation.
- **And** `tests/test_pyproject_metadata.py` parses `pyproject.toml` and asserts every PyPI-required field is non-empty and well-formed.

### Scenario: release runbook documents the full flow

- **Given** `sdlc/docs/runbooks/release.md` after this story
- **When** an operator follows it for a release
- **Then** they can: bump version in `pyproject.toml`; cut a release-candidate tag (`code-review-vX.Y.Z-rc1`) and verify install from TestPyPI; promote to the real tag (`code-review-vX.Y.Z`); verify install from PyPI; roll back a bad release.
- **And** the runbook documents the one-time **PyPI Trusted Publishers** setup on both `pypi.org` and `test.pypi.org` (pending publisher binding the repo, the workflow filename, and an optional environment), per ADR-0012. No GitHub repository secrets are involved — the workflow exchanges its OIDC identity for a short-lived upload token at runtime.

### Scenario: README.md exists at repo root

- **Given** the repo after this story
- **When** `cat README.md` runs
- **Then** the file exists and renders as the PyPI package description.
- **And** its sections include: install methods (pip, pipx, uv tool); 30-second usage example with `--review` and `--depth`; link to `.claude/skills/code-review/SKILL.md` for the full reference; status (alpha; pre-1.0).
- **Operator-approved content per "What stays human"**: Claude drafts; operator reads and edits before commit.

## Test specification

- **`tests/test_pyproject_metadata.py`** (new) — parses `pyproject.toml`; asserts every PyPI-required field is present and non-empty; asserts the locked set of classifiers is included; asserts `requires-python` matches the supported floor.
- **`tests/test_console_script_install.py`** (new) — exercises the full build + install + invoke loop: `uv build`, fresh venv via `venv.create`, `pip install` the wheel, run `<venv>/bin/claude-code-review --capabilities`, assert JSON validity + structural match against source-tree output.
- **No CI/workflow self-test.** The release workflow itself is exercised by the first real release; the runbook covers verification.
- **Existing tests** continue to pass — s0's `test_wheel_packaging.py` already proves the wheel builds and installs; this story only adds the metadata + console-script + workflow layer.

## Out of scope

- API-stability promises — `code-review` stays at `0.x.y` (alpha) for this epic.
- Multi-registry publishing (GitHub Packages, private indexes) — PyPI is the only target.
- Conda / Homebrew / system packages.
- Telemetry on install counts.
- Auto-bumping version (e.g., `release-please`, `semantic-release`) — manual bumps stay until they prove painful.
- Wheel-build correctness — proved by `s0-t1`.
- Branch protection / release-approval gates on `main` — orthogonal; covered by the operator's existing repo settings.

## Open questions / risks

- **PyPI account availability.** Story execution needs an active `pypi.org` account (and a separate `test.pypi.org` account) for the operator. Trusted Publishers requires no long-lived tokens — the operator instead configures a "pending publisher" trust relationship on each registry before the first release. Out-of-band setup; documented in the release runbook.
- **PyPI name (resolved).** `code-review` is taken on PyPI; this story publishes under `claude-code-review`. Console-script binary also renamed to `claude-code-review`; Python import name unchanged (`code_review`).
- **Release auth (resolved).** PyPI Trusted Publishers (OIDC) — no long-lived secrets. The publish workflow exchanges GitHub Actions' OIDC identity for a short-lived PyPI upload token at runtime; the trust relationship is configured per-registry (PyPI + TestPyPI) on the operator's first release.
- **README content.** Operator-approved per "What stays human". A draft is in scope for s1-t1; the operator's edits gate the commit.

## Close notes (2026-05-28)

Story-level Review (`reviewer` against `e9aaed2..HEAD`, 15 commits) returned MINOR-ONLY: 3 Minor + 1 Nit. All three Minors were resolved as part of this close commit rather than carried as backlog:

1. **Runbook path mismatch** — parent story referenced `sdlc/docs/runbooks/release.md`, runbook landed at `sdlc/work/active/release-runbook.md`. Resolved by the close-ceremony move/rename: runbook is now at `sdlc/docs/runbooks/release.md`.
2. **Missing runbook scaffold test** — added `test_release_runbook_exists()` to `tests/test_scaffold.py`, mirroring the dual-path pattern of `test_adr_0012_pypi_publication_exists()`.
3. **Redundant parenthetical in runbook step 2** — over-cooked in `s1-t5-fix1`. Tightened to "Edit `pyproject.toml` (at the `code-review/` package root): change `version = "..."`."

The Nit (one-line comment in `release.yml` justifying the Python 3.12 publish-version choice) was dropped — current state is correct as the reviewer themselves noted.

The s1-t4 round-1 review surfaced 2 Minor + 2 Nit that were left as future-visibility (recorded in the closed s1-t4 task's frontmatter) rather than actioned. They remain available as opportunistic cleanup.

Artefacts produced this story and their final homes:
- `pyproject.toml` — refreshed metadata (in-place).
- `README.md` — new (project root).
- `adr-0012-pypi-publication.md` → `sdlc/docs/decisions/`.
- `release.md` → `sdlc/docs/runbooks/` (renamed from `release-runbook.md`).
- `.github/workflows/release.yml` → monorepo root (sandbox-blocked path; placed by operator).
- `tests/test_pyproject_metadata.py` (new); `tests/test_console_script_install.py` (new); `tests/test_scaffold.py` (extended with README + ADR-0012 + runbook existence assertions).
