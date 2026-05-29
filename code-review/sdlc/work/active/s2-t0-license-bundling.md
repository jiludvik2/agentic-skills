---
id: s2-t0-license-bundling
kind: task
project: code-review
status: active
parent: s2-packaging-hardening
created: 2026-05-29
updated: 2026-05-29
---

# s2-t0 — Bundle LICENSE in the wheel

## Outcome

The built wheel contains a `LICENSE` file in its `dist-info/` metadata, satisfying PEP 639 and the de-facto expectation that PyPI-distributed packages ship their license text alongside the metadata claim. Achieved by physically duplicating the agentic-skills root `LICENSE` into `code-review/LICENSE` and changing `pyproject.toml` to a file-based license declaration.

## Acceptance criteria

- `code-review/LICENSE` exists and is byte-identical to `agentic-skills/LICENSE`.
- `pyproject.toml`'s `[project] license` is `{ file = "LICENSE" }`, replacing the prior `{ text = "MIT" }` form.
- The built wheel contains a `LICENSE` file at some path inside the `*.dist-info/` directory (PEP 639's `licenses/LICENSE` or the Hatchling-default top-level `dist-info/LICENSE` — test asserts containment, not exact sub-path).
- All existing tests continue to pass; `ruff check .` clean; `mypy code_review` no new errors.

## Test specification

- **`tests/test_pyproject_metadata.py`** (extend) — assert `_project()["license"] == {"file": "LICENSE"}`.
- **`tests/test_pyproject_metadata.py`** (extend, separate test) — assert `(REPO_ROOT / "LICENSE").exists()` and `(REPO_ROOT / "LICENSE").read_bytes() == (REPO_ROOT.parent / "LICENSE").read_bytes()`.
- **`tests/test_wheel_packaging.py`** (extend) — new `@pytest.mark.slow` test that builds the wheel and asserts at least one entry in the zip namelist matches the pattern `*.dist-info/*LICENSE*`.

## Notes

- Hatchling reads `license = { file = "LICENSE" }` and copies the file into the wheel's dist-info. No separate `[tool.hatch.build.targets.wheel]` entry is needed.
- The license value in classifiers (`"License :: OSI Approved :: MIT License"`) stays unchanged — it's a separate field from the file reference.
- We deliberately duplicate (not symlink) the file so it travels with the wheel even when the surrounding monorepo isn't present.
