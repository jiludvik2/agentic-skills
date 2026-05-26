---
id: s1-t4-reviewer-scope-integration
kind: task
project: code-review
status: active
parent: s1-reviewer-skill-and-capabilities
created: 2026-05-26
updated: 2026-05-26
---

# s1-t4 — Reviewer sub-agent scope integration

## Outcome

`.claude/agents/reviewer.md` becomes scope-aware: it reads `review_scope` (lite/standard/full) from the SDLC project config. At `lite` it behaves exactly as before; at `standard`/`full` it invokes the `code-review` CLI (passing `--review-scope`) before the LLM design-review step. Changing the config value takes effect on the next dispatch with no other operator action.

## Acceptance Criteria

- `.claude/agents/reviewer.md` documents the three scopes and the dispatch rule: `lite` → LLM-only (pre-installation behaviour); `standard`/`full` → run `python -m code_review.cli ... --review-scope <scope>` first, then LLM design review consuming the consolidated output.
- The scope value is read from the SDLC project config (the location the SDLC skill uses for project-level settings); absent/unset config defaults to `lite`.
- The agent instructions are explicit enough that at `lite` no CLI subprocess is spawned, and at `standard`/`full` the CLI receives the correct `--review-scope` argument.

## Test specification

New `tests/test_scope_dispatch.py` — since the reviewer is a markdown agent spec (not executable Python), tests target the parseable contract:

- `test_reviewer_md_documents_three_scopes` — assert `.claude/agents/reviewer.md` contains sections/text for `lite`, `standard`, `full` and the dispatch rule per scope.
- `test_reviewer_md_lite_is_llm_only` — assert the `lite` description states no analyzer CLI is invoked.
- `test_reviewer_md_standard_full_invoke_cli` — assert the `standard` and `full` descriptions reference invoking `code_review.cli` with `--review-scope`.
- `test_cli_accepts_review_scope_values` (in-process) — invoke the CLI with `--review-scope lite|standard|full` (added as passthrough in s1-t2); assert each is accepted (no "invalid value" error); assert an out-of-set value is rejected.
- `test_default_scope_is_lite` — assert the documented/coded default when `review_scope` is unset is `lite`.

## Notes / deferrals

- Actual sub-agent runtime invocation of the skill (the agent literally shelling out during a real Review) → s5 integration. This task fixes the agent's documented contract and the CLI flag surface; the end-to-end dispatch is verified when s5 wires the sub-agent in.
- `setup.sh` copying the updated reviewer.md into a host project is covered by s1-t3; this task owns the reviewer.md content itself.
