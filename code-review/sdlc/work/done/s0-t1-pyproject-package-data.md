---
id: s0-t1-pyproject-package-data
kind: task
project: code-review
status: done
parent: s0-deployment-layout-fixup
created: 2026-05-28
updated: 2026-05-28
---

# s0-t1 — Declare bundled JSON files as package data

## Outcome

`uv build` produces a wheel containing `code_review/capabilities.json` and all four `code_review/schemas/*.json` files, so a wheel-installed package has the same on-disk content as a source-tree checkout.

## Acceptance criteria

- `pyproject.toml` declares the JSON files as package data via hatchling's mechanism (`[tool.hatch.build.targets.wheel]` with `force-include` or `packages` glob — pick the idiomatic one for hatchling).
- `uv build` produces a wheel under `dist/`.
- `unzip -l dist/code_review-X.Y.Z-py3-none-any.whl` shows `code_review/capabilities.json` and every `code_review/schemas/*.json` file.
- `pip install dist/code_review-X.Y.Z-py3-none-any.whl` in a fresh venv installs the package with the JSON files intact, and `importlib.resources.files("code_review") / "capabilities.json"` resolves in that venv.

## Test specification

- **New: `tests/test_wheel_packaging.py`** — single test that:
  1. Runs `uv build` (or `python -m build`) in a tmpdir copy of the project (or against the current tree, depending on isolation needs).
  2. Locates the produced wheel.
  3. Opens the wheel as a zip archive (it is one) and asserts the presence of `code_review/capabilities.json` and the four schema files.
  4. Creates a fresh venv via `venv.create`.
  5. `pip install`s the wheel into that venv via `subprocess.run`.
  6. Runs `<venv>/bin/python -m code_review.cli --capabilities` and asserts the output is valid JSON.
- The test is allowed to take 30–60 seconds (build + install + run); mark it slow if pytest's defaults flag it, but don't skip by default.
- May require `uv build`'s network access for the build backend on first run — verify it works inside the sandbox; if not, the test relies on `setup.sh` having pre-populated the venv (acceptable per project precedent).

## Notes

- Depends on `s0-t0` landing first so that the wheel-installed package can actually find the JSON files via `importlib.resources`.
- The `[project.scripts]` entry (`code-review = "code_review.cli:app"`) is already declared and out of scope for this task — verified end-to-end in `s1-t4-install-smoke-test`.
- Hatchling auto-discovers `code_review/` as the package. The JSON files need explicit inclusion because hatchling defaults to source files only.

## Notes (post-review, MINOR-ONLY findings for opportunistic cleanup)

- `tests/test_wheel_packaging.py` — both tests independently call `uv build`, paying the build cost twice (~15-30s). Could be hoisted into a module-scoped `@pytest.fixture` returning the wheel path.
- `tests/test_wheel_packaging.py:29-34, 53-58, 63-66, 70-74` — `subprocess.run(..., check=True, capture_output=True)` swallows stdout/stderr on success and truncates on `CalledProcessError`. Drop `capture_output=True` on the three `check=True` calls (the fourth at line 76 correctly omits `check=True` to assert on `returncode`).
- `tests/test_wheel_packaging.py:42-45` — `assert any(n == expected for n in names)` is more verbose than the idiomatic `assert expected in names` since `names: list[str]`.
