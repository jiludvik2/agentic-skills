# State — last updated 2026-05-27

**Active focus:** epic-reviewer-subagent — **s4 CLOSED**. Next story: **s5 (subagent integration + design review)**, the last story before epic close.
**Last completed:** s4 story close — round-2 review `CLEAN`, all 9 ACs evidenced, supply-chain remediated (fastapi 0.115.12→0.136.3 floors starlette≥1.0.1; pytest CVE allow-listed). 3 fix tasks (s4-fix1/2/3) + story moved to `/sdlc/work/done/`. 213 passed / 6 skipped, ruff + mypy clean.
**Next:** read `sdlc/work/active/s5-subagent-integration-and-design-review.md`, then plan s5 tests-first.

## s4 outcome (Schemathesis-only) — done
- One adapter: Schemathesis, **in-process library** (ADR-0009), `full` scope, story-level only, 600s cooperative deadline. Tasks t0/t1/t2 ✅; story-level review round1 (1 Crit + 2 Imp) → fix1/2/3 → round2 CLEAN.
- AC #1 (the flagship) now genuinely verified: 2xx OpenAPI drift surfaces as `schemathesis.response_schema_violation` naming the divergent field (fix1 registers `response_schema_conformance`; fix2 reworks the fixture to a real 2xx drift + strict assertions).

## Open questions / known debt
- `--capabilities` output still has no schema; `analyzers` key shape differs from review-response (deferred from s0/s1).
- `code-review.toml` read from skill dir (`_SKILL_DIR` in cli.py); ADR-0007 defers CWD-relative decision.
- Ruff is part of per-task green-bar; verifier/reviewer sub-agents still don't run it — run locally every task.
- Architecture doc retains Pact prose as historical context (light supersede per ADR-0008); full purge deferred to epic close if wanted.
- **s4 deferred Minors** (in s4-fix1 notes): #4 adapter multi-target hard-return discards earlier-target findings; #5 orphaned `--review-scope` flag/enum + enum-less `review_scope` capabilities field. Opportunistic cleanup.
- **Supply-chain:** no formal gate defined (rule #26 N/A). pytest 8.3.4 / CVE-2025-71176 allow-listed until 2026-08-31 (blocked by `schemathesis==4.0.10` pinning `pytest<9`); consider an audit-gate ADR + pytest/schemathesis bump in a later story.
- **Housekeeping:** s3-plan.md and s4-plan.md linger in `active/` (plans aren't archived to `done/` per project precedent); s3 story/tasks were never moved to `done/` after s3 completed — pre-existing.
