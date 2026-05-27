# State — last updated 2026-05-27

**Active focus:** s4 (contract testing, Schemathesis-only) — executing. Pact dropped (ADR-0008); Schemathesis as in-process library (ADR-0009).
**Last completed:** s4-t1 — SchemathesisAdapter (library→SARIF), FastAPI drift fixture, env-var auth, cooperative deadline, `$TMPDIR` cache (`a16bd99`); 208 passed / 6 skipped.
**Next:** execute **s4-t2** tests-first (capabilities.json Schemathesis entry, SKILL.md sandbox docs, sandbox-network test, cross-cutting tests).

## s4 shape (Schemathesis-only)
- One adapter: Schemathesis (schema-driven, runs against a live API → SARIF), used as an **in-process library** (ADR-0009), `full` scope, story-level only, 600s timeout via cooperative deadline.
- Tasks: t0 ✅ · t1 ✅ · t2 (capabilities/SKILL.md/sandbox test).

## Open questions / known debt
- `--capabilities` output still has no schema; `analyzers` key shape differs from review-response (deferred from s0/s1).
- `code-review.toml` read from skill dir (`_SKILL_DIR` in cli.py); ADR-0007 defers CWD-relative decision.
- Ruff is part of per-task green-bar; verifier/reviewer sub-agents still don't run it — run locally every task.
- Architecture doc retains Pact prose as historical context (light supersede per ADR-0008); full purge deferred to epic close if wanted.
