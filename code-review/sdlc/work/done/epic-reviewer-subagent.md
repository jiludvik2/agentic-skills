---
id: epic-reviewer-subagent
kind: epic
project: code-review
status: done
children:
  - s0-analyzer-facade-and-two-adapters
  - s1-reviewer-skill-and-capabilities
  - s2-aggregator-and-severity-mapping
  - s3-remaining-deterministic-adapters
  - s4-contract-testing-adapters
  - s5-review-selection-scheme
created: 2026-05-26
updated: 2026-05-28
closed: 2026-05-28
tags: [reviewer, sarif, sdlc, ai-native, deterministic-analyzer]
---

# Epic: Deterministic Code-Review Skill

> **Note (epic close, 2026-05-28).** This epic was originally framed as a *unified* `reviewer` sub-agent extending the SDLC's reviewer with a deterministic analyzer layer, picking a single `review_scope` (`lite` / `standard` / `full`) at project setup. During the s5 design phase that framing was retired in favour of a clean deterministic/probabilistic split: the `code-review` skill is a pure deterministic analyzer (no LLM inside, no sub-agent install) and the probabilistic LLM-design-review work moves to a sibling `intent-review` project. See **ADR-0010** for the split and **ADR-0011** for the review-selection scheme that replaces `review_scope`. The original framing — and its hypotheses about layering deterministic + LLM review in one turn — is preserved below this banner for historical context, followed by a "What shipped" section that records the actual deliverable.

## What shipped

The `code-review` skill is a deterministic code-analysis layer that runs one or more analyzers against a target or a diff and emits a single consolidated JSON document (SARIF findings + complexity / coupling / cohesion metrics). It is invoked via `python -m code_review.cli`; no LLM lives inside the skill. Consumers (a future `intent-review` LLM, a CI script, a human at the terminal) all share the same surface.

- **Stories closed:** s0 (analyzer façade + Semgrep/Radon), s1 (skill scaffold + `capabilities.json` + `setup.sh`), s2 (aggregator + severity mapping), s3 (Bandit, gitleaks, Trivy, jscpd, vulture, knip, dependency-cruiser, ESLint+sonarjs, pydeps, cohesion), s4 (Schemathesis at story-level scope; Pact dropped per ADR-0008), s5 (review-selection scheme: `--review` domain/subcategory and `--depth` quick/full per ADR-0011; consumer-sub-agent removal per ADR-0010).
- **Decisions of record:** ADR-0001 through ADR-0011 (publication, sub-agent-over-HTTP rejection, exact pins + pip fallback, three-review-scopes [superseded by ADR-0011], sandbox compatibility, SARIF canonical, package-bundled contracts, Pact drop, Schemathesis in-process, **ADR-0010 split**, **ADR-0011 review-selection**).
- **Architecture:** `/sdlc/docs/architecture/architecture-reviewer-subagent.md` — retains the load-bearing decisions (Analyzer Protocol, SARIF + sdlc_severity envelope, sandbox section, severity mapping, dedup). §5 scope-mapping table and §8 sub-agent integration are marked superseded by ADR-0011 / ADR-0010 respectively; the supersede banner at the top of the document points readers at the current contract.
- **Out of scope, by design:** the LLM design-review step (now in `intent-review`); cross-skill aggregation/dedup (a consumer's judgment, not a built-in); a separate sub-agent file installed by `code-review/setup.sh` (removed in s5 Phase 3); unattended/CI invocation (a future epic, billed against the Agent SDK pool rather than the interactive subscription).

The skill works under the operator's strict-sandbox configuration (`failIfUnavailable: true`, `allowUnsandboxedCommands: false`) with no `allowWrite` widening; `allowedDomains` stays empty for per-task reviews and is narrowed to the contract-test target only for story-level Schemathesis runs.

## Validated hypotheses

Three of the original five hypotheses were validated by the work as it shipped; the other two were superseded by the split:

- **Assumption 3 — SARIF + `properties.sdlc_severity` is the right canonical format.** Validated: every analyzer normalises to SARIF, the aggregator dedups by `(file, line ±3, CWE)`, and the severity table maps cleanly to the SDLC's Critical/Important/Minor/Nit taxonomy. The format extends naturally — `intent-review`'s LLM findings will emit the same envelope.
- **Assumption 4 — every analyzer runs cleanly under `/sandbox`.** Validated: per-adapter sandbox accommodations (Trivy DB pre-fetched, Semgrep offline, Node tooling vendored, Hypothesis cache redirected, etc.) all land in `setup.sh` and `cache/`, and `test_sandbox_compatibility.py` is part of CI. Only Schemathesis needs a narrow `allowedDomains` widening, story-level only.
- **Assumption 5 — three scopes are the right granularity.** *Superseded* by ADR-0011's review-selection scheme: domains × subcategories × depth tier expresses what `lite`/`standard`/`full` couldn't (e.g., "quick security review" vs "full coupling check") without per-tool configuration.

The two hypotheses about LLM design review hosting (1: layering beats LLM-only; 2: turn budget) are now `intent-review`'s to validate.

## Stories (final sequence)

0. **s0-analyzer-facade-and-two-adapters** — `Analyzer` Protocol, SARIF/MetricSet types, Semgrep + Radon adapters, CLI scaffold. (done)
1. **s1-reviewer-skill-and-capabilities** — `.claude/skills/code-review/` packaging, `SKILL.md`, `capabilities.json` (now with `domain`/`subcategory`/`tier` per ADR-0011), `setup.sh`, runtime capability check. (done)
2. **s2-aggregator-and-severity-mapping** — SARIF dedup, SDLC severity mapping, ranked hotspots. (done)
3. **s3-remaining-deterministic-adapters** — Bandit, gitleaks, Trivy, jscpd, vulture, knip, dependency-cruiser, ESLint+sonarjs, pydeps, cohesion. (done)
4. **s4-contract-testing-adapters** — Schemathesis at story-level only; Pact dropped (ADR-0008). (done)
5. **s5-review-selection-scheme** — `--review` (domain or subcategory, repeatable) + `--depth` (quick/full); case-insensitive normalisation; redundancy/dedup warnings to stderr; the bundled consumer sub-agent removed. (done)

Auto-progress and per-task/story-level Review applied throughout per SDLC rules #22 and #25. No round-3 escalations were required.

## Open items at close

These outlive the epic but are not blockers:

- **`README.md` (rule #17).** This epic closes without a project-root `README.md` — to be drafted in a follow-up (operator approves README content per "What stays human"). The bundled `.claude/skills/code-review/SKILL.md` covers the analyzer interface for the immediate downstream consumer.
- **Plans linger in `active/`.** `s3-plan.md` and `s4-plan.md` remain in `/sdlc/work/active/` per project precedent (per-story plans aren't archived to `done/`).
- **Architecture has light prose drift.** §8 sub-agent integration and §5 scope-mapping table carry supersede notes pointing to ADR-0010 / ADR-0011 rather than being rewritten in place — the original framing is historically interesting and the live contract sits in the ADRs.
- **Supply-chain gate.** Rule #26 N/A in this project (no `make audit` defined). `pytest==8.3.4` / CVE-2025-71176 allow-listed until 2026-08-31 (blocked by `schemathesis==4.0.10` pinning `pytest<9`); a future ADR can formalise an audit gate.

---

## Original framing (historical, superseded by ADR-0010)

The text below describes the unified-reviewer hypothesis as it was framed at epic compile (2026-05-26). It is retained because it documents the reasoning that led to the s0–s4 shape, which is unchanged.

### The original three-scope premise

Extend the SDLC's existing `reviewer` sub-agent with a deterministic analyzer layer (Semgrep, Bandit, Radon, dependency-cruiser, gitleaks, jscpd, vulture, knip, Trivy, pydeps, cohesion, ESLint+sonarjs, Schemathesis), exposed as a Claude Code skill called `code-review`. A single `reviewer` sub-agent handles all projects; the operator picks a **review scope** (`lite`, `standard`, or `full`) at project setup time that controls which analyzers fire. No separate sub-agent files, no HTTP service, no separate process, no programmatic-pool billing.

The three scopes were meant to match three real project profiles:

- **`lite`** — quick PoCs and throwaway experiments. LLM-only review, no deterministic tools. Fast; minimal noise.
- **`standard`** — simple production projects. Security scanning (Semgrep, Bandit, gitleaks, Trivy) + code quality (Radon, vulture, jscpd, knip, ESLint+sonarjs) + LLM design review grounded by those findings. The default.
- **`full`** — complex brownfield projects. Everything in `standard` plus coupling/cohesion analysis (pydeps, dependency-cruiser, cohesion LCOM4) + contract testing (Schemathesis) at story boundaries. Accepts longer review time for deeper coverage.

The operator was to set one config value (`review_scope`) in the SDLC skill's project-level config. They wouldn't pick individual tools.

This replaced the earlier `epic-reviewer-service` design (HTTP service) for three reasons: (1) the Agent SDK billing change made programmatic Claude Code use draw from a separate credit pool at API rates, undermining the "use the subscription" goal; (2) the single-operator interactive workflow didn't justify a service's operational complexity; (3) the SDLC's existing sub-agent pattern looked like the natural home for review logic.

### Why the framing was retired

During s5's design phase (2026-05-28), three signals pushed the work to split:

1. **The deterministic and probabilistic layers don't share state.** SARIF goes one way (skill → consumer), nothing comes back; the LLM consumer just needs to read SARIF and emit findings in the same envelope. There's no shared context, no shared turn, no shared install.
2. **A sub-agent inside a skill couples the analyzer code to a specific harness.** Other consumers — a CI script, a different LLM, a human at the terminal — would have had to work around the reviewer sub-agent's prompt expectations.
3. **`lite`/`standard`/`full` couldn't express "quick security review" vs "full coupling check"** — the granularity matched project profiles, not review intents. Domain × subcategory × depth (ADR-0011) does.

The split is recorded in ADR-0010; the review-selection scheme is in ADR-0011 and s5's spec.

### Original assumptions (for the record)

The original epic enumerated five assumptions. The current status of each:

1. *Deterministic-layer + narrowed LLM design review beats LLM-only at `standard`/`full` scope.* **Reassigned to `intent-review`.** The `code-review` skill does not host an LLM; this is now `intent-review`'s hypothesis to validate.
2. *The sub-agent's turn budget can host both deterministic-result interpretation and design review.* **Reassigned to `intent-review`.** Same reason.
3. *SARIF + `properties.sdlc_severity` is the right canonical format.* **Validated.** See "Validated hypotheses" above.
4. *Every analyzer runs cleanly inside the operator's `/sandbox`-enabled session.* **Validated.** See "Validated hypotheses" above.
5. *Three scopes are the right granularity.* **Superseded** by ADR-0011.
