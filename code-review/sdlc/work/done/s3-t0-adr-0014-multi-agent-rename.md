---
id: s3-t0-adr-0014-multi-agent-rename
kind: task
project: code-review
status: active
parent: s3-multi-agent-rename
sources: [s3-multi-agent-rename]
status: done
created: 2026-05-29
updated: 2026-05-29
---

# s3-t0 — ADR-0014: multi-agent rename

## Outcome

File ADR-0014 recording the `claude-code-review` → `polyreview` rename and its rationale. No code change. Drafted in `sdlc/work/active/adr-0014-multi-agent-rename.md`; moves to `sdlc/docs/decisions/` at story close (Co-locate active work).

## Acceptance criteria

Satisfies the story scenario **"ADR-0014 documents the multi-agent rename strategy"**. The ADR records:

- The rename `claude-code-review` → `polyreview` and the rationale: multi-agent neutrality (`pip install claude-…` reads as Anthropic-only), Ruff/Semgrep/Bandit naming family, PEP-423 distribution-vs-import asymmetry.
- **Kept unchanged** (and why — each names a capability, not the vendor): Python import name `code_review`; skill bundle path `.claude/skills/code-review/`; skill folder name; monorepo subdirectory `code-review/`.
- **Tag prefix `code-review-v*` kept unchanged** (s3 amendment): names the release stream/capability, same reasoning as the folder name. Recorded explicitly so the asymmetry — package `polyreview` released under `code-review-v*` tags — is on the record rather than an accident.
- The Agent Skills standard finding: `.claude/skills/` is read by Copilot/Cursor/Codex/Gemini-CLI/Goose/~40 agents (open-sourced 2025-12-18), so no skill-side move is needed — the `claude-` distribution-name prefix was the only real coupling.
- The AGENTS.md decision (canonical cross-agent policy file) + CLAUDE.md one-line redirect.
- **Consequence note (s3 amendment):** the binary rename forces `.github/workflows/release.yml` changes — the `test-dist` smoke step (`claude-code-review --capabilities` → `polyreview --capabilities`) and the workflow `name:`. Executed in s3-t1; recorded here so the coupling is documented.
- Deferred follow-up: publish a `claude-code-review` 0.x.y redirect meta-package depending only on `polyreview`, once `polyreview` is first published. Not a task in this story (depends on operator-side off-repo publication).

## Test specification

The ADR is prose; no automated test. Verify = the pre-dispatch self-check confirms every bullet above is present in the drafted ADR; the operator reads and approves the ADR before commit (SDLC "What stays human": ADRs — Claude drafts, operator approves).

## Notes

- ADR content: Claude drafts, operator approves before commit.
