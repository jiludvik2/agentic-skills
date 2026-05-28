---
id: s0-deployment-layout-fixup
kind: story
project: code-review
status: active
parent: epic-deployment-readiness
sources: [adr-0007-package-bundled-contracts.md]
created: 2026-05-28
updated: 2026-05-28
tags: [deployment, layout, importlib-resources, packaging]
---

# s0 — Deployment Layout Fix-up

## Summary

Bring the `code-review` package, its wheel, and its runtime path resolution into a state where the skill works identically in three layouts:

1. **Developer sibling layout** (current repo): `<repo>/code_review/` next to `<repo>/.claude/skills/code-review/`.
2. **Production nested layout**: `<host>/.claude/skills/code-review/code_review/` (Python package nested inside the skill dir).
3. **Wheel-installed layout**: `code_review/` under `site-packages/`; host's `.claude/skills/code-review/` carries only `SKILL.md` and an optional `code-review.toml`.

The change centres on two seams: package-bundled *data* (`capabilities.json`, `schemas/*.json`) moves to `importlib.resources` loading; operator-tunable *config* (`code-review.toml`) moves to a CWD-relative lookup with a `--config <path>` flag override. The hard-coded `_SKILL_DIR` path arithmetic in `cli.py` is deleted. `pyproject.toml` declares the JSON files as package data so `uv build` produces complete wheels.

## Use case

- **As a** host operator
- **I want to** drop the `code-review` skill into my project under `<host>/.claude/skills/code-review/` (source bundle or wheel)
- **so that** the skill works without needing the dev repo at a path that matches hardcoded assumptions, and without manual file fixups after install.

## Design choices (locked)

- **Package-bundled data** (`capabilities.json`, `schemas/*.json`) → loaded via `importlib.resources.files("code_review")`. Layout-agnostic; survives wheel install.
- **`code-review.toml`** → CWD-relative (`Path.cwd() / "code-review.toml"`) by default; `--config <path>` CLI flag overrides. No skill-dir walk. Matches the ruff / black / pytest idiom.

## Acceptance criteria

### Scenario: package data loads via importlib.resources

- **Given** the runtime needs `capabilities.json` or any of `schemas/*.json`
- **When** the loader runs
- **Then** it reads the file via `importlib.resources.files("code_review")` (not `Path(__file__).parent`), and the load succeeds identically in the dev sibling layout, the nested production layout, and an installed-wheel layout.

### Scenario: wheel includes the bundled JSON files

- **Given** a clean checkout
- **When** `uv build` runs
- **Then** the resulting wheel contains `code_review/capabilities.json` and all four `code_review/schemas/*.json` files
- **And** `pip install dist/code_review-X.Y.Z-py3-none-any.whl` in a fresh venv produces a working install where `python -m code_review.cli --capabilities` runs and matches source-tree output.

### Scenario: `code-review.toml` resolves CWD-relative

- **Given** `./code-review.toml` exists in the caller's CWD
- **When** the CLI is invoked (without `--config`)
- **Then** `load_config` reads that file and the resulting `Config` reflects the overrides.

### Scenario: `--config` flag overrides CWD lookup

- **Given** `--config /some/other/path/code-review.toml`
- **When** the CLI is invoked
- **Then** the named path is read regardless of CWD contents
- **And** if the named path doesn't exist, the CLI exits non-zero with a clear error naming the missing path. Defaults are *not* silently substituted when `--config` is explicit.

### Scenario: no `code-review.toml` anywhere → defaults

- **Given** no `code-review.toml` in CWD and no `--config` flag
- **When** the CLI runs
- **Then** `load_config` returns defaults (current behaviour) without warning or error.

### Scenario: `_SKILL_DIR` is gone

- **Given** the codebase after this story
- **When** `grep -rn '_SKILL_DIR' code_review/` runs
- **Then** the result is empty. The hard-coded path arithmetic `Path(__file__).resolve().parent.parent / ".claude" / "skills" / "code-review"` is removed; nothing in `code_review/` depends on the sibling-layout assumption.

### Scenario: vestigial directories removed

- **Given** the repo after this story
- **When** the file tree under `.claude/skills/code-review/` is inspected
- **Then** the empty `schemas/` and `agents/` directories are deleted; only files actually read at runtime remain (`SKILL.md`, optionally an installed `code-review.toml`).

### Scenario: production-layout smoke test passes

- **Given** a tempdir staged as `<tmp>/.claude/skills/code-review/code_review/{*.py, capabilities.json, schemas/*.json}` plus `<tmp>/code-review.toml` containing a small override (e.g., `dedup_line_tolerance = 5`)
- **When** `python -m code_review.cli --capabilities` and `python -m code_review.cli --review security --target .` run with CWD = `<tmp>`
- **Then** both invocations succeed and the override is honoured in the second.

### Scenario: starter `code-review.toml.example` ships with the skill

- **Given** the skill bundle after this story
- **When** the operator looks inside `<skill_root>/code-review.toml.example`
- **Then** the file exists, every key from the `Config` dataclass is shown commented-out with a one-line purpose and default, and `tomllib.loads` parses the file cleanly.
- **And** `setup.sh`'s final summary prints the absolute path and a one-line `cp` hint pointing at the operator's host project root (or a generic hint if no `.claude/` ancestor resolves).

### Scenario: ADR-0007 resolved

- **Given** the repo after this story
- **When** `adr-0007-package-bundled-contracts.md` is read
- **Then** its status is `accepted` (no longer "deferred"); a "Decision" addendum records: `importlib.resources` for package data; CWD-relative + `--config` for `code-review.toml`; `_SKILL_DIR` removed.
- **And** SKILL.md's Install section names the three supported layouts.

## Test specification

- **`tests/test_package_data_resources.py`** (new) — `importlib.resources.files("code_review")` returns a traversable that resolves `capabilities.json` and each of `schemas/*.json`; their JSON is loadable; the schemas validate as JSON-Schema draft 2020-12.
- **`tests/test_config_lookup.py`** (new) — table-driven over: TOML in CWD found; CWD-only with no TOML → defaults; `--config <existing>` honored; `--config <missing>` errors non-zero with a clear message; `--config` value takes precedence over CWD TOML.
- **`tests/test_production_layout.py`** (new) — full smoke per AC8: stage layout under `tmp_path`, exercise CLI with `--capabilities` and `--review security`, assert TOML override applied.
- **`tests/test_wheel_packaging.py`** (new) — `uv build`; install resulting wheel into isolated venv (via `subprocess.run` and `venv.create`); assert `importlib.resources.files("code_review") / "capabilities.json"` resolves in the installed venv; assert `python -m code_review.cli --capabilities` runs.
- **`tests/test_toml_example_template.py`** (new) — `code-review.toml.example` exists in the skill bundle; `tomllib.loads` parses it; copying it to a `tmp_path` and invoking `load_config(Path(tmp_path))` produces a `Config` with all keys reflecting the example's values.
- **`tests/test_paths.py`** — extend or retire: `SkillPaths` is either wired to `importlib.resources` for any remaining use or deleted if unused. Either way, no regression.
- **Existing tests** — `test_capabilities.py`, `test_capabilities_runtime.py`, `test_skill_scaffold.py`, `test_sandbox_compatibility.py` continue to pass without modification (they don't touch the path arithmetic).

## Out of scope

- Wheel publication to a registry — that's `s1-package-publication`.
- Changing the *contents* of `capabilities.json`, `code-review.toml`, or the schemas — only changing how they're *found* and *bundled*.
- A skill-dir walk for `code-review.toml` — explicitly rejected; CWD-relative + `--config` is the only mechanism.
- Migration tooling for existing installs that have a stale `code-review.toml` somewhere — not needed because no such installs exist (skill is pre-release).
