---
id: stack-pins
kind: architecture
project: code-review
sources: [architecture-reviewer-subagent.md]
created: 2026-05-26
updated: 2026-05-26
verified-on: 2026-05-26
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
| Node | via `npm ci` | for JS/TS analyzers; binaries vendored into `node_modules/`, not fetched at runtime |
| Build backend | hatchling | — |

## Python dependencies (exact pins)

| Package | Version | Role |
|---|---|---|
| typer | `0.18.0` | CLI |
| jsonschema | `4.26.0` | schema validation |
| bandit | `1.7.10` | security (adapter-internal import) |
| radon | `6.0.1` | complexity metrics |
| vulture | `2.13` | dead-code detection |
| pydeps | `1.12.20` | coupling metrics |
| cohesion | `1.1.0` | LCOM4 cohesion |
| schemathesis | `4.0.10` | contract testing (full scope) |

## Python dev dependencies (exact pins)

| Package | Version |
|---|---|
| pytest | `8.3.4` |
| pytest-asyncio | `0.25.0` |
| mypy | `1.13.0` |
| ruff | `0.15.14` |

## Subprocess-only tools (runtime prerequisites, NOT Python deps)

semgrep, gitleaks, trivy, eslint (+ sonarjs), dependency-cruiser, jscpd, knip. Installed by `scripts/setup.sh`; presence verified at runtime via `python -m code_review.cli --capabilities`. Invoked as separate processes (license isolation — see floor below). (Pact was listed here but dropped — ADR-0008.)

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

Exact pins (`==`). Version bumps are deliberate, reviewed events, not incidental. Rationale and governance context: **adr-0003**.
