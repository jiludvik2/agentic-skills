---
id: adr-0002-subagent-over-http-service
kind: decision
project: code-review
status: accepted
parent: epic-reviewer-subagent
sources: [architecture-reviewer-subagent.md]
created: 2026-05-26
updated: 2026-05-26
tags: [architecture, billing, sub-agent]
---

# ADR-0002: Deliver review as a sub-agent + CLI, not an HTTP service

## Status

Accepted. Supersedes the earlier `epic-reviewer-service` draft.

## Context

An earlier design (`epic-reviewer-service`, eight stories) extracted the analyzer layer into a standalone HTTP daemon: FastAPI, an async job queue, capability discovery endpoints, observability spans, workspace isolation, and a result cache. That shape adds operational surface and, critically, changes the billing model.

## Decision

Deliver the deterministic analyzer layer as a single Claude Code `reviewer` **sub-agent** that shells out to a local **CLI** (`python -m code_review.cli`). No HTTP service, no daemon, no async job queue, no workspace isolation, no result cache. The sub-agent's turn is the unit of work; subprocesses run synchronously within it.

## Drivers

1. **Billing.** The Agent SDK billing change (effective 2026-06-15) makes programmatic Claude Code use draw from a separate credit pool at API rates. Keeping review inside the operator's interactive session preserves the "use the subscription" goal — zero Agent SDK credit consumption.
2. **Scale.** A single-operator interactive workflow does not justify the operational complexity of a service.
3. **Fit.** The SDLC's existing sub-agent pattern is the natural home for review logic.

## Consequences

- Review runs entirely on the interactive subscription pool; CI enforces this (no `claude -p`, no `ANTHROPIC_API_KEY`, no `anthropic` import — adr-0005 / s5).
- Simpler operational footprint; nothing to deploy or keep running.
- The deterministic-analyzer engineering (s0, s2–s4) is substantially the same as the rejected service design — only the transport changed from HTTP to direct CLI invocation.
- No unattended/CI review in this epic; a future epic could add a thin CI wrapper, but that would use the Agent SDK credit pool and needs its own ADR.
