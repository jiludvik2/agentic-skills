---
id: s2-t2-importlib-metadata-version-source
kind: task
project: code-review
status: active
parent: s2-packaging-hardening
created: 2026-05-29
updated: 2026-05-29
---

# s2-t2 — Single-source `__version__` via `importlib.metadata`

## Outcome

`code_review/__init__.py` no longer carries a hardcoded version string. The value of `code_review.__version__` is read at import time from the installed package metadata via `importlib.metadata.version("claude-code-review")`. When the package is not installed (e.g., a fresh source checkout before `uv sync`), the import does not raise; instead a documented dev-sentinel `"0.0.0+dev"` is returned.

This eliminates the drift risk between `pyproject.toml`'s `[project] version` and `code_review/__init__.py`'s `__version__` — both are currently `0.1.0`, and the existing `test_package_importable` test would not catch divergence (it only asserts the string type, not the value).

## Acceptance criteria

- `code_review/__init__.py` contains no string literal matching `r"\d+\.\d+\.\d+"`. The version is computed, not hardcoded.
- The implementation imports `version` and `PackageNotFoundError` from `importlib.metadata`, and on `PackageNotFoundError` returns the sentinel `"0.0.0+dev"`.
- In a developer-installed environment (`uv sync --frozen` complete, the local editable installed), `code_review.__version__` equals `importlib.metadata.version("claude-code-review")`.
- In a hypothetical uninstalled environment, the import does not raise — verified by patching `importlib.metadata.version` to raise `PackageNotFoundError` and asserting the sentinel is returned.
- All existing tests continue to pass; `ruff check .` clean; `mypy code_review` clean.
- `test_package_importable` continues to pass — `code_review.__version__` remains a `str`.

## Test specification

- **New: `tests/test_version_source.py`** with three tests:
  1. `test_version_matches_installed_package_metadata` — asserts `code_review.__version__ == importlib.metadata.version("claude-code-review")` in the dev venv (where the package IS installed).
  2. `test_no_hardcoded_version_in_init` — reads the source of `code_review/__init__.py` and asserts no `r"\d+\.\d+\.\d+"` match. Guards against a future "quick fix" that re-introduces a hardcoded string.
  3. `test_fallback_returned_when_metadata_missing` — uses `monkeypatch` to replace `importlib.metadata.version` with one that raises `PackageNotFoundError`, then `importlib.reload(code_review)`, then asserts `code_review.__version__ == "0.0.0+dev"`.
- **Regression**: full pytest green bar; `ruff`; `mypy`. `tests/test_scaffold.py::test_package_importable` continues to pass (the `isinstance(code_review.__version__, str)` assertion is satisfied by both the metadata value and the sentinel).

## Notes

- Distribution name in `importlib.metadata.version("claude-code-review")` is the PyPI name from `pyproject.toml`, not the import name `code_review`. This is the standard pattern.
- `importlib.metadata` is stdlib since Python 3.8; no new dependency.
- The fallback string includes `"+dev"` as a PEP 440 local version segment so it is visibly distinguishable from a real `0.0.0` release. Anyone who sees `0.0.0+dev` knows the package wasn't installed.
- The reload test (test #3) is intentional. Without `importlib.reload`, the module-level `__version__` would already be set from the test's own venv. We need to re-execute the module after patching `version`.
- mypy's `strict = true` will require explicit type annotation on `__version__`. The intended form: `__version__: str = ...`.
