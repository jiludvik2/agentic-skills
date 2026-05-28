---
id: s1-t0-project-metadata
kind: task
project: code-review
status: active
parent: s1-package-publication
created: 2026-05-28
updated: 2026-05-28
---

# s1-t0 — PyPI-ready project metadata in `pyproject.toml`

## Outcome

Fill in `pyproject.toml` with the metadata PyPI needs for a polished package page: authors, readme reference, project URLs, classifiers, keywords. The wheel built after this task has a complete `METADATA` file.

## Acceptance criteria

- `pyproject.toml`'s `[project]` section gains (or already-has-and-keeps):
  - `authors = [{ name = "Jiri Ludvik", email = "<email>" }]` (operator provides the address; placeholder OK at task start, operator approves before commit per "What stays human").
  - `readme = "README.md"` (file itself drafted in `s1-t1`).
  - `urls = { Homepage = "https://github.com/jiludvik2/agentic-skills/tree/main/code-review", Source = "https://github.com/jiludvik2/agentic-skills", Issues = "https://github.com/jiludvik2/agentic-skills/issues" }`.
  - `classifiers = [ ... ]` with at minimum:
    - `"License :: OSI Approved :: MIT License"`
    - `"Programming Language :: Python :: 3"`
    - `"Programming Language :: Python :: 3.11"`
    - `"Programming Language :: Python :: 3.12"`
    - `"Operating System :: OS Independent"`
    - `"Topic :: Software Development :: Quality Assurance"`
    - `"Topic :: Software Development :: Testing"`
    - `"Intended Audience :: Developers"`
    - `"Development Status :: 3 - Alpha"`
  - `keywords = ["code-review", "sarif", "static-analysis", "semgrep", "bandit", "sdlc", "deterministic-analyzer"]`.
- `requires-python = ">=3.11"` (already present — verify, don't remove).
- `name = "code-review"` (already present — verify; if PyPI name conflict surfaces during `s1` execution, see Open Questions in the parent story for the rename procedure).
- `version = "0.1.0"` (already present — keep; first release).
- `description` is one short sentence matching the style of the SKILL.md frontmatter.

## Test specification

- **New: `tests/test_pyproject_metadata.py`** — load `pyproject.toml` with `tomllib`; assert each required key is present and non-empty; assert the locked classifiers list is a strict subset of the actual classifiers; assert `requires-python` floor is `>=3.11`; assert `name` matches the published name.
- **Regression**: `tests/test_wheel_packaging.py` (from `s0-t1`) continues to pass — the wheel still builds.

## Notes

- The `authors` email is operator-supplied. If left as placeholder, the task does not close until the operator approves.
- "Author" vs "maintainer" — PyPI treats them differently. For a solo project, `authors` is sufficient; no `maintainers` field needed.
- `description` is short (one sentence); `readme` carries the long description. Don't duplicate.
- `dependencies` is unchanged — already correctly populated.
- Hatchling reads metadata directly from `[project]` — no separate `[tool.hatch.metadata]` block needed.
