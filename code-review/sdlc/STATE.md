# State — last updated 2026-05-27

**Active focus:** s4 (contract testing) — **scope reduced to Schemathesis-only**; Pact dropped (ADR-0008). Story spec updated and ready to Plan.
**Last completed:** s3 closed + cleanup commit `842c123` (tempfile temp-dirs for gitleaks/semgrep/trivy, schema de-duplication). All three s3 milestones (t0–t11) done; 191 passed / 6 skipped.
**Next:** `s4-plan.md` written (t0/t1/t2) — **awaiting operator review**, then execute s4-t0 tests-first.

## s4 shape (Schemathesis-only)
- One adapter: Schemathesis (schema-driven, runs against a live API → JUnit XML → SARIF), `full` scope, story-level only, 600s timeout.
- Proposed tasks: t0 infra (scope-restriction gate, timeout budgets, `[contract_testing]` config, severity→critical default + override wiring, FastAPI test-dep pin) · t1 adapter + FastAPI fixture + skipif tests · t2 SKILL.md sandbox docs + capabilities scope assignment + cross-cutting tests.

## Open questions / known debt
- `severity_overrides` parsed in `config.py` but not wired into `map_severity()`/aggregator — **now needed by s4** (contract findings default `critical` unless overridden); wire in s4-t0.
- `fastapi` not yet pinned — add as a **test-fixture-only** pin in s4-t0 (+ stack-pins).
- `--capabilities` output still has no schema; `analyzers` key shape differs from review-response (deferred from s0/s1).
- `code-review.toml` read from skill dir (`_SKILL_DIR` in cli.py); ADR-0007 defers CWD-relative decision.
- Ruff is part of per-task green-bar; verifier/reviewer sub-agents still don't run it — run locally every task.
- Architecture doc retains Pact prose as historical context (light supersede per ADR-0008); full purge deferred to epic close if wanted.
