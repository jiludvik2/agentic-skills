# State — last updated 2026-05-28

**Active focus:** `epic-reviewer-subagent` closed. No active epic; operator decides what's next.
**Last completed:** s5 Phase 4 — epic close + reconcile. Rewrote epic to deterministic-only framing (preserving original hypothesis as historical record); added supersede banners to architecture (§5, §8, §17.5/17.6 retired per ADR-0010 / ADR-0011; load-bearing sections — Analyzer Protocol, SARIF, sandbox, severity, dedup — unchanged); moved 11 ADRs → `/sdlc/docs/decisions/`, architecture → `/sdlc/docs/architecture/`, epic + s3 + s5 → `/sdlc/work/done/`.
**Next:** operator decision — see Open questions.

## Open questions

- **Rule #17 — `README.md` at repo root.** Epic closed without one (README content is operator-approved per "What stays human"). The bundled `.claude/skills/code-review/SKILL.md` covers the analyzer interface; a project-root README hasn't been drafted. Worth a follow-up.
- **Rule #18 — publication state.** `git remote -v` is configured (per ADR-0001: `github.com/jiludvik2/agentic-skills`). Local commits are ahead of `origin/main`; needs `git push` to satisfy `git log @{u}..HEAD` empty. Operator-runs-push per repo policy.
- **Lingering plans in `active/`.** `s3-plan.md` and `s4-plan.md` remain — project precedent is plans aren't archived, but they're orphans now. Sweep or leave.
- **`intent-review` sibling project.** Requirements captured at `/sdlc/docs/strategy/intent-review-requirements.md`; bootstrap is a separate session.
- **Supply-chain gate.** Rule #26 N/A. `pytest==8.3.4` / CVE-2025-71176 allow-listed until 2026-08-31 (blocked by `schemathesis==4.0.10`); a future ADR could formalise an audit gate + pytest/schemathesis bump.
- **s4 deferred Minor #4** (adapter multi-target hard-return) still open from s4 review; not blocking.
