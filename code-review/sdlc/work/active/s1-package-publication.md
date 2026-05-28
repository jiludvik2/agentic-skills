---
id: s1-package-publication
kind: story
project: code-review
status: active
parent: epic-deployment-readiness
sources: [adr-0001-publication.md]
created: 2026-05-28
updated: 2026-05-28
tags: [publication, pypi, github-actions, release, semver]
---

# s1 — Package Publication

## Summary

Publish `code-review` to **PyPI** on tag-push via **GitHub Actions**, with **TestPyPI** for pre-release staging. Versioning: **semver, manual bumps** in `pyproject.toml` + git tag created in the same commit. After publication, `pip install code-review`, `pipx install code-review`, and `uv tool install code-review` all work from a clean environment.

This story extends ADR-0001 (which currently only names `github.com/jiludvik2/agentic-skills` as the source target with no package-registry target) via a new ADR-0012 documenting PyPI as the package registry.

## Depends on

- `s0-deployment-layout-fixup` closed. The wheel must build correctly and bundle all needed JSON files before there's anything worth publishing. s1 starts only after s0 is in `/sdlc/work/done/`.

## Use case

- **As a** host operator
- **I want to** install `code-review` with one of `pip install code-review`, `pipx install code-review`, or `uv tool install code-review`
- **so that** I don't need to clone the dev repo or paste verbose direct-URL installs to use the skill.

## Design choices (locked)

- **Registry**: PyPI (with TestPyPI staging for release candidates).
- **Release mechanism**: GitHub Actions on tag push (`v*` → PyPI; `v*-rc*` → TestPyPI).
- **Versioning**: semver, manual bumps. `pyproject.toml` version + `git tag vX.Y.Z` in the same commit. Pre-1.0 (`0.x.y`) carries no API stability guarantee.

## Acceptance criteria

### Scenario: PyPI-ready project metadata

- **Given** the `pyproject.toml` after this story
- **When** the package metadata is inspected
- **Then** it carries non-empty values for: `authors` (name + email), `readme = "README.md"`, `urls` (Homepage, Source, Issues), `classifiers` (including `License :: OSI Approved :: MIT License`, `Programming Language :: Python :: 3.11`, `Programming Language :: Python :: 3.12`, `Operating System :: OS Independent`, `Topic :: Software Development :: Quality Assurance`, `Development Status :: 3 - Alpha`), `keywords`, and `requires-python = ">=3.11"` (the last already present).

### Scenario: console script works post-install

- **Given** `pip install code-review` ran successfully in a clean venv
- **When** the operator runs `code-review --capabilities` (no `python -m` prefix)
- **Then** the command resolves via the `[project.scripts]` entry point (already declared as `code-review = "code_review.cli:app"`), runs, and prints valid JSON identical to `python -m code_review.cli --capabilities` from the source tree.
- **And** the same holds after `pipx install code-review` and `uv tool install code-review`.

### Scenario: PyPI publication ADR exists

- **Given** the repo after this story
- **When** `sdlc/work/active/adr-0012-pypi-publication.md` (or moved to `sdlc/docs/decisions/` at story close) is read
- **Then** it records: PyPI as the registry (extending ADR-0001's source target); semver with manual bumps; GitHub Actions release workflow on tag push; TestPyPI used pre-release; secret-management notes (`PYPI_API_TOKEN`, `TESTPYPI_API_TOKEN`).

### Scenario: release workflow triggers on tag

- **Given** a `git tag vX.Y.Z && git push --tags` operation
- **When** GitHub Actions evaluates the trigger
- **Then** `.github/workflows/release.yml` matches `push: tags: ['v*']`, runs a job that (in order): checkout → set up Python 3.11+ → install uv → `uv sync --frozen` → `uv build` → `uv publish` (or equivalent) to PyPI using the `PYPI_API_TOKEN` secret.
- **And** tags matching `v*-rc*` route to TestPyPI via the `TESTPYPI_API_TOKEN` secret with `--repository-url https://test.pypi.org/legacy/`.
- **And** a `concurrency:` block prevents parallel releases of the same tag.

### Scenario: pre-publish smoke test catches packaging mistakes

- **Given** the test suite after this story
- **When** `tests/test_console_script_install.py` runs
- **Then** it: builds the wheel with `uv build`; creates a fresh tmpdir venv; `pip install`s the built wheel into that venv; runs `<venv>/bin/code-review --capabilities`; asserts the output is valid JSON and matches the source-tree invocation.
- **And** `tests/test_pyproject_metadata.py` parses `pyproject.toml` and asserts every PyPI-required field is non-empty and well-formed.

### Scenario: release runbook documents the full flow

- **Given** `sdlc/docs/runbooks/release.md` after this story
- **When** an operator follows it for a release
- **Then** they can: bump version in `pyproject.toml`; cut a release-candidate tag (`vX.Y.Z-rc1`) and verify install from TestPyPI; promote to the real tag (`vX.Y.Z`); verify install from PyPI; roll back a bad release.
- **And** the runbook documents how to create `PYPI_API_TOKEN` and `TESTPYPI_API_TOKEN` and where they live in GitHub repository secrets.

### Scenario: README.md exists at repo root

- **Given** the repo after this story
- **When** `cat README.md` runs
- **Then** the file exists and renders as the PyPI package description.
- **And** its sections include: install methods (pip, pipx, uv tool); 30-second usage example with `--review` and `--depth`; link to `.claude/skills/code-review/SKILL.md` for the full reference; status (alpha; pre-1.0).
- **Operator-approved content per "What stays human"**: Claude drafts; operator reads and edits before commit.

## Test specification

- **`tests/test_pyproject_metadata.py`** (new) — parses `pyproject.toml`; asserts every PyPI-required field is present and non-empty; asserts the locked set of classifiers is included; asserts `requires-python` matches the supported floor.
- **`tests/test_console_script_install.py`** (new) — exercises the full build + install + invoke loop: `uv build`, fresh venv via `venv.create`, `pip install` the wheel, run `<venv>/bin/code-review --capabilities`, assert JSON validity + structural match against source-tree output.
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

- **PyPI account / token availability.** Story execution needs an active `pypi.org` account for the operator and a generated API token scoped to the `code-review` project. Out-of-band setup; flagged in the release runbook.
- **Name availability on PyPI.** `code-review` may already be taken or reserved. If so, the operator picks an alternative (`sdlc-code-review`, `code-review-sdlc`, etc.) and the story's first task updates `name` in `pyproject.toml` to match. The console-script name follows.
- **README content.** Operator-approved per "What stays human". A draft is in scope for s1-t1; the operator's edits gate the commit.
