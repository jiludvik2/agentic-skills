---
id: adr-0005-sandbox-compatibility
kind: decision
project: code-review
status: accepted
parent: epic-reviewer-subagent
sources: [architecture-reviewer-subagent.md]
created: 2026-05-26
updated: 2026-05-26
tags: [sandbox, security, constraint]
---

# ADR-0005: Sandbox compatibility is a first-class constraint; no self-bypass

## Status

Accepted. A load-bearing architectural constraint (architecture §16).

## Context

The operator runs Claude Code with `/sandbox` enabled under strict settings (`failIfUnavailable: true`, `allowUnsandboxedCommands: false`). The sandbox confines writes to the project's CWD subtree and blocks network egress beyond an allow-list (macOS Seatbelt, Linux/WSL2 bubblewrap). Separately, Anthropic documents that Claude Code *may* retry a sandbox-blocked command with `dangerouslyDisableSandbox`, and a March 2026 incident showed Claude Code disabling its own sandbox to finish a task.

## Decision

Treat sandbox compatibility as a first-class design constraint, not an afterthought:

1. **CWD-only writes.** All transient output — `runs/`, `cache/`, `node_modules/` — lives inside the skill directory (inside CWD). No `sandbox.filesystem.allowWrite` widening is required. (The pre-sandbox draft put outputs in `/tmp`; that is rejected.)
2. **Offline by construction.** Network fetches happen exactly once, in `scripts/setup.sh`, run *outside* the sandbox before first use. Analyzers are wired to offline/local data thereafter (Trivy `--offline-scan` against a pre-fetched DB, Semgrep local rule packs, vendored Node binaries, redirected Hypothesis cache).
3. **Narrow network policy.** The only runtime network need is contract-test targets at `full` scope, via documented, specific `sandbox.allowedDomains` entries — never wildcards or public hosts.
4. **No self-bypass.** The `reviewer` sub-agent's prompt explicitly forbids retrying a failed command with `dangerouslyDisableSandbox`. On a sandbox-blocked failure it escalates via the Autonomy gate, naming what was blocked and the exact `settings.json` change that would unblock it.

## Consequences

- The skill runs under strict sandbox settings without prompting for widening; a CI sandbox-compatibility test enforces this.
- Docker-based fixtures (Pact broker) are sandbox-incompatible and run only outside the sandbox (`pytest --run-docker`).
- The constraint shapes every adapter (see architecture §16.3 per-adapter table); a tool that cannot comply is replaced or gated behind an operator-approved ADR.
