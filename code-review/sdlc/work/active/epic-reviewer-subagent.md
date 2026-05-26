---
id: epic-reviewer-subagent
kind: epic
project: code-review
status: active
children:
  - s0-analyzer-facade-and-two-adapters
  - s1-reviewer-skill-and-capabilities
  - s2-aggregator-and-severity-mapping
  - s3-remaining-deterministic-adapters
  - s4-contract-testing-adapters
  - s5-subagent-integration-and-design-review
created: 2026-05-26
updated: 2026-05-26  # scope model: lite/standard/full replaces basic/full-reviewer split
tags: [reviewer, sarif, sdlc, ai-native, subagent]
---

# Epic: Reviewer Sub-agent with Deterministic Analyzer Layer

Extend the SDLC's existing `reviewer` sub-agent with a deterministic analyzer layer (Semgrep, Bandit, Radon, dependency-cruiser, gitleaks, jscpd, vulture, knip, Trivy, pydeps, cohesion, ESLint+sonarjs, Schemathesis, Pact), exposed as a Claude Code skill called `code-review`. A single `reviewer` sub-agent handles all projects; the operator picks a **review scope** (`lite`, `standard`, or `full`) at project setup time that controls which analyzers fire. No separate sub-agent files, no HTTP service, no separate process, no programmatic-pool billing.

The three scopes match three real project profiles:

- **`lite`** — quick PoCs and throwaway experiments. LLM-only review, no deterministic tools. Fast; minimal noise.
- **`standard`** — simple production projects. Security scanning (Semgrep, Bandit, gitleaks, Trivy) + code quality (Radon, vulture, jscpd, knip, ESLint+sonarjs) + LLM design review grounded by those findings. The default.
- **`full`** — complex brownfield projects. Everything in `standard` plus coupling/cohesion analysis (pydeps, dependency-cruiser, cohesion LCOM4) + contract testing (Schemathesis, Pact) at story boundaries. Accepts longer review time for deeper coverage.

The operator sets one config value (`review_scope`) in the SDLC skill's project-level config. They don't pick individual tools.

This replaces and simplifies the earlier `epic-reviewer-service` design (which extracted the same functionality into an HTTP service). The sub-agent shape keeps all the analyzer value while staying inside the operator's interactive Claude Code session.

## If/Then Hypothesis

**If we** extend the `reviewer` sub-agent with a deterministic analyzer layer whose depth is controlled by a single `review_scope` config (`lite` / `standard` / `full`), packaged as the `code-review` skill,

**for** the SDLC operator running the Review verb at per-task and story boundaries across projects that range from quick PoCs to complex brownfield codebases,

**then we will** give each project the right level of review rigor without per-tool configuration — `lite` stays fast for throwaway code, `standard` catches security and quality issues on production projects, and `full` adds coupling/cohesion and contract testing for complex multi-service codebases — while keeping the entire workflow inside the interactive Claude Code subscription pool.

## Why this is a hypothesis, not a commitment

Five assumptions could be wrong:

1. **That deterministic-layer + narrowed LLM design review beats LLM-only** at `standard` and `full` scope. Industry evidence (Sonar, OpenText, CASTLE benchmark) suggests yes. Worth measuring on this repo's actual diffs because the gain depends on rule-coverage match against this codebase's actual issues.
2. **That the sub-agent's turn budget can host both deterministic-result interpretation and design review** at `standard` and `full` scope without context exhaustion on large story-level diffs. The LLM call sits inside one turn alongside spec-reading and fix-task spawning. If story-level diffs grow beyond a turn's context budget, the design-review step may need to be a separate sub-agent dispatch.
3. **That SARIF (extended with `properties.sdlc_severity`) is the right canonical format** for the deterministic layer to hand to the sub-agent. The format fits findings well; if the SDLC workflow ends up needing decision-shaped output for the design step, the format may need supplementing.
4. **That every analyzer can run cleanly inside the operator's `/sandbox`-enabled Claude Code session** with only narrow, documented widening of `allowedDomains` (for contract-test targets at `full` scope) and no widening of `allowWrite`, `excludedCommands`, or `allowUnsandboxedCommands`. If any analyzer turns out to need broader privilege, we either find an alternative tool or accept a documented operator-side widening with an ADR.
5. **That three scopes (`lite` / `standard` / `full`) are the right granularity.** If operators find themselves frequently wanting "standard + dependency-cruiser but not cohesion," the coarse model breaks and we'd need a finer-grained selection. The bet is that the three natural project profiles (PoC, simple production, complex brownfield) absorb the meaningful variation and individual-tool selection would add configuration burden without proportional value.

s0 and s1 prove assumption 3 (the deterministic SARIF layer is usable). s1's `setup.sh` and `--capabilities` runtime check prove assumption 4 for the offline-prefetch path. s5 proves assumptions 1, 2, 4, and 5 end-to-end (all three scopes work against real diffs in a real sandboxed session). Assumption 5 is validated by operator experience across the three project profiles during the validation window.

## What's intentionally not in scope

These are deliberate non-goals, recorded here so they don't drift back in mid-epic:

- **No per-tool selection for the operator.** The operator picks a scope; the skill maps scopes to tool sets. If a future operator genuinely needs to add one tool to `standard` that's normally only in `full`, the config allows overrides via `code-review.toml`'s `[scope_overrides]` section — but the three scopes are the primary interface and the overrides are not promoted in the SKILL.md's quick-start section.
- **No HTTP service.** Earlier design (`epic-reviewer-service`) extracted analysis into a daemon. We're not doing that. Reasons: interactive-subscription billing model, simpler operational footprint, single-operator scale doesn't justify a service.
- **No async job queue, no workspace isolation, no result cache.** The sub-agent's turn is the unit of work; subprocesses run synchronously within it.
- **No unattended/CI invocation in this epic.** A future epic could add a thin CI wrapper that calls the same analyzer CLI, but that path uses the Agent SDK credit pool, not the interactive subscription. Not now.
- **No service-style capability discovery endpoints.** Capability declaration becomes static metadata in `capabilities.json` referenced from `SKILL.md` — useful for self-description and audit, not a runtime API.
- **No multi-tenant or multi-repo support.** Single operator, single repo per session.
- **No reliance on unsandboxed execution.** The skill must work under the operator's strict-sandbox configuration; analyzers that would require widening the sandbox beyond the documented `allowedDomains` for contract-test targets (at `full` scope) are out of scope and a future operator-approved ADR.
- **No SDLC-version check at runtime.** The architecture depends on the SDLC contract surface enumerated in the architecture's §17, treated as stable by convention. There is no parser, no compatibility range, no refusal-to-load on unknown SDLC versions.

## Tiny Acts of Discovery Experiments

**We will test our assumption by:**

- Building the s0 analyzer façade with Semgrep + Radon adapters, and exercising it via the CLI (`python -m code_review.cli --review-scope standard --scope per-task --diff <ref>`) against a fixture diff with known issues. Confirms the SARIF shape is usable before any sub-agent integration.
- Wiring the skill's `capabilities.json` and the `reviewer` sub-agent to read the `review_scope` config and select the correct analyzer set (s1 + s5). Confirms the scope-to-tool mapping works without the operator touching individual tools.
- Running the consolidated analyzer set at `standard` scope against 10 recent task diffs from this repo and recording per-axis findings. Compare against `lite` scope (LLM-only, same as the current reviewer's output) on the same diffs.
- Manually running a per-task review at `standard` scope on a fixture diff containing a planted design issue (e.g., function named `process_data` that handles authentication) that no deterministic rule will catch. Confirms the LLM design step still surfaces issues that rules can't, with the deterministic context successfully suppressing duplicate findings.
- Running one full per-task close end-to-end at `standard` scope (deterministic + LLM design + fix-task spawning per rule #25) on a real task in this repo. Confirms the SDLC auto-remediation loop still closes correctly.
- Running one story-level review at `full` scope on a fixture with planned inter-service spec drift. Confirms Schemathesis / Pact contract testing fires at story boundaries but not at per-task timing.

## Validation Measures

**We know our hypothesis is valid if within 3 weeks** of s0–s5 shipping **we observe:**

- **Finding overlap (`standard` scope):** ≥ 70% of `lite`-scope findings on the 10-diff comparison sample are also produced by the deterministic layer, confirming that the rule-based tools cover what the LLM was previously redoing (quantitative).
- **Precision on design findings:** for findings the LLM design step surfaces that the deterministic layer does *not* (at `standard` scope), operator agreement is ≥ 70% (quantitative). The LLM's narrowed scope should improve hit rate vs. `lite`-scope baseline.
- **Context budget headroom:** on the largest story-level diff the loop encounters during the validation window (at `full` scope), the sub-agent's turn completes the deterministic-result interpretation + design review + fix-task spawning without running into context-window pressure (qualitative; observable from turn metadata).
- **Workflow stability:** the SDLC's rule #25 2-round remediation bound, the `-fix<N>-` naming convention, and the per-task vs. story-level distinction all work unchanged at every scope (qualitative — no `/sdlc/SDLC.md` text changes required to integrate).
- **Subscription pool only:** zero Agent SDK credit consumption attributed to Reviewer work during the validation window at any scope (quantitative). All LLM calls happen inside the operator's interactive Claude Code session.
- **Sandbox-clean operation:** every per-task review at every scope during the validation window completes in a `/sandbox`-enabled session with strict settings (`failIfUnavailable: true`, `allowUnsandboxedCommands: false`) without prompting the operator for additional widening and without any `dangerouslyDisableSandbox` retry (quantitative — instrumented in CI's sandbox-compatibility test).
- **`lite` scope fidelity:** `lite` scope produces output functionally equivalent to the current SDLC reviewer's output — same review quality, same speed, no unexpected deterministic findings (qualitative — confirms that `lite` is a genuine no-change path for PoC projects).
- **Scope switch is instant:** an operator can change `review_scope` from `lite` to `standard` to `full` (and back) by editing the SDLC skill's config, with no other action, and observe the corresponding analyzer set on the next Review dispatch (qualitative).

**We know the hypothesis is invalidated if:**

- Finding overlap is < 30% (the deterministic layer isn't catching what the LLM was catching, so layering doesn't help).
- The sub-agent's turn runs out of context on routine story-level diffs at `standard` scope (assumption 2 fails — design review needs its own dispatch even for the common case).
- The SDLC's workflow text requires changes to accommodate the scope-based output (assumption 5 fails — the abstraction is wrong).
- Any analyzer turns out to require sandbox widening beyond the contract-test `allowedDomains` entries documented in `SKILL.md` (assumption 4 fails — we need either a different tool or an operator-approved ADR).
- Operators consistently override the scope-to-tool mapping for individual projects (assumption 5 fails — three scopes aren't the right granularity and we need finer control).

## Stories

Sequenced for build order. Each story is independently mergeable. Epic does not close until s0–s5 are all done; there's no minimum-viable subset because the value only lands once the sub-agent actually uses the analyzers.

0. **s0-analyzer-facade-and-two-adapters** — Define the `Analyzer` Protocol and canonical SARIF / MetricSet types. Ship Semgrep and Radon adapters as reference implementations. Ship a CLI (`python -m code_review.cli`) that runs configured analyzers against a diff and emits consolidated JSON. CLI accepts `--review-scope` to select the analyzer set. No sub-agent integration yet. *Prerequisite for everything else.*

1. **s1-reviewer-skill-and-capabilities** — Package the analyzer code as a Claude Code skill at `.claude/skills/code-review/`. Includes `SKILL.md`, `capabilities.json` (review kinds, stack coverage, taxonomies, analyzer registry, scope-to-analyzer mapping), JSON Schemas for request/response shapes, the CLI entry point the sub-agent will invoke, and a `setup.sh` that handles offline cache pre-fetch. Skill is loadable but not yet wired into the `reviewer` sub-agent.

2. **s2-aggregator-and-severity-mapping** — SARIF deduplication by `(file, line, ruleId-family / CWE)`. Severity mapping from SARIF `level` + `properties.severity` into the SDLC's Critical / Important / Minor / Nit taxonomy (lines 166–169 of SDLC.md). Ranked-hotspots output for the sub-agent's auto-remediation step.

3. **s3-remaining-deterministic-adapters** — Bandit, gitleaks, Trivy, jscpd, vulture, knip, dependency-cruiser, ESLint+sonarjs, pydeps, cohesion. SARIF normalisation shims for tools whose native output isn't SARIF. Each new adapter appears in the skill's `capabilities.json` analyzer registry and is assigned to one or more review scopes.

4. **s4-contract-testing-adapters** — Schemathesis (schema-driven, runs against a live API) and Pact (consumer-driven, broker-published). Story-level scope only, longer timeout budgets. Assigned to `full` review scope. Scope restrictions declared in `capabilities.json`.

5. **s5-subagent-integration-and-design-review** — Update `.claude/agents/reviewer.md` to read the SDLC skill's `review_scope` config, invoke the `code-review` skill's CLI with the appropriate scope, then perform LLM design review as part of its own turn using the deterministic SARIF as grounding context. At `lite` scope, the sub-agent skips the CLI and does LLM-only review (matching the current behaviour). Includes the prompt structure for design review, the "do not duplicate deterministic findings" instruction, and the fix-task spawning per rule #25. This is where the hypothesis is actually tested end-to-end.

## Convert-to-stories note

Stories sit alongside this epic in `/sdlc/work/active/` and follow the `s<N>-<slug>` naming convention per SDLC file conventions (line 80). Tasks under each story carry `s<N>-t<M>-<slug>` ids and are not pre-drafted — task decomposition happens at Plan time per the SDLC's Plan verb.

## Relationship to the older epic-reviewer-service draft

A prior version of this work was framed as an HTTP service (`epic-reviewer-service` with eight stories s0–s8, including FastAPI, async job queue, capability endpoints, observability spans). That design was rejected in favour of this sub-agent approach for three reasons:

1. The Agent SDK billing change (effective June 15, 2026) makes programmatic Claude Code use draw from a separate credit pool at API rates, undermining the "use the subscription" goal.
2. The single-operator interactive workflow doesn't justify the operational complexity of a service.
3. The SDLC's existing sub-agent pattern is the natural home for review logic.

The older epic file is preserved for context; the deterministic-analyzer engineering work (s0, s2–s4 here) is substantially the same — only the transport changed from HTTP to direct CLI invocation by the sub-agent.
