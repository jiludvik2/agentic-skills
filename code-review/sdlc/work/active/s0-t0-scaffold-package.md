---
id: s0-t0-scaffold-package
kind: task
project: code-review
status: active
parent: s0-analyzer-facade-and-two-adapters
created: 2026-05-26
updated: 2026-05-26
---

# s0-t0 — Scaffold package structure

## Outcome

`pyproject.toml` (PEP 621, exact pins, hatchling backend, MIT) exists and `uv sync` completes; `import code_review` succeeds; `schemas/sarif-2.1.0.json` is present offline; `runs/`, `cache/`, and `node_modules/` are gitignored.

## Acceptance Criteria

- `pyproject.toml` declares `name = "code-review"`, `requires-python = ">=3.11"`, build-backend `hatchling`, all runtime and dev dependencies from `stack-pins.md` as exact `==` pins, `[project.scripts] code-review = "code_review.cli:app"`, and tool config sections for `ruff` (`target-version = "py311"`, `line-length = 100`, `select = ["E","F","I","B","UP","SIM"]`), `mypy` (`python_version = "3.11"`, `strict = true`), and `pytest` (`asyncio_mode = "auto"`).
- `uv sync` runs without error; `.venv/` is created.
- `python -c "import code_review"` exits 0.
- `schemas/sarif-2.1.0.json` exists at `<skill_root>/schemas/sarif-2.1.0.json` and is valid JSON (the SARIF 2.1.0 official schema, checked in for offline use — fetch once via setup, commit the file).
- `runs/`, `cache/`, `node_modules/`, `.venv/` appear in the project `.gitignore`.
- No `__init__.py` contains business logic; `code_review/__init__.py` exports only `__version__`.

## Test specification

`tests/test_scaffold.py` — written before any files are created; all four fail initially then pass after scaffold:

- `test_package_importable` — `import code_review` succeeds and `code_review.__version__` is a string.
- `test_pyproject_valid` — load `pyproject.toml` with `tomllib`; assert `project["name"] == "code-review"`, `"code_review.cli:app"` is the declared script entry point, `requires-python` starts with `">=3.11"`, `build-system.build-backend == "hatchling.build"`.
- `test_sarif_schema_present_and_valid` — assert `schemas/sarif-2.1.0.json` exists relative to the repo root; load with `json.load`; assert `"$schema"` key is present (or `"title"` — accept the real SARIF schema envelope).
- `test_gitignore_covers_transient_dirs` — read the nearest `.gitignore`; assert `runs/`, `cache/`, `node_modules/`, `.venv/` all appear (exact lines or pattern match).
