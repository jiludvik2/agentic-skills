---
id: adr-0006-sarif-canonical-format
kind: decision
project: code-review
status: accepted
parent: epic-reviewer-subagent
sources: [architecture-reviewer-subagent.md]
created: 2026-05-26
updated: 2026-05-26
tags: [sarif, format, interchange]
---

# ADR-0006: SARIF 2.1.0 as the canonical analyzer output format

## Status

Accepted. Epic assumption 3 (validated by s0/s1).

## Context

The deterministic analyzer layer fans out across many tools with heterogeneous native outputs (SARIF, JSON, DOT, JUnit XML, plain text) and must hand a single, uniform document to the `reviewer` sub-agent for interpretation, dedup, severity mapping, and design review.

## Decision

Use **SARIF 2.1.0 as the canonical format**, extended with a `properties.sdlc_severity` field carrying the SDLC's Critical / Important / Minor / Nit taxonomy.

- Tools whose native output is not SARIF get a **normalisation shim** in their adapter; the resulting SARIF validates against the 2.1.0 schema, sets `tool.driver.name` to the original tool, and uses `ruleId` of the form `<toolname>.<category>`.
- CWE and OWASP references go through SARIF's `taxa` / `supportedTaxonomies` mechanism, not free-form tags.
- Findings are deduplicated by `(file, line, ruleId-family / CWE)` and severity-mapped before reaching the sub-agent.

## Consequences

- One schema to validate against (`jsonschema` in tests); one shape for the sub-agent to read regardless of analyzer count.
- New adapters slot in by emitting (or normalising to) SARIF — no change to the consuming sub-agent.
- **Risk:** SARIF fits *findings* well; if the design-review step later needs decision-shaped output, the format may need supplementing. Revisit if that emerges.
