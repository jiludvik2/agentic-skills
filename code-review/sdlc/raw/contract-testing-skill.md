# Future: standalone contract-testing skill

Spun out of code-review per ADR-0021 (2026-05-31). Contract testing (Schemathesis-style,
property-based + consumer-driven) does not belong in the deterministic static-analyzer
layer — it exercises a *running* API with live HTTP, needs target/auth config, and produces
findings on a different axis.

Seeds for the skill (lift from git history before this commit):
- `code_review/adapters/schemathesis_.py` — the in-process Schemathesis 4.0.10 adapter:
  schema load via `schemathesis.openapi.from_url`, per-operation Hypothesis generation,
  `additional_checks=[response_schema_conformance]`, failure-type→ruleId mapping, cooperative
  wall-clock deadline with partial-findings-on-timeout, auth via `requests.Session` header
  (token off `argv`), HYPOTHESIS_STORAGE_DIRECTORY redirect.
- `tests/test_adapters/test_schemathesis.py` + `tests/fixtures/schemathesis-target/` — the
  FastAPI fixture app with planted 2xx schema drift (`user_name` vs `username`) and the
  integration harness.
- ADR-0009 (superseded) — the in-process-vs-subprocess rationale, incl. the auth-secrecy
  and partial-findings-on-timeout ACs that drove the in-process choice.
- ADR-0008 — why Pact was dropped (prior contract-testing decision).
- Deps it needs: `schemathesis>=4.0,<5`, `hypothesis`, `fastapi`, `uvicorn` (test fixture).
  - **Transitive constraint to carry over:** the `schemathesis` pin forces `pytest>=8,<9`, which is
    why code-review's `pytest` could not reach 9.x (and CVE-2025-71176 stayed allow-listed). The new
    skill inherits that `pytest<9` ceiling for as long as it pins this schemathesis line.

Open design questions for the skill:
- Live-target config + auth (env-named token) and the sandbox `allowedDomains` posture.
- Whether it emits a thin-runner-style raw bundle or keeps the rich field-level SARIF.
- How it composes with code-review (separate invocation? shared review-selection?).
