---
id: adr-0009-schemathesis-as-in-process-library
kind: decision
project: code-review
status: accepted
parent: epic-reviewer-subagent
sources: [s4-contract-testing-adapters.md, s4-plan.md, architecture-reviewer-subagent.md, adr-0005-sandbox-compatibility.md]
created: 2026-05-27
updated: 2026-05-27
tags: [contract-testing, adapters, sandbox, network, architecture]
---

# ADR-0009: The Schemathesis adapter runs Schemathesis as an in-process library, not a subprocess

## Status

Accepted. Departs from the default subprocess-per-analyzer pattern for the Schemathesis adapter (s4). Permitted by the architecture's Python-library exception; recorded here because it introduces in-process network egress and reverses the s4-plan's initial subprocess default.

## Context

s4 adds the Schemathesis contract-testing adapter. Schemathesis is a pinned Python dependency (`schemathesis==4.0.10`), so two implementations are possible:

- **(a) subprocess** its CLI (`schemathesis run …`) and parse a machine-readable report (JUnit XML / JSON);
- **(b) import** it and run its checks programmatically.

The architecture's analyzer rule is "invoked as a subprocess, except where the analyzer is itself a Python library (Bandit, Radon, vulture)" — Schemathesis qualifies for the exception either way, so neither option violates the architecture. The s4-plan initially defaulted to (a) for process isolation and to reuse the existing `run_subprocess` timeout machinery. Re-examining the story's acceptance criteria flipped the decision:

1. **Partial findings on timeout.** The story requires "time-budgeted exhaustion produces a clean `status: timeout` with the adapter's partial findings (if any) preserved." A subprocess hard-killed at the 600s wall clock typically loses an end-of-run report (report writers flush at the end) → the AC fails. An in-process loop accumulates findings per operation and returns what it has at the deadline → the AC is satisfied naturally.
2. **Faithful field-level SARIF.** The story wants `message.text` to name the divergent field and `properties.endpoint` to record the failing endpoint. Structured failure objects from the library map to SARIF far more faithfully than scraping a report format.
3. **Auth secrecy.** The token "never appears in CLI argument logs." An in-process auth hook keeps the token out of `argv` entirely; the subprocess path must actively avoid passing it as an argument.
4. **CLI surface volatility.** Schemathesis 4.x reworked its CLI and report flags from 3.x; the report format is a moving target. The library's data model is the more direct, version-checkable contract (pinned at 4.0.10).

## Decision

The Schemathesis adapter imports Schemathesis and runs its checks **in-process**, operation-by-operation, under a **cooperative wall-clock deadline** (per-operation Hypothesis `deadline`/`max_examples`; elapsed-time check between operations; each operation run via `asyncio.to_thread` so the event loop isn't blocked), mapping structured failures to a SARIF shim. It does **not** subprocess the Schemathesis CLI.

This applies only to the Schemathesis adapter. All binary/CLI analyzers (semgrep, gitleaks, trivy, eslint, jscpd, knip, dependency-cruiser) remain subprocesses.

## Consequences

- **Positive:** satisfies the partial-findings-on-timeout AC; faithful field-level SARIF; the auth token never touches `argv`; not coupled to the volatile 4.x CLI/report flags.
- **Negative / accepted:**
  - **Couples the adapter to Schemathesis's programmatic API**, which is less stable than the CLI contract. Mitigated by the exact pin (`==4.0.10`); a version bump must re-validate the API (the s4-plan's verify-first step #1 becomes the upgrade checklist).
  - **No process isolation** — a hang/crash/memory-spike in Schemathesis hits the CLI process directly. Mitigated by per-operation Hypothesis bounds + the cooperative deadline + `asyncio.to_thread` (no hard kill is available in-process, which is the residual risk).
  - **First analyzer to perform network egress in-process** rather than via a child. The sandbox posture (ADR-0005) is unchanged *in effect* — egress is still gated by `sandbox.allowedDomains` — but the egressing process is now the CLI itself. The architecture doc's subprocess section is annotated to note this exception.
- **Reversible:** if the programmatic API proves unstable on a future upgrade, fall back to subprocessing the CLI (re-accepting the partial-findings-on-timeout limitation, or streaming the report to mitigate it).
