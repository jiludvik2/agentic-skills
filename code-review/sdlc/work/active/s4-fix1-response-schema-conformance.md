---
id: s4-fix1-response-schema-conformance
kind: task
project: code-review
status: active
parent: s4-contract-testing-adapters
sources: [s4-story-level-review]
created: 2026-05-27
updated: 2026-05-27
notes: |
  Story-level review MINORs not filed as fixes (captured here for opportunistic cleanup):
  - #4 multi-target hard-return (schemathesis_.py:139-147): first unreachable target does a hard
    `return`, discarding partial findings from earlier targets and skipping later targets. Should
    `continue` and accumulate per-target status. (In-adapter cross-target preservation; the
    cross-analyzer AC is already met by the aggregator.)
  - #5 orphaned --review-scope (cli.py:187, enum :28): ReviewScope option/enum still declared but
    never consumed after t0 introduced --scope for the timing axis. Remove, or wire into
    analyzer-depth. Also: capabilities `review_scope` field is an enum-less string (schema :75) on
    only the schemathesis entry — fold into the same cleanup.
  - #7 auth-secrecy test gap (test_schemathesis.py:104-140): asserts token absent from SARIF but not
    from AnalyzerOutput.error or logs. Add a negative assertion on output.error.
  Story-level review NIT dropped: _MAX_EXAMPLES=5 lacks a rationale comment.
  Minor #6 (title-slug ruleId fragility) is RESOLVED by this task's explicit Failure-type→ruleId map.
---

# s4-fix1 — Register response_schema_conformance; map to response_schema_violation naming the field

## Context

Story-level review found a **Critical**: the Schemathesis adapter calls
`case.call_and_validate(session=session)` with no `checks=`, so only the default `not_a_server_error`
check runs (confirmed by the adapter's own docstring, lines 35-37). The story's flagship AC #1
requires response-schema drift on a 2xx response to surface as
`ruleId="schemathesis.response_schema_violation"` whose `message.text` names the divergent field.
With only `not_a_server_error` active, genuine OpenAPI drift that returns 2xx is invisible; the
fixture's drift even surfaces as a 500 today, so the only finding emitted is `schemathesis.server_error`.

Verified empirically: `TestClient` against the current fixture returns **500** (FastAPI's
`response_model` rejects the missing `user_name`), so even the conformance check would not see a 2xx
violation — the fixture rework lives in **s4-fix2**.

This task fixes the **adapter** side. Resolving the Critical also requires deriving ruleIds from
known `Failure` types rather than slugging the human-readable title (Minor #6), so a
`response_schema_conformance` failure maps to the stable `schemathesis.response_schema_violation`
ruleId the AC requires.

## Acceptance Criteria

- The adapter runs the OpenAPI `response_schema_conformance` check (in addition to the default
  `not_a_server_error`) on every operation via `call_and_validate(checks=[...], session=...)`.
- A `response_schema_conformance` failure maps to `ruleId == "schemathesis.response_schema_violation"`,
  `level == "error"`, with `message.text` naming the divergent field and `properties.endpoint` set.
- A `not_a_server_error` failure continues to map to a stable `schemathesis.server_error` ruleId.
- RuleId derivation no longer depends on slugging the free-text `Failure.title` (Minor #6): known
  `Failure` types map to fixed suffixes; an unknown type falls back to a safe slug.

## Test specification

- `test_conformance_failure_maps_to_response_schema_violation` — synthetic conformance `Failure`
  (title/type per the verify-first probe, message naming `user_name`, operation `GET /users/{user_id}`)
  → `_failure_to_sarif_result` (or the new mapping) yields `ruleId == "schemathesis.response_schema_violation"`,
  `message.text` contains `user_name`, `properties.endpoint` == the operation.
- `test_server_error_maps_to_stable_ruleid` — synthetic server-error `Failure` → `schemathesis.server_error`
  regardless of title phrasing/punctuation.
- Confirm `call_and_validate` is invoked with the conformance check registered (mock/spy in the
  existing run-path test).

## Verify-first unknown

Confirm the Schemathesis 4.0.10 API before coding: does `case.call_and_validate(checks=[...], session=...)`
accept a `checks=` kwarg; import path for `response_schema_conformance` (`schemathesis.specs.openapi.checks`);
the `Failure` subclass/type and `.title`/`.message` shape for a conformance failure (does `message` name
the field?). Record confirmed calls in the adapter docstring.
