# code-review (`polyreview`)

Deterministic code-review skill: runs Semgrep, Radon, Bandit and friends across a diff and emits consolidated SARIF + per-finding `sdlc_severity`. Published to PyPI as **`polyreview`**; the Python import name is `code_review`. The skill bundle is consumed cross-agent (Copilot, Cursor, Codex, Claude, …) via the Agent Skills standard.

This file is the canonical cross-agent policy. It is read-in-spirit by any agent working in this repo; Claude Code reads `CLAUDE.md`, which redirects here.

## Commands

The project venv is uv-managed (Python 3.12; runtime floor 3.11). **Always run tooling through `uv run`** — never bare `python -m …`.

- Install / bootstrap binaries: `./scripts/setup.sh`
- Tests: `uv run pytest`
- Lint: `uv run ruff check .`
- Types: `uv run mypy --config-file pyproject.toml code_review/`
- Run the CLI from a source checkout: `python -m code_review.cli --capabilities` (fallback; the installed binary is `polyreview`)

## Conventions

- **Workflow:** this repo follows an AI-native, spec-anchored SDLC. The filesystem is the source of truth; there is no external tracker. Read [`sdlc/SDLC.md`](sdlc/SDLC.md) before doing development work — it defines the verb cycle (capture → compile → plan → execute → verify → review → file), the autonomy gate, and the hard rules.
- **Tests first.** No implementation before a failing test derived from an accepted task's acceptance criteria.
- **Pins are source of truth.** Runtime/dev/tool versions live in [`sdlc/docs/architecture/stack-pins.md`](sdlc/docs/architecture/stack-pins.md) (see ADR-0003/ADR-0013 for the pinning policy and invocation conventions). No dependency installs without a pin.
- **Verify + Review are non-negotiable** at every task close (fresh-context sub-agents in `.claude/agents/`).

## Layout / sub-projects

- `code_review/` — the Python package (analyzers, CLI, contracts, bundled schemas + `capabilities.json`).
- [`.claude/skills/code-review/SKILL.md`](.claude/skills/code-review/SKILL.md) — the Agent Skill bundle: review-set taxonomy, CLI resolution rules, invocation contract. Read by all major agents.
- `sdlc/` — the SDLC working area: `work/` (active/done artefacts), `docs/` (architecture, decisions/ADRs, runbooks, strategy), `STATE.md` (cross-session bridge), `SDLC.md` (the process).
- `tests/` — pytest suite (structural + integration; some adapter tests require external binaries and skip when absent).

This `code-review/` directory is one subproject of the `agentic-skills` monorepo; release tags use the `code-review-v*` prefix (the package name and the tag prefix differ by design — see ADR-0014, filed under `sdlc/docs/decisions/`).
