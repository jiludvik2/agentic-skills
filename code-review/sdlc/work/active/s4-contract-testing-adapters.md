---
id: s4-contract-testing-adapters
kind: story
project: code-review
status: active
parent: epic-reviewer-subagent
created: 2026-05-26
updated: 2026-05-27  # Pact dropped from scope (ADR-0008); story is now Schemathesis-only. Hypothesis cache aligned to tempfile/$TMPDIR (matches s3 cache refactor)
---

# s4 — Contract testing adapter (Schemathesis)

## Summary

Add Schemathesis (schema-driven; runs against a live API) as an analyzer. It differs structurally from s3 adapters — it's slower, it requires a running service to test against, and it's only meaningful at story-level scope, not per-task. Normalise its output (JUnit XML) into SARIF so it slots into the same aggregator (s2). Scope restrictions and longer default timeouts are declared in `capabilities.json` (s1).

> **Pact removed.** Pact (consumer-driven contract testing) was originally planned for this story. It has been **dropped from the epic** — see **ADR-0008**. Rationale in brief: the target workflow doesn't need consumer-driven contracts, and dropping Pact removes the project's only Docker / native-binding dependency, keeping `setup.sh`'s binary-on-PATH + vendored-`node_modules` install model intact. If a consumer-driven contract-testing need arises later, it returns as its own story.

## Use Case

- **As a** SDLC operator with a FastAPI (or similar) backend exposing an OpenAPI spec
- **I want to** include contract-testing findings in story-level reviews
- **so that** I catch backend changes that drift from the OpenAPI spec (Schemathesis), without writing separate CI plumbing

## Acceptance Criteria

### Scenario: Schemathesis adapter runs against a live API and produces SARIF

- **Given** a fixture FastAPI service running on `localhost:8080` with an OpenAPI spec at `/openapi.json` that contains a deliberate drift (e.g., an endpoint returns `username` but the spec says `user_name`)
- **When** the Schemathesis adapter runs with `spec_url=http://localhost:8080/openapi.json`
- **Then** the output SARIF contains at least one `result` whose `ruleId` is `schemathesis.response_schema_violation`, whose `message.text` names the divergent field, and whose `properties.endpoint` records the failing endpoint

### Scenario: The Schemathesis adapter is only available at story-level scope

- **Given** the CLI is invoked with `--scope per-task --analyzer schemathesis`
- **When** the CLI validates the invocation
- **Then** the CLI exits with a clear error stating that the Schemathesis adapter requires `--scope story-level`; the same invocation with `--scope story-level` is accepted

### Scenario: The Schemathesis adapter honours longer timeout budgets

- **Given** the Schemathesis adapter is configured with a default timeout of 600 seconds (vs. 60–180 for s3 adapters), declared in `capabilities.json`
- **When** I check the timeout configuration
- **Then** the contract adapter's timeout is at least 5x the deterministic-adapter defaults, configurable via `code-review.toml`, and time-budgeted exhaustion produces a clean `status: "timeout"` outcome with the adapter's partial findings (if any) preserved

### Scenario: Adapter fails cleanly when the target API isn't reachable

- **Given** the Schemathesis target API isn't running
- **When** the adapter runs
- **Then** the adapter returns `AnalyzerOutput` with `error` populated naming the reachability issue, the CLI's consolidated output reflects the failure per-analyzer, and the deterministic-layer SARIF from other analyzers is preserved

### Scenario: Contract findings carry severity mapped to Critical

- **Given** a contract violation finding from Schemathesis
- **When** it flows through the s2 severity mapper
- **Then** `properties.sdlc_severity == "critical"` by default (contract violations break inter-service correctness — line 166 of SDLC.md), unless overridden in `code-review.toml`

### Scenario: Auth is configurable per-target

- **Given** the Schemathesis target requires Bearer auth
- **When** the adapter is invoked with `auth: {type: bearer, token_env: "FIXTURE_API_TOKEN"}` in its config
- **Then** the adapter reads the token from the named env var (not from request payload or CLI args) and sends it on every request; the token never appears in logs, the consolidated output, or any artefact the sub-agent reads

### Scenario: The Schemathesis adapter is the only analyzer that needs runtime network access

- **Given** the operator's Claude Code session has `/sandbox` enabled with no `allowedDomains` widening (i.e. only per-task review works)
- **When** the operator attempts a story-level review that would include contract testing
- **Then** the Schemathesis adapter fails with `status: "error"` and an `error` field naming the specific host (e.g. "Schemathesis target `http://localhost:8080` not reachable; check that the host is in `sandbox.allowedDomains`"); the consolidated output exits non-zero; other adapters' results are preserved; the sub-agent escalates to the operator with a clear remediation path
- **and Given** the operator subsequently adds the target host to `sandbox.allowedDomains` and retries
- **Then** the Schemathesis adapter completes successfully

### Scenario: Schemathesis cache writes never land in CWD

- **Given** the Schemathesis adapter is running (which uses Hypothesis-based fuzzing with a `.hypothesis/` cache)
- **When** I monitor filesystem writes during a Schemathesis run
- **Then** the adapter redirects Hypothesis's storage to a `tempfile.TemporaryDirectory` under `$TMPDIR` via the `HYPOTHESIS_STORAGE_DIRECTORY` environment variable (matching the s3 cache pattern used by semgrep/gitleaks/trivy); no `.hypothesis/` directory or other scratch file is created in CWD, and the temp directory is auto-cleaned when the run completes

### Scenario: SKILL.md documents which domains the operator must allowlist

- **Given** an operator setting up the skill for story-level reviews
- **When** they read `SKILL.md`'s "Sandbox configuration" section (added in s1)
- **Then** they find an explicit subsection on contract testing that says: "Story-level reviews invoke Schemathesis. It needs network access to the targets you configure in `code-review.toml`'s `[contract_testing]` section. Add only those specific hosts (e.g., `localhost`, your internal service hostname) to `sandbox.allowedDomains` — never widen to wildcards or public-internet hosts."

## Test specification

- **Schemathesis adapter integration test** — fixture FastAPI service with a planned spec drift; assert the drift surfaces with the expected `ruleId`. Skipif-guarded on the FastAPI test dependency / fixture service being available.
- **Scope-validation test** — `per-task` + `schemathesis` → CLI error; `story-level` + `schemathesis` → accepted.
- **Timeout-budget test** — config-driven timeout values applied; exhaustion produces `status: "timeout"` with partial findings preserved.
- **Reachability-failure test** — target API is `http://localhost:1` (unreachable); adapter fails cleanly with informative error; other analyzers' results preserved.
- **Sandbox-blocked-network test** — run the adapter with the network stack patched to simulate sandbox denial of the configured target; assert the error message explicitly names `sandbox.allowedDomains` as the likely cause.
- **Hypothesis cache-redirect test** — set `HOME` to an empty temp dir, run the adapter; assert all Hypothesis storage writes land under the adapter's `tempfile` directory (`$TMPDIR`) and that no `.hypothesis/` appears in CWD or under the temp `HOME`.
- **Severity-mapping test** — contract violations route to `critical` after s2 mapping.
- **Auth secrecy test** — assert the token never appears in the consolidated output, in `analyzers.<name>.raw_output` (if present for debugging), or in CLI argument logs.

## Out of scope (deferred to later stories)

- **Pact / consumer-driven contract testing** — removed from this epic (ADR-0008); returns as its own story if a real need arises.
- GraphQL contract testing — Schemathesis supports it but the fixture / test surface is separate work.
- gRPC / Protobuf contract testing — out of this epic.
- AsyncAPI (event-driven systems) — separate epic if needed.
- Running Schemathesis in stateful "links" mode for multi-step API flows — single-operation mode is the default in this story.
