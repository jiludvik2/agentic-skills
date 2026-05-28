---
id: adr-0003-exact-version-pinning-and-pip-fallback
kind: decision
project: code-review
status: accepted
parent: epic-reviewer-subagent
sources: [architecture-reviewer-subagent.md]
created: 2026-05-26
updated: 2026-05-26
tags: [dependencies, governance, supply-chain]
---

# ADR-0003: Exact version pinning + working pip-install fallback

## Status

Accepted. The two governance-risk mitigations agreed during tool-stack review.

## Context

The analyzer layer depends on a broad set of third-party tools. Tool-stack review surfaced a governance risk (the Astral/OpenAI situation) where upstream ownership or licensing changes could break or compromise a dependency without warning. The build must remain reproducible and portable regardless of upstream churn.

## Decision

1. **Pin every tool version exactly** (`==`) in `pyproject.toml` / `package.json`. Version bumps are deliberate, reviewed events — never incidental resolution.
2. **Keep a working pip-install fallback.** `pyproject.toml` follows PEP 621 so `pip install -e .` (Python ≥3.11) yields a working environment. uv is preferred but never required.
3. **Invoke `ruff` only via CLI**, never as a library import — if a fork or alternative is needed later, only CI scripts change.
4. **Never depend on uv-specific `pyproject.toml` features.** `uv.lock` may exist alongside, but everything in `pyproject.toml` stays portable.

## Consequences

- The current code keeps working regardless of upstream governance events.
- Adding a dependency is a deliberate, pinned, reviewed action (`uv add pkg == X.Y.Z` / `npm install --save-exact`), recorded in `stack-pins.md` in the same commit.
- Slightly more friction on upgrades — accepted as the cost of supply-chain resilience.
- The exact pins live in `stack-pins.md` (authoritative *what*); this ADR is the *why*.
