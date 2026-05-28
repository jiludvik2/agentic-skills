---
id: s1-t0-project-metadata
kind: task
project: code-review
status: done
parent: s1-package-publication
created: 2026-05-28
updated: 2026-05-28
closed: 2026-05-28
verify: PASS (commit 91142af; 299 passed/6 skipped; ruff clean; pre-existing mypy conftest dup noted, out of scope)
review: CLEAN (zero findings at any severity)
---

# s1-t0 — PyPI-ready project metadata in `pyproject.toml`

## Outcome

Fill in `pyproject.toml` with the metadata PyPI needs for a polished package page: distribution name, authors, readme reference, project URLs, classifiers, keywords, console-script entry point. The wheel built after this task has a complete `METADATA` file.

## Acceptance criteria

- `pyproject.toml`'s `[project]` section gains (or already-has-and-keeps):
  - `authors = [{ name = "Jiri Ludvik" }]` (no email — omitted intentionally to avoid publishing a private address on PyPI).
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
- `name = "claude-code-review"` (renamed from `"code-review"` — that name is already taken on PyPI). The Python **import name** stays `code_review` (the package directory is unchanged); the **console-script binary** is renamed in `[project.scripts]` (see below).
- `[project.scripts]` is updated to `claude-code-review = "code_review.cli:app"` (renamed from the previous `code-review = "code_review.cli:app"` entry point — same target, new binary name).
- `version = "0.1.0"` (already present — keep; first release).
- `description` is one short sentence matching the style of the SKILL.md frontmatter.

## Test specification

- **New: `tests/test_pyproject_metadata.py`** — load `pyproject.toml` with `tomllib`; assert each required key is present and non-empty; assert the locked classifiers list is a strict subset of the actual classifiers; assert `requires-python` floor is `>=3.11`; assert `name == "claude-code-review"`; assert `[project.scripts]` contains exactly `{"claude-code-review": "code_review.cli:app"}` (i.e., no stale `code-review` entry remains).
- **Regression**: `tests/test_wheel_packaging.py` (from `s0-t1`) continues to pass — the wheel still builds.

## Notes

- The `authors` email is operator-supplied. If left as placeholder, the task does not close until the operator approves.
- "Author" vs "maintainer" — PyPI treats them differently. For a solo project, `authors` is sufficient; no `maintainers` field needed.
- Email omitted by design — PyPI doesn't require it, and publishing a private address in package metadata is unnecessary for a solo open-source project.
- `description` is short (one sentence); `readme` carries the long description. Don't duplicate.
- `dependencies` is unchanged — already correctly populated.
- Hatchling reads metadata directly from `[project]` — no separate `[tool.hatch.metadata]` block needed.
