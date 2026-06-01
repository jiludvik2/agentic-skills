---
id: adr-0021-remove-schemathesis-from-scope
kind: decision
project: code-review
status: accepted
parent: epic-analyzer-thin-runner
sources: [s1-t1c-migrate-schemathesis.md, adr-0009-schemathesis-as-in-process-library.md, adr-0020-thin-invocation-runner.md, architecture-reviewer-subagent.md]
created: 2026-05-31
updated: 2026-05-31
tags: [contract-testing, schemathesis, scope, removal, supersedes-0009, amends-0011]
---

# ADR-0021: Remove Schemathesis / contract testing from code-review scope

## Status

Accepted 2026-05-31 (operator-directed, this session). **Supersedes ADR-0009**
(Schemathesis as in-process library). **Amends ADR-0011** (review-selection scheme):
the `contracts` review domain is removed from the selectable taxonomy. Joins
**ADR-0008** (which earlier dropped Pact) — with Schemathesis gone, code-review carries
no contract-testing analyzer at all. Resolves the s1-t1c autonomy-gate escalation.

> **Amendment (2026-06-01, operator-directed) — the separate-skill spinout is abandoned.**
> The original decision below removed contract testing from code-review *and* parked it as a
> planned standalone skill (seed captured to `/sdlc/raw/contract-testing-skill.md`). The
> operator has now decided contract testing is **out of scope entirely, with no planned
> successor skill** — it is not a deliverable of this project or a queued follow-on. The
> `/sdlc/raw/` seed is discarded. Where the **Decision** and **Consequences** below say
> contract testing "will live as a separate, dedicated skill," read that as **withdrawn**:
> the capability is simply not provided. The audit trail is unchanged — the removed adapter
> and its ADR-0009 design remain in git history, so a *future, separate, unrelated* decision
> could still revive it, but nothing in the current roadmap does.

## Context

s1-t1c (migrate adapters to the thin invocation runner, ADR-0020) reached the
Schemathesis adapter and halted at the gate. Schemathesis is the one adapter that runs
**in-process** (ADR-0009) precisely because a subprocess could not satisfy its ACs —
notably **auth secrecy**: ADR-0009 §3 kept the bearer token out of `argv` via an
in-process `requests.Session` header. Under ADR-0020 the thin runner serialises
`CaptureOutput.command` **verbatim** into the agent-facing bundle (`review_bundle.py`),
and stock `schemathesis run` only accepts auth on `argv` (`-H NAME:VALUE` / `-a USER:PASS`).
Migrating it would therefore have leaked any configured token onto `argv` and into the
bundle — a regression the task spec explicitly forbade ("do not silently weaken auth or
isolation to fit the subprocess model").

Rather than bend a core primitive (a `redact=` scrub) or add Schemathesis-specific
off-`argv` plumbing (`SCHEMATHESIS_HOOKS`) for a single tool, the operator decided that
contract testing does not belong inside the deterministic analyzer layer at all. It is a
different activity — it exercises a *running* API with property-based tests and live HTTP
egress, needs target/auth configuration, and produces value (field-level conformance
findings) on a different axis from the static analyzers. Its rich SARIF mapping is also
lost under the thin runner (which hands the agent raw stdout), removing the main reason
it earned an in-process exception.

## Decision

**Remove Schemathesis and the entire `contracts` review domain from code-review.**
~~Contract testing will live as a **separate, dedicated skill** (captured to `/sdlc/raw/`;
not built under this epic).~~ **Withdrawn by the 2026-06-01 amendment above:** contract
testing is out of scope entirely, with no planned successor skill.

Concretely, removed:

- the `schemathesis` adapter, its registry entry, tests, and fixture;
- the `contracts` domain and `contract-verification` category from `capabilities.json`
  (`--review contracts` is no longer a valid selection);
- the `contract_testing` config field and its CLI plumbing;
- the `schemathesis`, `hypothesis`, `fastapi`, and `uvicorn` dependencies and their
  `stack-pins.md` rows (all Schemathesis-only — verified no other importer).

The generic `scope_restrictions` mechanism stays (it is analyzer-agnostic); its test keeps
coverage via a generic story-level-only stub rather than a Schemathesis-named one.

## Consequences

- **Positive:** unblocks s1-t2/s1-t3; the thin runner stays uniform (no per-tool redaction
  carve-out); no auth-token leak path; lighter install (four deps + their transitive trees
  gone); the contract-testing concern gets a home sized for it (config, live targets, auth)
  instead of being squeezed into the static analyzer contract.
- **Negative / accepted:** code-review no longer offers contract verification — and, per the
  2026-06-01 amendment, no successor skill is planned, so contract verification is simply not
  a capability of this project. `--review contracts` is an unknown-domain error. Historical
  analyzer-coverage QA snapshots that mention Schemathesis are left as dated records.
- **Reversible:** the adapter and its ADR-0009 design remain in git history, so a future,
  separate decision could revive contract testing wholesale — but the 2026-06-01 amendment
  removes it from this project's roadmap; reviving it would be a fresh decision, not a
  resumption of parked work.
