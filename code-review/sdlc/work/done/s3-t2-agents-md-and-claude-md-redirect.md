---
id: s3-t2-agents-md-and-claude-md-redirect
kind: task
project: code-review
status: active
parent: s3-multi-agent-rename
sources: [s3-multi-agent-rename]
status: done
created: 2026-05-29
updated: 2026-05-29
notes: |
  Verify PASS; Review MINOR-ONLY. One Minor (AGENTS.md linked the not-yet-filed
  decisions/ path for ADR-0014 — transiently dead until story close) resolved
  in-task by referencing ADR-0014 by id + the decisions/ dir instead of a fragile
  full path. Two Nits dropped (uv-run vs bare python-m note; sanctioned SDLC
  pointer in CLAUDE.md). CLAUDE.md hard-stop edit explicitly operator-approved
  in-turn.
---

# s3-t2 — AGENTS.md + CLAUDE.md redirect

## Outcome

Author `AGENTS.md` at the repo root (`code-review/AGENTS.md`) as the canonical cross-agent policy file; shrink the project `CLAUDE.md` to a one-line redirect. No policy content duplicated between the two.

## Acceptance criteria

Satisfies story scenarios **"AGENTS.md exists and is canonical"** and **"CLAUDE.md becomes a redirect"**:

- `AGENTS.md` follows the [agents.md](https://agents.md/) format: H1 title, short summary, sections for commands / conventions / sub-projects. It carries the canonical cross-agent policy and links to:
  - `sdlc/SDLC.md` (the SDLC verb cycle)
  - `.claude/skills/code-review/SKILL.md` (the skill bundle, read by all agents)
  - `sdlc/docs/architecture/stack-pins.md` (pinning policy + invocation conventions per ADR-0003/ADR-0013)
- `CLAUDE.md` (project root, `code-review/CLAUDE.md`): ≤5 lines, contains the string `AGENTS.md` (the redirect target); may keep a single SDLC pointer line for the v6.6 bootstrap. No policy content duplicated from AGENTS.md.

## Test specification

- **New `tests/test_agents_md_exists.py`** — assert `AGENTS.md` exists at the repo root, contains a top-level `# ` heading, and references both `sdlc/SDLC.md` and `.claude/skills/code-review/SKILL.md`.
- **New `tests/test_claude_md_is_redirect.py`** — assert `CLAUDE.md` is ≤5 lines and contains `AGENTS.md`. Catches drift back toward duplicated policy.
- Regression: full suite green; `uv run ruff check .` + `uv run mypy` clean.

## Notes

- **Hard-stop:** editing `CLAUDE.md` governs harness behaviour and requires an explicit operator directive in the current turn (SDLC hard-stop list). "run s3" + the operator-approved design decision #2 (AGENTS.md + CLAUDE.md redirect, per STATE.md) cover it — reconfirm before the CLAUDE.md write if any doubt.
- AGENTS.md + CLAUDE.md content: Claude drafts, operator approves before commit.
- `tests/test_agents_md_exists.py` resolves "repo root" as the `code-review/` package root, consistent with the existing `test_pyproject_metadata.py` REPO_ROOT convention.
