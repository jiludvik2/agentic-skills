---
id: s2-t1-relax-runtime-dependency-pins
kind: task
project: code-review
status: done
parent: s2-packaging-hardening
created: 2026-05-29
updated: 2026-05-29
closed: 2026-05-29
verify: PASS round-1 on 24550b2; PASS round-2 on 1d2249f (301 passed + 6 skipped + 8 deselected; ruff clean; mypy clean; uv.lock [[package]] blocks unchanged)
review: round-1 on 24550b2 — 1 Critical (ADR-0003 contradiction) + 1 Important (unbounded schemathesis) + 2 Minor + 1 Nit; operator chose ADR-supersede path. round-2 on 1d2249f — MINOR-ONLY: 1 Minor (stale "runtime pin" phrasing in stack-pins.md security-floor allow-list) + 1 Nit (test_runtime_dependency_set_is_exactly awkward name). Both resolved in this close commit. ADR-0013 filed in /sdlc/work/active/ per ADR-0012 precedent; will move to /sdlc/docs/decisions/ at story close.
---

# s2-t1 — Relax runtime dependency pins

## Outcome

Every entry in `[project.dependencies]` switches from exact `==X.Y.Z` to a `>=X.Y` lower bound anchored at the currently-pinned minor. Consumers installing via `pip install claude-code-review` into a pre-existing environment can resolve transitive dependencies. Developer reproducibility is unchanged because `uv.lock` continues to pin exact versions, and `uv sync --frozen` enforces the lockfile.

The lower bound is set at the **currently-locked minor** — "minimum compatible minor", with `uv.lock` carrying the exact patch the project was actually tested against. This matches the PyPA guidance of "lower bound at the minimum supported minor; add upper bounds only when there's evidence of a specific incompatibility". Patches roll forward; we don't want to flag bandit 1.7.11 as out-of-range.

ADR-0013 (filed in this same task's remediation pass) formalises this as a split policy: runtime deps lower-bounded for consumer resolution; dev deps stay exact-pinned for reproducible CI; ADR-0003's governance intent ("version bumps are deliberate, reviewed events") attaches to `uv.lock` + `stack-pins.md` for runtime, and to spec + lock together for dev.

## Acceptance criteria

- Every line in `[project.dependencies]` (eight entries today) uses `>=X.Y` (not `==`, not `>=X.Y.Z`, not `~=`).
- No upper bound on any dependency (no `<X` or `,<X`). If a future task adds one, it must carry an inline `#` comment explaining the specific incompatibility.
- The exact minor anchors:
  - `typer>=0.18`
  - `jsonschema>=4.26`
  - `bandit>=1.7`
  - `radon>=6.0`
  - `vulture>=2.13`
  - `pydeps>=1.12`
  - `cohesion>=1.1`
  - `schemathesis>=4.0,<5  # 3→4 was a breaking-change major; re-evaluate before allowing 5.x` (the one justified upper bound, per ADR-0013)
- `uv sync --frozen` still installs exactly the locked versions in the developer venv (no change to runtime behaviour).
- The full test suite continues to pass; `ruff check .` clean; `mypy code_review` clean.
- The wheel METADATA carries the same `>=` specifiers (verified by the existing `test_pyproject_metadata.py` extension).

## Test specification

- **`tests/test_pyproject_metadata.py`** (extend) — `test_dependencies_use_lower_bound_only`: parse each entry in `[project.dependencies]`, assert it contains `>=` and does not contain `==`, `~=`, or `<`. Allow inline `#` comments for upper bounds that justify themselves (none today).
- **`tests/test_pyproject_metadata.py`** (extend) — `test_dependency_anchors_match_locked_minors`: hard-code the eight expected `name>=X.Y` strings and assert each appears as a dependency entry. Catches accidental drift to a lower minor or to a patch-level anchor.
- **Regression**: full pytest green bar; `ruff`; `mypy`. The lockfile is not modified by this task; `uv sync --frozen` continues to succeed.

## Notes

- Lockfile is unchanged because the lockfile pins exact versions independent of the spec bounds. `uv lock` would regenerate the same lockfile from the relaxed spec.
- The cohesion package's current pinned minor is `1.1` (lockfile shows `1.1.0`). Verify against `uv.lock` if any value is uncertain; the anchors above came from the current `==X.Y.Z` values in `pyproject.toml`.
- No dependency uses an environment marker today — none of the entries need `python_version`-conditional specifiers.
- `[dependency-groups] dev` is intentionally NOT touched. Dev tooling stays exact-pinned because reproducible CI matters more than transitive flexibility there.
