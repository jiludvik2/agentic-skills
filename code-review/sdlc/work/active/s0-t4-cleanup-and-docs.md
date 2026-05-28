---
id: s0-t4-cleanup-and-docs
kind: task
project: code-review
status: done
parent: s0-deployment-layout-fixup
created: 2026-05-28
updated: 2026-05-28
---

# s0-t4 — Cleanup vestigial dirs + resolve ADR-0007 + update SKILL.md

## Outcome

Remove the empty placeholder directories from `.claude/skills/code-review/`, mark ADR-0007 as decided with the actual mechanism recorded, and update SKILL.md's Install section with the three supported deployment layouts.

## Acceptance criteria

- `.claude/skills/code-review/schemas/` is deleted from the repo (was an empty placeholder from the original pre-ADR-0007 sketch; runtime ignores it).
- `.claude/skills/code-review/agents/` is deleted from the repo (was emptied in Phase 3 of s5 when the bundled reviewer.md was removed; nothing reads it).
- `sdlc/docs/decisions/adr-0007-package-bundled-contracts.md` gets a "Decision" addendum documenting:
  - **Package data loading**: `importlib.resources.files("code_review")` for `capabilities.json` and `schemas/*.json`.
  - **Operator config lookup**: `Path.cwd() / "code-review.toml"` by default; `--config <path>` CLI flag overrides.
  - **`_SKILL_DIR` removed** from `cli.py:24`.
  - **ADR status**: changes from whatever "deferred" wording was used to `accepted` (or stays accepted but with the decision text added).
- `.claude/skills/code-review/SKILL.md`'s Install section gains a "Deployment layouts" subsection explaining the three supported shapes:
  1. **Dev sibling layout** (repo-as-skill): `<repo>/code_review/` + `<repo>/.claude/skills/code-review/`. Used when developing the skill.
  2. **Production nested layout**: `<host>/.claude/skills/code-review/code_review/`. Used when copying the skill bundle into a host project.
  3. **Wheel-installed layout**: `code_review/` under `site-packages/` + `<host>/.claude/skills/code-review/` carrying only `SKILL.md` and optional `code-review.toml`. Used when `pip install code-review` lands.
- `setup.sh` step messages reflect the layout-agnostic behaviour (no changes if already correct; verify the existing step 4 reviewer.md check still works in all three layouts).

## Test specification

- **`tests/test_skill_scaffold.py`** — extend or verify: the directory cleanup doesn't break any scaffold assertion. If existing tests reference `.claude/skills/code-review/schemas/` or `agents/`, update them.
- **No new test for the ADR text** — ADRs are prose; verification is a manual read by the operator.
- **No new test for SKILL.md content** — `test_skill_scaffold.py` already checks the required-sections list; if a new section is added ("Deployment layouts"), add it to the required-headers list there.

## Notes

- This task is the bookend of s0 — runs after t0–t3 so that the docs reflect what was actually built.
- Cleanup is git rm; both directories must be empty before removal. Verify with `ls -la` before invoking `git rm -r`.
- The ADR-0007 update is in `/sdlc/docs/decisions/` (it was moved there at Phase 4 of the prior epic). Confirm the path before editing.
- If the SKILL.md scaffold test gains a new required section, the test must be updated in the same commit — the green bar applies.
