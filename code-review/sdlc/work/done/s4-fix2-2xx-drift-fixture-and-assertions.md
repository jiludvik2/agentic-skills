---
id: s4-fix2-2xx-drift-fixture-and-assertions
kind: task
project: code-review
status: done
parent: s4-contract-testing-adapters
sources: [s4-story-level-review]
created: 2026-05-27
updated: 2026-05-27
---

# s4-fix2 — Rework fixture to a 2xx schema drift; tighten integration assertions

## Context

Story-level review found an **Important**: the integration test asserts only
`status in ("ok","timeout")` and guards the ruleId check behind `if results:` with a loose
`startswith("schemathesis.")` — so zero results or a `server_error` result both pass. This is exactly
why the Critical (s4-fix1) shipped green.

The current fixture (`tests/fixtures/schemathesis-target/app.py`) returns `{"username": ...}` against a
`response_model=UserResponse` that declares `user_name`. FastAPI's response_model validation rejects
the missing field and returns **500**, so the drift never reaches Schemathesis as a 2xx
`response_schema_conformance` violation. To exercise AC #1 end-to-end, the fixture must return a 2xx
body that diverges from its declared OpenAPI schema.

Depends on **s4-fix1** (the adapter must register the conformance check before the integration test
can assert `response_schema_violation`).

## Acceptance Criteria

- The fixture endpoint declares `user_name` in its OpenAPI response schema but returns a **200** body
  `{"username": ...}` (e.g. return a raw `JSONResponse` so FastAPI keeps the schema in the OpenAPI doc
  but skips response_model validation). Verified: `TestClient` GET returns status 200 with the
  `username` body, and `/openapi.json` still advertises `user_name`.
- The integration test asserts at least one result with
  `ruleId == "schemathesis.response_schema_violation"` whose `message.text` contains `user_name`; the
  `if results:` guard is removed so an empty result set fails the test.

## Test specification

- Update `test_integration_real_schemathesis_run` (test_schemathesis.py): after the run, assert a
  `response_schema_violation` finding naming `user_name` is present (no `if results:` guard); keep the
  SARIF-schema validation.
- (Opportunistic, Minor #7) add a negative assertion that the configured auth token never appears in
  `output.error`.
