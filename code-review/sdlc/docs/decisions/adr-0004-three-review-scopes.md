---
id: adr-0004-three-review-scopes
kind: decision
project: code-review
status: accepted
parent: epic-reviewer-subagent
sources: [architecture-reviewer-subagent.md]
created: 2026-05-26
updated: 2026-05-26
tags: [scopes, configuration, interface]
---

# ADR-0004: Three review scopes (lite / standard / full), one config key

## Status

Accepted. Replaces an earlier `basic` / `full-reviewer` split.

## Context

Review rigor should match a project's profile — a throwaway PoC and a complex brownfield service need different depth — without burdening the operator with per-tool configuration. An earlier two-way `basic`/`full` split was too coarse on one axis and still implied tool-level choices.

## Decision

A single `reviewer` sub-agent, parameterised by one config value, `review_scope`, with three values mapped to the three natural project profiles:

- **`lite`** — quick PoCs / experiments. LLM-only review, no deterministic tools. Fast, minimal noise. Functionally equivalent to the pre-epic reviewer.
- **`standard`** (default) — simple production projects. Security (Semgrep, Bandit, gitleaks, Trivy) + code quality (Radon, vulture, jscpd, knip, ESLint+sonarjs) + LLM design review grounded by those findings.
- **`full`** — complex brownfield. Everything in `standard` plus coupling/cohesion (pydeps, dependency-cruiser, cohesion LCOM4) and contract testing (Schemathesis, Pact) at story boundaries.

The scope→toolset mapping lives in the skill's `capabilities.json`. The operator sets one value; they do not pick individual tools. A `[scope_overrides]` section in `code-review.toml` exists as an escape hatch but is deliberately not promoted in the quick-start.

## Consequences

- One config line controls review depth; switching scope is instant and reversible, effective on the next dispatch.
- No separate sub-agent files per scope; `lite` is a genuine no-change path for PoCs.
- **Risk (epic assumption 5):** if operators frequently want partial sets (e.g. "standard + dependency-cruiser but not cohesion"), the coarse model breaks and a finer-grained selection would be needed. Validated by operator experience across the three profiles during the validation window.
