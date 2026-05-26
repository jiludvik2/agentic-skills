---
id: s4-contract-testing-adapters
kind: story
project: code-review
status: active
parent: epic-reviewer-subagent
created: 2026-05-26
updated: 2026-05-26  # sandbox compatibility: allowedDomains, cache redirection
---

# s4 — Contract testing adapters (Schemathesis, Pact)

## Summary

Add Schemathesis (schema-driven; runs against a live API) and Pact (consumer-driven; reads contracts from a broker) as analyzers. These differ structurally from s3 adapters — they're slower, they may require a running service or broker, and they're only meaningful at story-level scope, not per-task. Normalise their output (JUnit XML, Pact's own JSON) into SARIF so they slot into the same aggregator (s2). Scope restrictions and longer default timeouts are declared in `capabilities.json` (s1).

## Use Case

- **As a** SDLC operator with a FastAPI backend and a Next.js frontend that consumes its API
- **I want to** include contract-testing findings in story-level reviews
- **so that** I catch backend changes that drift from the OpenAPI spec (Schemathesis) and backend changes that break the frontend's actual consumption pattern (Pact), without writing separate CI plumbing for each tool

## Acceptance Criteria

### Scenario: Schemathesis adapter runs against a live API and produces SARIF

- **Given** a fixture FastAPI service running on `localhost:8080` with an OpenAPI spec at `/openapi.json` that contains a deliberate drift (e.g., an endpoint returns `username` but the spec says `user_name`)
- **When** the Schemathesis adapter runs with `spec_url=http://localhost:8080/openapi.json`
- **Then** the output SARIF contains at least one `result` whose `ruleId` is `schemathesis.response_schema_violation`, whose `message.text` names the divergent field, and whose `properties.endpoint` records the failing endpoint

### Scenario: Pact adapter verifies provider against broker-published contracts

- **Given** a fixture Pact broker (Docker container) holding one consumer contract for a known endpoint
- **and Given** a fixture provider service that satisfies the contract
- **When** the Pact adapter runs with `broker_url=...` and `provider=fixture-api`
- **Then** the output SARIF reports verification success with no findings; modifying the provider to break the contract produces a `result` with `ruleId: pact.contract_violation` and `properties.consumer` naming which consumer's contract broke

### Scenario: Contract adapters are only available at story-level scope

- **Given** the CLI is invoked with `--scope per-task --analyzer schemathesis`
- **When** the CLI validates the invocation
- **Then** the CLI exits with a clear error stating that contract adapters require `--scope story-level`; the same invocation with `--scope story-level` is accepted

### Scenario: Contract adapters honour longer timeout budgets

- **Given** the Schemathesis adapter is configured with a default timeout of 600 seconds (vs. 60–180 for s3 adapters), declared in `capabilities.json`
- **When** I check the timeout configuration
- **Then** contract adapters' timeouts are at least 5x the deterministic-adapter defaults, configurable via `code-review.toml`, and time-budgeted exhaustion produces a clean `status: "timeout"` outcome with the adapter's partial findings (if any) preserved

### Scenario: Adapter fails cleanly when its prerequisite isn't reachable

- **Given** the Pact broker URL is unreachable, or the Schemathesis target API isn't running
- **When** the adapter runs
- **Then** the adapter returns `AnalyzerOutput` with `error` populated naming the reachability issue, the CLI's consolidated output reflects the failure per-analyzer, and the deterministic-layer SARIF from other analyzers is preserved

### Scenario: Contract findings carry severity mapped to Critical

- **Given** a contract violation finding from either Schemathesis or Pact
- **When** it flows through the s2 severity mapper
- **Then** `properties.sdlc_severity == "critical"` by default (contract violations break inter-service correctness — line 166 of SDLC.md), unless overridden in `code-review.toml`

### Scenario: Auth is configurable per-target

- **Given** the Schemathesis target requires Bearer auth
- **When** the adapter is invoked with `auth: {type: bearer, token_env: "FIXTURE_API_TOKEN"}` in its config
- **Then** the adapter reads the token from the named env var (not from request payload or CLI args) and sends it on every request; the token never appears in logs, the consolidated output, or any artefact the sub-agent reads

### Scenario: Contract adapters are the only analyzers that need runtime network access

- **Given** the operator's Claude Code session has `/sandbox` enabled with no `allowedDomains` widening (i.e. only per-task review works)
- **When** the operator attempts a story-level review that would include contract testing
- **Then** the Schemathesis and Pact adapters fail with `status: "error"` and an `error` field naming the specific host (e.g. "Schemathesis target `http://localhost:8080` not reachable; check that the host is in `sandbox.allowedDomains`"); the consolidated output exits non-zero; other adapters' results are preserved; the sub-agent escalates to the operator with a clear remediation path
- **and Given** the operator subsequently adds the target host to `sandbox.allowedDomains` and retries
- **Then** the contract adapters complete successfully

### Scenario: Contract adapters' cache writes stay inside CWD

- **Given** the Schemathesis adapter is running (which uses Hypothesis-based fuzzing with a `.hypothesis/` cache)
- **When** I monitor filesystem writes during a Schemathesis run
- **Then** every write target is inside the project's CWD — Schemathesis's `.hypothesis/` is redirected to `.claude/skills/code-review/cache/hypothesis/` via the `HYPOTHESIS_STORAGE_DIRECTORY` environment variable; the same applies to any Pact verification log files (configured to `.claude/skills/code-review/cache/pact/`)

### Scenario: SKILL.md documents which domains the operator must allowlist

- **Given** an operator setting up the skill for story-level reviews
- **When** they read `SKILL.md`'s "Sandbox configuration" section (added in s1)
- **Then** they find an explicit subsection on contract testing that says: "Story-level reviews invoke Schemathesis and Pact. Both need network access to the targets you configure in `code-review.toml`'s `[contract_testing]` section. Add only those specific hosts (e.g., `localhost`, your internal broker hostname) to `sandbox.allowedDomains` — never widen to wildcards or public-internet hosts."

## Test specification

- **Schemathesis adapter integration test** — fixture FastAPI service with a planned spec drift; assert the drift surfaces with the expected `ruleId`.
- **Pact adapter integration test** — Dockerized Pact broker fixture + fixture provider; happy path + broken-provider path; assert SARIF outputs match expectations.
- **Scope-validation test** — `per-task` + contract analyzer → CLI error; `story-level` + contract analyzer → accepted.
- **Timeout-budget test** — config-driven timeout values applied; exhaustion produces `status: "timeout"` with partial findings preserved.
- **Reachability-failure test** — broker URL is `http://localhost:1` (unreachable); adapter fails cleanly with informative error; other analyzers' results preserved.
- **Sandbox-blocked-network test** — run contract adapters with the network stack patched to simulate sandbox denial of the configured target; assert the error message explicitly names `sandbox.allowedDomains` as the likely cause.
- **Hypothesis cache-redirect test** — set `HOME` to an empty temp dir, run Schemathesis; assert all `.hypothesis/` writes land under `.claude/skills/code-review/cache/hypothesis/` and none under the temp `HOME`.
- **Severity-mapping test** — contract violations route to `critical` after s2 mapping.
- **Auth secrecy test** — assert the token never appears in the consolidated output, in `analyzers.<name>.raw_output` (if present for debugging), or in CLI argument logs.

## Out of scope (deferred to later stories)

- GraphQL contract testing — Schemathesis supports it but the fixture / test surface is separate work.
- gRPC / Protobuf contract testing — out of this epic.
- AsyncAPI (event-driven systems) — separate epic if needed.
- Running Schemathesis in stateful "links" mode for multi-step API flows — single-operation mode is the default in this story.
- Operating the Pact broker as part of the skill's deployment — the broker is an external dependency the operator runs separately.
- Bi-directional contract testing (Pactflow's exclusive) — basic consumer-driven contracts only.
