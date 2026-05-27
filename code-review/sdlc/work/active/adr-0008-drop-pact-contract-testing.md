---
id: adr-0008-drop-pact-contract-testing
kind: decision
project: code-review
status: accepted
parent: epic-reviewer-subagent
sources: [s4-contract-testing-adapters.md, epic-reviewer-subagent.md, adr-0005-sandbox-compatibility.md]
created: 2026-05-27
updated: 2026-05-27
tags: [scope, contract-testing, dependencies, sandbox]
---

# ADR-0008: Drop Pact (consumer-driven contract testing) from the reviewer epic

## Status

Accepted. Narrows story `s4-contract-testing-adapters` to a single analyzer (Schemathesis) and removes Pact from the epic's analyzer list and `full`-scope description. Operator decision, 2026-05-27.

## Context

The epic's s4 story originally bundled two contract-testing analyzers: **Schemathesis** (schema-driven; runs a generated test suite against a live API and flags OpenAPI-spec drift) and **Pact** (consumer-driven; verifies a provider against broker-published consumer contracts). They were grouped because both are slow, story-level-only, and network-bound.

Two facts reframed the Pact half during s4 planning:

1. **No demonstrated need.** The target workflow is single-service review against an OpenAPI spec. Consumer-driven contracts (Pact's value) only pay off with a real consumer/provider pair and a contract broker — infrastructure and a collaboration shape this project does not have. The operator judged it won't be needed.
2. **Pact is the project's only Docker / heavy dependency.** Every existing analyzer's test prerequisite is either a binary on `PATH` (`shutil.which`: gitleaks, trivy, semgrep) or a vendored `node_modules/.bin` (`npm ci`: eslint, jscpd, knip, depcruiser) — all provisioned by `setup.sh` with no daemon, no image, no root. Pact's provider-verification story (per the original AC) needed a Dockerized `pactfoundation/pact-broker` (+ Postgres) fixture, plus the `pact-python` / `pact-python-ffi` native dependency. That is a categorical step up in test-environment weight that `setup.sh` cannot reasonably provision, and it collides with the strict-sandbox model (ADR-0005).

Schemathesis carries neither problem: it is already pinned (`schemathesis==4.0.10`), runs against a plain HTTP target, and its only test prerequisite is a fixture FastAPI service (a pinned test-only dependency).

## Decision

Remove Pact from the reviewer epic. Concretely:

- `s4-contract-testing-adapters` is now **Schemathesis-only** (story retitled, Pact scenarios and the Pact integration test removed, Pact listed under "out of scope").
- The epic's analyzer enumeration, `full`-scope description, and discovery-experiment list drop Pact; an explicit non-goal ("No Pact / consumer-driven contract testing") is recorded so it doesn't drift back in.
- **No `pact-python` / `pact-python-ffi` dependency is added.** `schemathesis==4.0.10` stays pinned. The s4 plan introduces only `fastapi` as a test-fixture-only pin.
- The project remains Docker-free: no analyzer or test requires a container daemon.

## Consequences

- **Positive:** s4 shrinks to one adapter; the green bar stays binary-/`node_modules`-only (no Docker gate in CI); the strict-sandbox guarantee is preserved; one fewer native dependency to pin and prefetch.
- **Negative / accepted:** the reviewer cannot catch provider-breaks-consumer regressions. For a single-service-against-its-own-spec workflow this is not a gap that matters; Schemathesis still catches the implementation-drifts-from-spec case.
- **Reversible:** Pact returns as its own story (with its own ADR superseding this one) if a concrete consumer-driven need appears — e.g. the operator starts maintaining a frontend/backend pair with a shared contract.
