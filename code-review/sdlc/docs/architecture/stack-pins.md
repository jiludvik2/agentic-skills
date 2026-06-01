---
id: stack-pins
kind: architecture
project: code-review
sources: [architecture-reviewer-subagent.md]
created: 2026-05-26
updated: 2026-05-29
verified-on: 2026-05-29
tags: [pins, stack, security-floor]
---

# Stack pins — code-review

Canonical, greppable pin list. The architecture (`architecture-reviewer-subagent.md` §10, §11) explains *why* each pin was chosen; this file is the authoritative *what*. Every later pin decision lands here in the same commit as its justifying ADR or architecture edit. No `stack-pins.md` ⇒ no dependency installs.

Status: harvested from the architecture's pin sections at first compile. No project manifest (`pyproject.toml` / `package.json`) exists yet — it gets created during s0/s1 execution and reconciled against this file per SDLC rule #1b.

## Runtime

| Layer | Pin | Note |
|---|---|---|
| Python | `>=3.11` | `requires-python` |
| Package manager | uv (preferred) | `pip install -e .` fallback works (PEP 621); never depend on uv-only `pyproject` features — see adr-0003 |
| Node | **20 LTS + 22 LTS** (matrix) | per **ADR-0017**; for JS/TS analyzers; binaries vendored into `node_modules/`, not fetched at runtime; CI matrix-tests both majors (s1-t3) |
| Build backend | hatchling | — |

## Python dependencies (runtime — spec floor + locked patch)

Per **ADR-0013** (partial supersede of ADR-0003): `pyproject.toml` declares a lower-bound-only spec floor (consumer-resolvable); `uv.lock` pins the exact version tested. Justified upper bounds carry an inline `#` comment.

| Package | Spec floor (`pyproject.toml`) | Locked patch (`uv.lock`) | Role |
|---|---|---|---|
| typer | `>=0.18` | `0.18.0` | CLI |
| jsonschema | `>=4.26` | `4.26.0` | schema validation |
| bandit | `>=1.7` | `1.7.10` | security (adapter-internal import) |
| radon | `>=6.0` | `6.0.1` | complexity metrics |
| vulture | `>=2.13` | `2.13` | dead-code detection |
| pydeps | `>=1.12` | `1.12.20` | coupling metrics |
| cohesion | `>=1.1` | `1.1.0` | LCOM4 cohesion |

## Python dev dependencies (exact pins)

| Package | Version |
|---|---|
| pytest | `8.3.4` |
| pytest-asyncio | `0.25.0` |
| mypy | `1.13.0` |
| ruff | `0.15.14` |

**Known allow-listed advisory:** `pytest 8.3.4` / CVE-2025-71176 (fix 9.0.3). The prior blocker —
schemathesis requiring `pytest>=8,<9` — was removed when schemathesis was dropped (ADR-0021,
2026-05-31), so the `pytest` 9.x bump is now unblocked. Deferred to a separate dev-dep-bump story;
test-only, never shipped at runtime. **Expiry: 2026-08-31** — bump `pytest` then, or re-affirm.

(fastapi/uvicorn were dev-only fixture deps for the Schemathesis adapter; removed with it under
ADR-0021. The starlette transitive-CVE floor they provided is no longer relevant — nothing else
imports them.)

## Subprocess-only tools (runtime prerequisites, NOT Python deps)

semgrep, gitleaks, trivy, eslint (+ sonarjs), dependency-cruiser, jscpd, knip. Installed by `scripts/setup.sh`; presence verified at runtime via `python -m code_review.cli --capabilities`. Invoked as separate processes (license isolation — see floor below). (Pact was listed here but dropped — ADR-0008.)

## Node/JS toolchain (vendored via npm)

Per **ADR-0017**. Manifest pins are major-version floors in `package.json` at the skill root; exact patches are locked in `package-lock.json` (mirroring the Python spec-floor/lock split, ADR-0013). The lockfile — not `capabilities.json` — is the source of truth for installed versions. Supported Node range: **20 LTS + 22 LTS** (see Runtime table). Not shipped in the wheel.

| Package | Manifest pin | Locked patch | Role |
|---|---|---|---|
| eslint | `^9` | `package-lock.json` (s1-t1) | JS/TS linting |
| @microsoft/eslint-formatter-sarif | `^3` | `package-lock.json` (s1-t1) | eslint → SARIF |
| knip | `^5` | `package-lock.json` (s1-t1) | unused-export detection |
| jscpd | `^4` | `package-lock.json` (s1-t1) | copy-paste detection |
| dependency-cruiser | `^16.10.4` | `16.10.4` (s3-t0) | coupling/cycles; 16.0.0 broke on modern Node (F1, seen on Node 24) — `R_OK` SyntaxError up to 16.10.1, fixed in 16.10.2 (`node:fs/constants`). s3-t0 bumped to 16.10.4 (latest 16.x, inside `^16`); empirical floor 16.10.2 |
| typescript | `^5` | `5.9.3` (s3-t1) | depcruiser's TS transpiler — must be in `>=2 <6` for depcruise to enumerate `.ts`/`.tsx` in a directory target; knip pulls `typescript@6` (out of range), so 5.x is vendored top-level so the default `.` full-scan sees TS files (F1) |
| @typescript-eslint/parser | `^8.60.0` | `8.60.0` (story-jscomplexity-ts) | ESLint parser bridge so `jscomplexity` reports cyclomatic complexity for `.ts`/`.tsx` (ADR-0022 TS follow-up). Parser-only (operator decision 2026-06-01) — the `complexity` rule is syntactic, so no type-aware/`tsconfig` setup; peers `eslint@^9` + `typescript@^5` already vendored |

## Tooling config pins

| Tool | Pin |
|---|---|
| ruff | `target-version = py311`, `line-length = 100`, lint select `E,F,I,B,UP,SIM` |
| mypy | `python_version = 3.11`, `strict = true` |
| pytest | `asyncio_mode = auto` |

## License floor

- Skill code: **MIT**.
- Python dependencies: **MIT / Apache-2.0 / BSD only**. No LGPL, GPL, or AGPL in import paths.
- Subprocess-only tools may be GPL/LGPL when invoked as a separate process (Semgrep LGPL-2.1, gitleaks MIT, Trivy Apache-2.0). **No AGPL anywhere**, even via subprocess — TruffleHog rejected on this basis in favour of gitleaks.
- Enforced in CI via `scripts/license_audit.py` against an allow-list.

## Invocation conventions

All project tooling must be invoked via `uv run <tool>`, not via bare `python` or direct tool binaries.

| Do | Don't | Why |
|---|---|---|
| `uv run pytest tests/...` | `python -m pytest tests/...` | pyenv global is 3.13; project venv is 3.12 (uv-managed). Bare `python` hits the wrong interpreter. |
| `uv run pytest tests/... -v` | `rtk proxy python -m pytest ...` | `rtk proxy` bypasses RTK filtering but still uses pyenv's 3.13, which lacks project deps. `uv run pytest -v` already produces full uncompressed output. |
| `uv run ruff check .` | `ruff check .` | Same venv isolation reason. |
| `uv run mypy --strict ...` | `mypy --strict ...` | Same. |

There is no `.python-version` pin because pyenv only has 3.13 installed; the project's 3.12 is fetched and managed exclusively by uv.

## File placement conventions

The system sandbox blocks writes to `.claude/skills/code-review/` (`denyWithinAllow`). Only skill definition files belong there; agents cannot write project artifacts into that tree.

| Artifact type | Correct location | Never here |
|---|---|---|
| JSON schemas (output contracts) | `code_review/schemas/` | `.claude/skills/code-review/schemas/` |
| Test fixtures | `tests/fixtures/` | `.claude/skills/code-review/` |
| Generated output | `code_review/` subtree or `tests/fixtures/` | `.claude/skills/` anywhere |

Attempting `mkdir .claude/skills/code-review/<anything>` will fail with "Operation not permitted" unless `dangerouslyDisableSandbox: true` is set — which should not be a routine workaround.

## Pinning policy

Split per **ADR-0013**:

- **Runtime deps** (`[project.dependencies]`): lower-bound only (`>=X.Y`), anchored at the currently-locked minor. Justified upper bounds permitted with an inline `#` comment stating why (no runtime dep currently carries one — schemathesis, the former example, was removed under ADR-0021). Spec floor = "minimum compatible minor"; `uv.lock` carries the exact patch the project was tested against.
- **Dev deps** (`[dependency-groups] dev`): exact pins (`==X.Y.Z`). Never shipped to consumers; reproducible CI matters more than transitive flexibility. ADR-0003 §1 applies unchanged here.

Version bumps are deliberate, reviewed events — for runtime deps the substantive change is the `uv.lock` bump (with `stack-pins.md` reconciled in the same commit per SDLC rule #1b); for dev deps the change is both spec + lock together. Rationale: **adr-0003** (original governance intent), **adr-0013** (split for PyPI consumers).
