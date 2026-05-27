# State — last updated 2026-05-27

**Active focus:** s4 (contract testing, Schemathesis-only) — **story close**. All tasks complete.
**Last completed:** s4-t2 — Schemathesis entry in capabilities.json (kind=contract, scope_restriction=story-level, review_scope=full, 600s), SKILL.md contract-testing sandbox subsection, sandbox-network test; 210 passed / 6 skipped.
**Next:** **s4 story close** — story-level Review on cumulative s4 diff, supply-chain gate (pip-audit), AC sweep, then move story to `/sdlc/work/done/`.

## s4 shape (Schemathesis-only)
- One adapter: Schemathesis (schema-driven, runs against a live API → SARIF), used as an **in-process library** (ADR-0009), `full` scope, story-level only, 600s timeout via cooperative deadline.
- Tasks: t0 ✅ · t1 ✅ · t2 ✅.

## Open questions / known debt
- `--capabilities` output still has no schema; `analyzers` key shape differs from review-response (deferred from s0/s1).
- `code-review.toml` read from skill dir (`_SKILL_DIR` in cli.py); ADR-0007 defers CWD-relative decision.
- Ruff is part of per-task green-bar; verifier/reviewer sub-agents still don't run it — run locally every task.
- Architecture doc retains Pact prose as historical context (light supersede per ADR-0008); full purge deferred to epic close if wanted.
