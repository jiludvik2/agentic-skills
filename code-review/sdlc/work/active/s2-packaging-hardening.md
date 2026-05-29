---
id: s2-packaging-hardening
kind: story
project: code-review
status: active
parent: epic-deployment-readiness
sources: [packaging-research-2026-05-29]
created: 2026-05-29
updated: 2026-05-29
tags: [packaging, dependencies, ci, importlib-metadata, release-workflow, skill-bundle]
---

# s2 — Packaging Hardening

## Summary

Bring `claude-code-review`'s packaging in line with current (2024-2026) Python CLI best practice before the first public release. Seven concrete defects identified by external research + repo audit, grouped into a single story because they all touch the publication contract and want to land together: relax exact runtime pins so consumers can resolve transitive deps; bundle `LICENSE` in the wheel; single-source `__version__` via `importlib.metadata`; split the release workflow into separate build / test-installed-artifact / publish jobs; add a CI workflow that gates `main`/PRs on tests + lint + types; correct the `SKILL.md` invocation line to use the installed console script; fix the `code-review.toml.example` path bug in `setup.sh`.

The story is execution-only — no new ADR. Every change either implements existing ADR-0012 / ADR-0003 intent more faithfully (deps, license, release workflow) or fixes a defect surfaced after s1 closed.

## Depends on

- `s1-package-publication` closed (it is — commit `42045ba`). This story refines what s1 shipped; it doesn't reopen any s1 decision.

## Use case

- **As a** host operator (or any third party) installing `claude-code-review` from PyPI
- **I want to** install it without pip-resolution conflicts, receive a wheel with `LICENSE` included, follow accurate skill documentation, and trust that releases were tested
- **so that** `claude-code-review` behaves like other well-packaged Python CLI tools and is fit for unattended public use.

## Design choices (locked)

- **Dependency bounds**: lower bounds at the currently-pinned minor, no upper bounds, allow patch/minor advances. (Lockfile `uv.lock` continues to pin exact versions for reproducible dev — that doesn't change.) This is the PyPA-recommended pattern for distributed packages.
- **`__version__` source**: `importlib.metadata.version("claude-code-review")` with a `PackageNotFoundError` fallback for editable/uninstalled checkouts. `pyproject.toml` stays the single source of truth.
- **LICENSE**: a `code-review/LICENSE` file (copy of the agentic-skills root MIT license), referenced from `pyproject.toml` as `license = { file = "LICENSE" }`. Hatchling then ships it in the wheel.
- **Release workflow shape**: three jobs — `build`, `test-dist`, `publish` — with `id-token: write` only on `publish`. `pypa/gh-action-pypi-publish@release/v1` replaces the current `uv publish` step so OIDC handling stays in the official action. `setup-uv@v3` → `@v5`.
- **CI workflow shape**: triggers on `push` to `main` and on `pull_request` against `main`, with path filter `code-review/**` so sibling-package edits in the monorepo don't fan out. Runs `uv sync --frozen` + `uv run pytest -m "not slow and not integration"` + `uv run ruff check .` + `uv run mypy code_review`. One job, Python 3.12 only (matching release-published version).
- **SKILL.md invocation**: leads with `claude-code-review …` (the installed binary). The legacy `python -m code_review.cli …` form stays in a developer-mode note since `SKILL.md` is also read in source checkouts during the SDLC verb cycle.
- **`code-review.toml.example` path**: fixed in `setup.sh` by introducing a `BUNDLE_DIR` resolved to `<repo>/.claude/skills/code-review/` in dev layout (i.e. its actual home), with the existing `SKILL_ROOT` reserved for the package root. The example file does not move.

## Acceptance criteria

### Scenario: runtime dependencies allow consumer resolution

- **Given** `pyproject.toml` after this story
- **When** `[project.dependencies]` is parsed
- **Then** every entry uses a `>=X.Y` lower bound (anchored at the currently-pinned minor version) with no upper bound, except where an upper bound has a written justification in a comment on the same line.
- **And** `uv sync --frozen` continues to install exactly the lockfile versions (no behaviour change for developers).
- **And** the wheel built after the change carries the same lower-bound specifiers in its `METADATA`.

### Scenario: LICENSE is bundled in the wheel

- **Given** the wheel built after this story
- **When** `unzip -l dist/claude_code_review-0.1.0-py3-none-any.whl` is inspected
- **Then** a `LICENSE` file appears in the wheel at the `claude_code_review-0.1.0.dist-info/licenses/` location (Hatchling's standard placement under PEP 639) or at the top of the dist-info directory.
- **And** `pyproject.toml` declares `license = { file = "LICENSE" }` referencing `code-review/LICENSE`.
- **And** `code-review/LICENSE` exists and is byte-identical to `agentic-skills/LICENSE`.

### Scenario: `__version__` is single-sourced from package metadata

- **Given** the package after this story
- **When** `import code_review; print(code_review.__version__)` runs in an installed environment
- **Then** the value equals `pyproject.toml`'s `[project] version`.
- **And** in an uninstalled / source-tree-only environment (no installed distribution), `code_review.__version__` returns the fallback string `"0.0.0+dev"` (or equivalent sentinel) rather than raising `PackageNotFoundError`.
- **And** there is no hardcoded version string in `code_review/__init__.py`.

### Scenario: release workflow validates the built artifact before publishing

- **Given** the `.github/workflows/release.yml` after this story
- **When** a `code-review-v*` tag is pushed and the workflow runs
- **Then** it has three jobs in order: `build` → `test-dist` → `publish`.
- **And** `build` runs `uv build` and uploads `dist/` as an artifact.
- **And** `test-dist` downloads the artifact, creates a fresh venv, `pip install`s the wheel, runs `claude-code-review --capabilities`, asserts the output parses as JSON. No source-tree access.
- **And** `publish` (`needs: test-dist`) downloads the artifact and calls `pypa/gh-action-pypi-publish@release/v1` with `id-token: write` declared at job (not workflow) level.
- **And** the workflow uses `astral-sh/setup-uv@v5` with `enable-cache: true` and `cache-dependency-glob: "code-review/uv.lock"`.
- **And** the existing TestPyPI / PyPI routing (by `-rc` in the tag) is preserved.

### Scenario: CI runs tests on every push and PR

- **Given** the repo after this story
- **When** a commit is pushed to `main`, or a PR is opened against `main`, touching any path under `code-review/`
- **Then** `.github/workflows/ci.yml` triggers a single `test` job that runs (in order): checkout → `astral-sh/setup-uv@v5` (with cache) → `uv sync --frozen` → `uv run pytest -m "not slow and not integration"` → `uv run ruff check .` → `uv run mypy code_review`.
- **And** the workflow file declares a path filter `code-review/**` so edits to sibling packages don't trigger it.
- **And** the workflow has no `id-token: write` and no secrets — it is read-only CI.

### Scenario: SKILL.md leads with the installed console script

- **Given** `.claude/skills/code-review/SKILL.md` after this story
- **When** an operator reads the Invocation section
- **Then** the primary example uses `claude-code-review …` (the installed binary).
- **And** a single secondary line notes `python -m code_review.cli …` works in a source checkout, scoped to developer/SDLC contexts.
- **And** no other example in the file uses `python -m code_review.cli …` as the primary form (regressions caught by test below).

### Scenario: `setup.sh` correctly locates the bundled example config

- **Given** the developer-layout repo after this story
- **When** `./scripts/setup.sh` runs
- **Then** step 5 ("Starter config template") prints `available: <abs-path>` for `<repo>/.claude/skills/code-review/code-review.toml.example`, not `missing: …`.
- **And** the printed `cp` hint points to `<host-root>/code-review.toml` as before.
- **And** the script exits 0 in dev layout.

## Test specification

- **`tests/test_pyproject_metadata.py`** (extend) — assert every `[project.dependencies]` entry uses `>=` (not `==`); assert `license` is a `{ file = "LICENSE" }` declaration; assert no upper bounds present (or every upper bound has an inline `#` comment justification).
- **`tests/test_pyproject_metadata.py`** (extend, separate test) — assert `code-review/LICENSE` exists and equals `agentic-skills/LICENSE` byte-for-byte (latter resolved via repo-relative path).
- **New: `tests/test_version_source.py`** — assert `code_review.__version__ == importlib.metadata.version("claude-code-review")` when the package is installed; assert no string literal matching `"\d+\.\d+\.\d+"` appears in `code_review/__init__.py` source.
- **`tests/test_wheel_packaging.py`** (extend) — assert the built wheel contains a `LICENSE` file under `*.dist-info/`.
- **New: `tests/test_release_workflow.py`** — parse `.github/workflows/release.yml` as YAML; assert it has three jobs `build`, `test-dist`, `publish`; assert `needs` chain; assert `id-token: write` lives only on `publish`; assert `publish` step uses `pypa/gh-action-pypi-publish@release/v1`; assert `astral-sh/setup-uv@v5`.
- **New: `tests/test_ci_workflow.py`** — parse `.github/workflows/ci.yml`; assert triggers (`push` to `main`, `pull_request` against `main`); assert path filter `code-review/**`; assert single job runs pytest + ruff + mypy in sequence; assert no `id-token: write` and no `permissions:` block elevated beyond default.
- **New: `tests/test_skill_md_invocation.py`** — parse `.claude/skills/code-review/SKILL.md`; assert the first non-blank line of the Invocation code block starts with `claude-code-review`; assert no other code block uses `python -m code_review.cli` as the leading invocation.
- **New: `tests/test_setup_sh_example_path.py`** — assert `setup.sh` references `BUNDLE_DIR` (or equivalent) resolving to `.claude/skills/code-review/`; alternative: invoke `bash -c 'source setup.sh && echo "$EXAMPLE_PATH"'` in a smoke variant and assert the path exists.
- **Regression**: existing 304-test green bar continues to pass; `ruff check .` clean; `mypy --strict` on `code_review/` clean (pre-existing `conftest.py` duplicate-module noise carries on unchanged).

## Out of scope

- Adding new analyzers — orthogonal.
- Changing the PyPI distribution name, console-script name, or import name — locked in s1.
- Workspace-level `uv.lock` spanning sibling skills — possible future cleanup; doesn't block packaging hardening.
- Python 3.13 classifier — covered by the parallel "L2" finding and will land as a one-line follow-up after this story, since classifiers are operator-approved metadata per s1's pattern.
- CHANGELOG.md — also "L"-priority follow-up; deferred to s3 if/when the epic continues.
- Updating the root `agentic-skills/README.md` to list `code-review` — deferred; covered by a separate documentation task outside this story.
- Distributing the SKILL.md via PyPI (an `install-skill` subcommand) — research-suggested, but the current model is git-based and the operator hasn't agreed to ship a side-effect-producing subcommand. Out of scope.

## Open questions / risks

- **Backward compat of relaxed pins.** Risk: a downstream `bandit` or `semgrep` release silently changes output and our adapters mis-parse. Mitigation: lockfile-pinned dev environment + the existing per-adapter golden tests catch parser drift on every commit. The release workflow's `test-dist` step also exercises the production wheel against current pinned versions.
- **`LICENSE` location convention drift.** PEP 639 standardised license metadata in 2024; Hatchling's exact `dist-info` placement (top-level vs `licenses/` subdirectory) depends on the Hatchling version. Test asserts on the wheel's containment of `LICENSE`, not on its precise sub-path, to avoid brittleness.
- **CI workflow path filter granularity.** `code-review/**` triggers on changes to `code-review/sdlc/**` too, which is fine (no harm in running tests on SDLC artefact edits) but means more CI minutes. Alternative: more specific path filters (`code-review/code_review/**`, `code-review/tests/**`, `code-review/pyproject.toml`, `code-review/uv.lock`). Locked-in: the broader filter, accepting the extra runs.

## Tasks

- `s2-t0-license-bundling` — copy `LICENSE` into `code-review/`, switch `pyproject.toml` to `license = { file = "LICENSE" }`, assert LICENSE in built wheel.
- `s2-t1-relax-runtime-dependency-pins` — change every `==` in `[project.dependencies]` to `>=` (at currently-pinned minor); test guards regressions.
- `s2-t2-importlib-metadata-version-source` — replace hardcoded `__version__` with `importlib.metadata.version()` + fallback; test asserts equality with `pyproject.toml`.
- `s2-t3-release-workflow-three-job-split` — restructure `release.yml` into `build` → `test-dist` → `publish`; upgrade `setup-uv@v5`; switch publish to `pypa/gh-action-pypi-publish@release/v1`; test parses the YAML.
- `s2-t4-ci-workflow` — new `.github/workflows/ci.yml` running pytest + ruff + mypy on push/PR with path filter; test parses the YAML.
- `s2-t5-skill-md-and-setup-script-fixes` — SKILL.md invocation lines lead with `claude-code-review`; `setup.sh` example path resolves correctly via new `BUNDLE_DIR`; tests assert both.
