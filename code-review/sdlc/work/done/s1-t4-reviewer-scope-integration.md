---
id: s1-t4-reviewer-scope-integration
kind: task
project: code-review
status: done
parent: s1-reviewer-skill-and-capabilities
created: 2026-05-26
updated: 2026-05-26
notes: |
  Review MINOR-ONLY. Actioned opportunistically: find_host_root relative-path loop guard
  (&& -n "$d"); tests neutralise steps 1-3 (was only step 1) to isolate the install step;
  mkdir exist_ok=True. Noted not-actioned: fails-loud test assumes tmp_path has no .claude
  ancestor (reliably clean). Rejected Nit: reviewer.md "semgrep lands in s3" is wrong —
  the semgrep adapter shipped in s0-t3 and is in REGISTRY. Deferred Nit: exact review_scope
  config path pinned when s5 wires runtime dispatch.
---

# s1-t4 — Reviewer sub-agent scope integration

## Outcome

A scope-aware Reviewer sub-agent source is bundled with the skill and installed into the host
project by `setup.sh`. The agent reads `review_scope` (lite/standard/full) from the SDLC project
config. At `lite` it behaves exactly as before; at `standard`/`full` it invokes the `code-review`
CLI (passing `--review-scope`) before the LLM design-review step. Changing the config value takes
effect on the next dispatch with no other operator action.

## Acceptance Criteria

- A skill-bundled reviewer source exists at `.claude/skills/code-review/agents/reviewer.md`
  (co-located with `SKILL.md`/`capabilities.json`) and documents the three scopes and the dispatch
  rule: `lite` → LLM-only (pre-installation behaviour); `standard`/`full` → run
  `python -m code_review.cli ... --review-scope <scope>` first, then LLM design review consuming the
  consolidated output.
- The scope value is read from the SDLC project config (the location the SDLC skill uses for
  project-level settings); absent/unset config defaults to `lite`.
- The agent instructions are explicit enough that at `lite` no CLI subprocess is spawned, and at
  `standard`/`full` the CLI receives the correct `--review-scope` argument.
- **(absorbed from s1-t3-fix1)** `setup.sh` gains the install step that copies the bundled
  reviewer source into the host project's `.claude/agents/reviewer.md`. Host root is resolved by
  walking up from the skill dir to the nearest ancestor containing `.claude/` (no fixed-depth
  `../../..`); if none is found the step fails loud (non-zero, named). The copy is a plain `cp`
  (byte-identical across runs). The step is guarded on the bundled source existing.

## Test specification

New `tests/test_scope_dispatch.py` — since the reviewer is a markdown agent spec (not executable Python), tests target the parseable contract:

- `test_reviewer_md_documents_three_scopes` — assert the bundled reviewer source contains text for `lite`, `standard`, `full` and the dispatch rule per scope.
- `test_reviewer_md_lite_is_llm_only` — assert the `lite` description states no analyzer CLI is invoked.
- `test_reviewer_md_standard_full_invoke_cli` — assert the `standard` and `full` descriptions reference invoking `code_review.cli` with `--review-scope`.
- `test_cli_accepts_review_scope_values` (in-process) — invoke the CLI with `--review-scope lite|standard|full` (added as passthrough in s1-t2); assert each is accepted; assert an out-of-set value is rejected.
- `test_default_scope_is_lite` — assert the documented default when `review_scope` is unset is `lite`.
- **(absorbed from s1-t3-fix1)** `test_setup_installs_reviewer_into_host` — in a synthetic
  `<tmp>/.claude/skills/code-review/` tree containing `scripts/setup.sh` (steps 1–3 neutralised to
  `true`), `scripts/prefetch_caches.py`, and the bundled `agents/reviewer.md`, run setup.sh; assert
  `<tmp>/.claude/agents/reviewer.md` is created and byte-identical to the source; a second run keeps
  it byte-identical.
- **(absorbed from s1-t3-fix1)** `test_setup_install_fails_loud_without_project_root` — run the
  install path from a dir with no `.claude/` ancestor; assert non-zero exit naming the step.

## Notes / deferrals

- Actual sub-agent runtime invocation of the skill (the agent literally shelling out during a real Review) → s5 integration. This task fixes the agent's documented contract and the CLI flag surface; the end-to-end dispatch is verified when s5 wires the sub-agent in.
- The setup.sh install step was deferred here from s1-t3 (see s1-t3-fix1): t4 owns the bundled
  reviewer source, the host-root resolution, and the copy test together.
