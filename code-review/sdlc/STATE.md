# State — last updated 2026-05-27

**Active focus:** s4 (contract testing, Schemathesis-only) — executing. Pact dropped (ADR-0008); Schemathesis as in-process library (ADR-0009).
**Last completed:** s4-t0 — scope-restriction gate, severity-override wiring, `[contract_testing]` config, fastapi/uvicorn pin (`4d87e6e`); 200 passed / 6 skipped.
**Next:** execute **s4-t1** tests-first (SchemathesisAdapter, FastAPI drift fixture, env-var auth, cooperative deadline, `$TMPDIR` cache). ⚠️ Resolve verify-first unknown #1 (Schemathesis 4.0.10 library API) at top of t1 before writing adapter.

## s4 shape (Schemathesis-only)
- One adapter: Schemathesis (schema-driven, runs against a live API → SARIF), used as an **in-process library** (ADR-0009), `full` scope, story-level only, 600s timeout via cooperative deadline.
- Tasks: t0 ✅ · t1 (adapter + FastAPI fixture + skipif tests) · t2 (capabilities/SKILL.md/sandbox test).

## Open questions / known debt
- `--capabilities` output still has no schema; `analyzers` key shape differs from review-response (deferred from s0/s1).
- `code-review.toml` read from skill dir (`_SKILL_DIR` in cli.py); ADR-0007 defers CWD-relative decision.
- Ruff is part of per-task green-bar; verifier/reviewer sub-agents still don't run it — run locally every task.
- Architecture doc retains Pact prose as historical context (light supersede per ADR-0008); full purge deferred to epic close if wanted.
