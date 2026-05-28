---
id: s1-t1-readme-draft
kind: task
project: code-review
status: active
parent: s1-package-publication
created: 2026-05-28
updated: 2026-05-28
---

# s1-t1 — Draft `README.md` at repo root

## Outcome

Repo root has a `README.md` suitable for both GitHub's repo landing page and PyPI's package description. Claude drafts; operator approves content (per "What stays human") before commit.

## Acceptance criteria

- `code-review/README.md` (the project lives at `agentic-skills/code-review/`; README sits inside the project subdir) exists with sections:
  - **Title + one-line tagline** — what the skill is in 10 words.
  - **Status** — alpha, 0.x.y, no API stability guarantees pre-1.0.
  - **Install** — three command examples (PyPI distribution is `claude-code-review`; the bare `code-review` is taken):
    - `pip install claude-code-review`
    - `pipx install claude-code-review`
    - `uv tool install claude-code-review`
  - **Quick start** — one 5-line example invocation showing `claude-code-review --review … --depth … --diff …` and what comes back. The console-script binary is `claude-code-review`; the Python import name is `code_review` (so `python -m code_review.cli …` also works from a source checkout).
  - **What it does** — three short bullets: deterministic analyzer layer; SARIF + sdlc_severity output; runs under `/sandbox`.
  - **What it doesn't do** — LLM-based review (that's the sibling `intent-review` project), cross-skill aggregation, CI orchestration.
  - **Full reference** — link to `.claude/skills/code-review/SKILL.md` for the complete taxonomy, resolution rules, and configuration details.
  - **Development** — `git clone … && cd code-review && ./scripts/setup.sh && uv run pytest`.
  - **License** — MIT.
- README is GitHub-flavoured markdown; renders cleanly in both GitHub's view and PyPI's markdown renderer (CommonMark with extensions — keep code fences fenced).
- **Operator-approved content per "What stays human"**: Claude drafts and shows to operator; operator edits or signs off before this task closes.

## Test specification

- **No automated test for content quality** — operator approval gates closure.
- **`tests/test_skill_scaffold.py`** — extend to assert `README.md` exists at the project root (the skill's repo root, i.e. `agentic-skills/code-review/`). The path the test uses for `REPO_ROOT` is already correct; just add an `assert README_MD.exists()` check.
- **`tests/test_pyproject_metadata.py`** (from `s1-t0`) — assert the file referenced by `readme = "README.md"` in `pyproject.toml` exists and is non-empty.

## Notes

- Path: `agentic-skills/code-review/README.md` (project root, not monorepo root). The monorepo may have its own top-level README; that's separate and out of scope.
- Long-description rendering for PyPI: hatchling reads `readme = "README.md"` and includes the file content in the wheel's `METADATA`. PyPI renders it. Test with `twine check dist/*` or equivalent before tagging — covered in the release runbook (`s1-t5`).
- The "Quick start" example should use a realistic invocation, not a toy one. `claude-code-review --review security --diff HEAD~1..HEAD --output review.json` (post-install) or `python -m code_review.cli --review security --diff HEAD~1..HEAD --output review.json` (from a source checkout) is the canonical shape.
- Keep README short (under 200 lines). The deep reference lives in SKILL.md; README is the front door.
- Drafting flow: Claude writes initial draft, posts in chat, operator reads + edits, Claude applies edits, task closes only after operator says "looks good" or pushes their own edit.
