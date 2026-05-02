# Decision Framework: Skills, Code-Skills, Tools, and Hooks

*A concise architectural reference for Claude Code and Microsoft Agent Framework 1.0*

**Audience:** Enterprise AI architects, agent developers, DevOps / platform engineers, governance leads.
**Status:** Reference v1.2 · May 2026 (see §12 Changelog for revision history)

---

## 1. Purpose and Scope

This document gives architects a single-page mental model for choosing how to realise a business requirement in an agentic AI ecosystem built on Claude Code (Anthropic) and/or Microsoft Agent Framework 1.0 (Microsoft, GA April 2026). It answers:

- Which **component type** should each requirement use: prompt-driven skill, code-driven skill, tool, or hook / middleware?
- How should those components **compose** when more than one is needed?

Three organisational constraints are baked in: regulatory **auditability**, cross-business-unit **reusability**, and **token-cost / latency** efficiency. Two operational constraints are added in v1.1: **observability** and **blast radius of change**.

> **Composition mindset.** Components are *complementary*, not alternatives. Most production capabilities are a skill that calls one or more tools, optionally guarded by a hook. The decision tree below chooses a *primary* type per sub-operation; §6 covers composition patterns.

---

## 2. Terminology Mapping

| Concept | Claude Code / Claude Agent SDK | Microsoft Agent Framework 1.0 |
|---|---|---|
| **Prompt-driven skill** | `SKILL.md` (instructions, examples, references). Loaded by description match. | Skill — instructions + reference material. Discovered by skills provider. |
| **Code-driven skill** | `SKILL.md` plus bundled scripts the model invokes via Bash. Script source never enters context. | Skill that bundles executable scripts called from instructions. Same `SKILL.md` convention. |
| **Tool** | Built-in tool (Read/Edit/Bash) or MCP server function with name + JSON schema. | Tool — single typed callable. Native function or MCP-discovered endpoint. |
| **Hook / middleware** | Pre/post tool-use hooks; deterministic interception in the agent loop. | Middleware, content filters, function-invocation filters. |
| **Subagent** | `Task` tool invocations with isolated context windows. | Agent-as-tool, multi-agent workflows. |
| **Selection mechanism** | Description-based lazy load by the agent loop. | Skills provider context provider; tool calling via function-call API. |

---

## 3. Component Types

**Prompt-driven skill.** Natural-language instructions injected into the model's context when triggered. The model interprets and executes. Behaviour is *probabilistic*; output varies with phrasing, sampling, and context length. Strongest fit: judgement, synthesis, classification with fuzzy criteria, natural-language generation.

**Code-driven skill.** A skill whose instructions delegate critical work to bundled scripts. The script runs deterministically; only its output is loaded into context. Combines model judgement (when to call) with code reliability (how it runs). Strongest fit: bounded-dependency utilities that don't need to be invoked from outside the agent.

**Tool.** A typed callable with name, JSON-schema parameters, and description. The model decides when to call; the runtime guarantees how it runs. Strongest fit: external systems, shared utilities, high-volume deterministic operations, schema-constrained outputs (function-calling), anything needing first-class observability and IAM.

**Hook / middleware.** Deterministic code that runs *around* the agent loop or tool calls — before/after tool use, on token streams, on context window changes. The model does not "decide" to invoke a hook; the runtime does. Strongest fit: policy enforcement, redaction, audit logging, rate limiting, prompt-injection defence, content moderation.

**Subagent.** A spawned agent with its own context window. Reach for it when a sub-task is large enough to bloat the parent's context, or needs an independent system prompt / toolset. Cost = extra LLM round-trip; benefit = context isolation and parallelism.

> **The hybrid pattern.** A *tool that internally calls an LLM with a JSON schema* (function-calling / structured output) is a first-class option that the v1.0 tree missed. Use it when you want LLM judgement with code-grade interface guarantees: typed input, typed output, observable, versionable.

---

## 4. Decision Criteria

Apply these in order; criteria #1–#4 usually determine the answer.

| # | Criterion | What to ask |
|---|---|---|
| 1 | **Determinism required** | Same input → same output? Temperature=0 is *not* determinism — only code is. |
| 2 | **Side effects / state mutation** | Does it write, send, charge, or otherwise change state? Mutating ops need idempotency, retries, audit — almost always tools or hooks. |
| 3 | **Operation nature** | Judgement / synthesis (LLM-shaped) vs transformation / computation (code-shaped) vs external interaction (tool-shaped) vs cross-cutting policy (hook-shaped). |
| 4 | **Auditability & blast radius** | Must each invocation be replayable and signed-off? How wide is the blast radius if the component misbehaves? |
| 5 | **Reuse scope** | Single workflow, single agent, multiple agents, or cross-BU? Wider reuse → typed tool with versioning. |
| 6 | **Observability budget** | What traces / metrics / logs do you need? Tools come with first-class observability; prompt-skills require LLM-trace tooling. |
| 7 | **Security surface** | Prompt-injection exposure, secret handling, IAM scopes, data residency. Mutating-on-untrusted-input → tool guarded by hook. |
| 8 | **Token cost / latency / SLO** | Volume × token cost. Synchronous user-facing path? Prompt-skill latency is variable; tool latency is bounded. |
| 9 | **Invocation pattern** | Always-needed (default-loaded tool) vs conditionally needed (lazy-loaded skill) vs runtime-injected (hook). |
| 10 | **Implementation & ops complexity** | Prompt engineering ≪ bundled script ≪ packaged MCP server ≪ middleware in the agent runtime. Pick the cheapest mechanism that satisfies #1–#7. |

---

## 5. Decision Tree — Choosing the Primary Component Type

Walk top to bottom. Stop at the first match that fits the *primary* responsibility (composition still applies — see §6).

### Q1. Is this a cross-cutting policy concern (auth, redaction, audit, rate-limit, prompt-injection defence, content moderation)?

- **Yes →** **Hook / middleware.** Implement once, attach to all relevant tools or the agent loop. Deterministic by definition. **Stop.**
- **No →** Continue to Q2.

### Q2. Does the operation interact with an external system (network, DB, SaaS, persistent storage, message bus) or otherwise mutate shared state?

- **Yes →** **Tool.** Local function for in-process work, MCP server for cross-agent / cross-language reuse. Tools own auth, retries, observability, idempotency, versioning. **Stop.**
- **No →** Continue to Q3.

### Q3. Does the requirement demand deterministic, repeatable output and / or full audit traceability?

- **Yes →** Continue to Q4 (a prompt-driven skill is disqualified).
- **No →** Skip to Q5.

### Q4. Does the deterministic logic meet **all** of: (a) bounded dependency footprint that fits the agent runtime, (b) execution within the agent's per-call latency budget, (c) no need for invocation from outside the agent, (d) no need for independent versioning / release lifecycle?

- **All yes →** **Code-driven skill.** Bundle the script with a `SKILL.md`. Script output enters context, source does not — cheap on tokens, deterministic, locally auditable.
- **Any no →** **Tool**, exposed via MCP. Packaging as a server gives observability, scaling, dependency isolation, independent release lifecycle, and reuse across agents and languages.

### Q5. Does the requirement involve judgement, synthesis, classification with fuzzy criteria, or natural-language production?

- **Yes →** Continue to Q6.
- **No →** Reconsider — most non-judgement operations belong in Q1, Q2, or Q4. Avoid prompt-driven skills for arithmetic, parsing, format conversion, or rule lookups.

### Q6. Does the consumer need a **typed, machine-parsable result** (downstream code branches on the output)?

- **Yes →** **Tool with structured-output LLM call inside** (function-calling / response-format). You get LLM judgement *and* contract-grade interface, observability, and versioning.
- **No →** Continue to Q7.

### Q7. Will multiple agents or business units rely on this judgement?

- **Yes →** **Prompt-driven skill** published to the shared skill registry. Invest in a tight, disambiguating description so lazy loading triggers correctly.
- **No →** Inline the prompt in the agent system prompt, or keep a local prompt-driven skill scoped to that agent.

### Cross-cutting guardrails (apply after Q1–Q7)

- **Cost.** If the component will run >100×/day at production volume, prefer code-skill or tool over prompt-skill; consider a hook for policies the prompt-skill keeps re-explaining.
- **Compliance.** Regulated decisions (credit, clinical, sanctions, legal) may not depend on a prompt-driven skill on the critical path. Prompt-skills are acceptable for human-in-the-loop drafting only.
- **Vendor portability.** Cross-platform requirements (Claude + MS Agent Framework) are best served by MCP tools and `SKILL.md` skills, both of which are supported by both ecosystems. Hooks/middleware are platform-specific — abstract behind a tool when portability matters.
- **Latency SLO.** Synchronous user-facing path with tight SLO → avoid prompt-skill on the critical path; use a tool (function-calling LLM if judgement needed) so latency is bounded and measurable.

---

## 6. Composition Patterns

Most useful capabilities combine multiple types. Reach for these patterns by name; resist mono-component designs.

| Pattern | Shape | When to use |
|---|---|---|
| **Skill + Tool** | Prompt-skill instructs the model when/how to call a domain tool. | Cross-BU judgement that needs to act (e.g. "draft and post a Jira update"). |
| **Tool wrapping LLM (function-calling)** | Tool whose internals call an LLM with a JSON-schema response format. | Typed extraction, classification, routing — when callers need a parseable object. |
| **Code-skill + Tool** | Code-skill orchestrates deterministic steps and calls tools at well-defined points. | Multi-step workflows with auditable orchestration (e.g. month-end close). |
| **Hook + Tool** | Pre-tool hook enforces policy (PII redact, scope check); tool executes. | Any tool touching customer data, money, or external systems. |
| **Subagent + parent toolset** | Parent spawns a focused subagent with a narrow tool budget for a long task. | Research-style tasks; jobs that would bloat the parent's context. |
| **Skill stack** | Lightweight "meta-skill" describes when to load several specific skills. | Domain entry-points that branch into specialised judgement paths. |

---

## 7. Non-Functional Concerns Matrix

The single biggest gap in v1.0 was treating cost as the only non-functional axis. Use this matrix to weigh the rest before committing.

| Concern | Prompt-skill | Code-skill | Tool (incl. MCP) | Hook / middleware |
|---|---|---|---|---|
| **Determinism** | Probabilistic | Deterministic | Deterministic interface; behaviour depends on backend | Deterministic |
| **Observability** | Hard — needs LLM trace tooling, prompt diffs | Medium — stdout/stderr, can wrap with logging | Strong — native metrics, structured logs, distributed tracing | Strong — runs in agent runtime with telemetry |
| **Security surface** | Prompt-injection, instruction subversion | Sandbox-bounded; supply-chain risk in deps | IAM/OAuth scopes, secret store, network policy | Last line of defence — redaction, scope check |
| **Blast radius of change** | Wide, silent — affects every agent that loads it | Bounded to the script; versioned with the skill | Bounded by schema; semver + contract tests catch breaks | Wide — applies to every call it intercepts |
| **Latency profile** | Token-bound, variable; degrades on long context | Bounded by script runtime | Bounded by backend; timeouts enforceable | Microseconds to low ms; on every call |
| **Token cost** | Full skill text in context per session | Output only enters context | Schema only enters context | None to the model (runtime-side) |
| **Data residency** | Always sends data to the model | Local processing | Depends on tool deployment region | Local to the runtime |
| **Testability** | LLM-as-judge eval suites; flaky | Unit tests | Unit + contract + integration tests | Unit tests; replay tests on captured traces |
| **Versioning model** | Skill description + body, no semver convention | Versioned with the skill bundle | Semver + schema versioning | Versioned with the agent runtime / plugin |

---

## 8. Lifecycle and Ops

Each component type needs a different CI/CD and runtime story. Bake these into the platform up front.

**Prompt-driven skill**
- *CI gate:* description-trigger eval (does the right skill load on representative prompts?), prompt-injection adversarial suite, regression eval against a labelled task set.
- *Rollout:* canary on a shadow agent; A/B vs current; rollback = revert SKILL.md.
- *Runtime:* capture full prompt + response traces; alert on description drift (load rate spikes/drops).
- *Owner:* product / domain SME with prompt-engineering review.

**Code-driven skill**
- *CI gate:* unit tests on bundled scripts, dependency vulnerability scan, SBOM, lint.
- *Rollout:* version-pinned in skill bundle; rollback = previous bundle version.
- *Runtime:* structured logging from script; capture stdout/stderr in agent telemetry.
- *Owner:* engineering team owning the skill repo.

**Tool / MCP server**
- *CI gate:* schema validation (JSON-schema lint), unit + contract + integration tests, auth scope review, image scan, performance budget.
- *Rollout:* semver; backward-compatible schema changes only on minor; deprecation window for breaking changes; canary deployment + traffic shift.
- *Runtime:* RED metrics (rate/errors/duration), distributed tracing, error budget, SLOs; tool-level kill switch.
- *Owner:* platform / service team with on-call rotation.

**Hook / middleware**
- *CI gate:* unit tests, replay tests against captured production traces, performance regression test (hooks run on every call).
- *Rollout:* feature-flagged; staged enablement; circuit-breaker on hook errors.
- *Runtime:* metric per hook (invocations, denials, errors), opt-out controls per agent.
- *Owner:* platform / security team.

**Cross-cutting**
- *Registry:* every shared component has owner, version, changelog, SLA, and a runbook URL in the registry entry.
- *Incident response:* skill misbehaving at 3am → kill switch (disable skill description from registry) → rollback prior version → post-incident eval added to CI suite.
- *Model-version drift:* prompt-skills are coupled to the underlying model; pin the model in the agent config and run the regression suite on model upgrades.

---

## 9. Anti-patterns

- **The mega-skill.** A 2,000-line `SKILL.md` doing six unrelated jobs. Lazy-loading misfires and context bloats. Split by responsibility.
- **Prompt-driven calculation.** Using LLM judgement for arithmetic, parsing, validation, format conversion, hashing, IBAN checks. Move to code.
- **Skill for an external API.** Telling the model in markdown to "run this curl". Loses retries, auth secrets, observability, rate limits, idempotency. Use a tool.
- **Description leakage.** Vague skill descriptions trigger spurious or missed loads. Treat the description as a public API; review it.
- **Determinism via temperature=0.** Sampling reduction is not reproducibility. If reproducibility matters, the operation belongs in code.
- **Hidden cross-component dependencies.** Skill A silently assumes skill B is loaded, or assumes a tool is available. Document in the description, or merge.
- **Untyped LLM extraction.** Returning free-form JSON-in-prose to a downstream parser. Use function-calling / structured output via a tool.
- **Policy in the prompt.** "Remember to redact PII before posting" inside a SKILL.md. Move to a hook so it runs deterministically and is testable.
- **No kill switch.** Skill or tool with no runtime way to disable it without a deployment. Build the kill switch in v0.
- **Model-version drift unmanaged.** Prompt-skill behaviour shifts when the underlying model upgrades. Pin the model and re-run the eval suite on changes.
- **Hook bloat.** Hooks that do business logic, not policy. Hooks should be cheap and orthogonal; push logic into the tool or skill it intercepts.

> *Removed from v1.0:* "Tool for a true one-off." On reflection this anti-pattern was wrong: a one-off internal tool is fine when ops needs the observability and kill-switch story. The cost is mostly initial scaffolding, which can be templated.

---

## 10. Quick-Reference Matrix

| Requirement (illustrative) | Build it as… |
|---|---|
| Summarise an email thread or meeting transcript | Prompt-driven skill |
| Generate a Word memo from an outline | Code-driven skill (bundled docx scripts) |
| Look up a customer in Salesforce / Dynamics | Tool (MCP) |
| Validate IBAN, parse a date, hash a string | Code-driven skill — or shared utility tool if cross-BU |
| Decide which of five reply templates fits this ticket | **Tool wrapping LLM** (typed enum result) — not a prompt-skill |
| Approve a $50k expense per policy XYZ | Tool (deterministic policy engine), guarded by audit hook |
| Draft a status update from Jira tickets | Prompt-driven skill + Jira tool |
| Compute month-end FX P&L | Code-driven skill or tool — must be deterministic and auditable |
| Produce a chart from a CSV | Code-driven skill (matplotlib / chart lib) |
| Triage incoming support tickets by topic and urgency | **Tool wrapping LLM** for classification + ticketing tool for action |
| Redact PII from anything posted to external systems | **Hook / middleware** on outbound tool calls |
| Enforce per-tenant rate limits on tool use | **Hook / middleware** |
| Long-running multi-source research on a market | **Subagent** with a narrow tool budget |
| Extract structured invoice data from a PDF | **Tool wrapping LLM** with JSON schema (or PDF-skill + structured-output tool) |

---

## 11. Governance Notes

- **Registry.** Cross-BU reusable components belong in an internal MCP / skill registry with owner, schema/description, version, SLA, runbook URL, and changelog.
- **Regulated workflows.** Mandate code-driven skills, tools, or hooks on the critical path. Document the deterministic execution path; retain inputs and outputs for the regulator's retention period; require an attached audit hook.
- **Cost telemetry.** Track invocations × tokens per skill and tool. Any prompt-driven skill exceeding a defined threshold (e.g. >100 calls/day) enters a refactor queue; candidate target is usually a tool wrapping a structured-output LLM call.
- **Description review.** Treat skill descriptions and tool schemas as public contracts; review them in the same PR template as code.
- **Portability.** Where the same capability is required on Claude Code and MS Agent Framework, prefer the `SKILL.md` + MCP idiom; both ecosystems consume it natively. Hooks/middleware require platform-specific implementation behind a portable abstraction.
- **Model-version policy.** Pin the model in the agent config; gate model upgrades on a regression eval suite covering all prompt-driven skills.
- **Kill switch policy.** Every shared skill, tool, and hook has a runtime-disable mechanism that does *not* require redeployment.

---

## 12. Changelog

### v1.1 → v1.2

- **Removed §6 Decision Tree B (Single Component, or Several?).** Granularity is now handled implicitly by Tree A (which already chooses a primary type per sub-operation) and §6 Composition Patterns (which names the recurring multi-component shapes). The explicit Tree B was redundant once composition was made first-class.
- Renumbered §7–§14 down by one. Cross-references updated in §1, §3, and §5.

### v1.0 → v1.1

The v1.1 review added the dev / DevOps lens that was missing in v1.0.

**Added**

- §3, §5: **Hook / middleware** as a fourth component type (deterministic interception). Covers the policy / redaction / rate-limit class previously force-fit into prompt-skills.
- §3: **Subagent** acknowledged as a composition primitive.
- §3, §5 Q6, §10: **Tool wrapping LLM (function-calling / structured output)** as a first-class hybrid pattern.
- §6: **Composition Patterns** — six named patterns. Replaces the implicit "or" framing with an explicit "and" framing.
- §7: **Non-Functional Concerns Matrix** — observability, security surface, blast radius, latency profile, data residency, testability, versioning per type.
- §8: **Lifecycle and Ops** — CI gates, rollout, runtime, ownership for each type; cross-cutting registry / incident-response / model-drift policy.
- §4: New criteria #2 (side effects), #6 (observability), #7 (security), and revised #8 to include SLO.
- §9: New anti-patterns — Untyped LLM extraction, Policy in the prompt, No kill switch, Model-version drift unmanaged, Hook bloat.

**Changed**

- §5 Q4 (was Q3): replaced the "~200 lines" heuristic with a four-factor test (dependency footprint, latency, external invocation need, independent versioning). The previous heuristic conflated code size with deployment boundary.
- §5 Q7 (was Q5): added Q6 first to route typed-output cases to a tool with structured output, instead of always defaulting cross-BU judgement to a prompt-skill.
- §9: removed "Tool for a true one-off" — the previous anti-pattern was wrong.

**Reframed**

- Components are *complementary*, not alternatives. Tree A chooses a *primary* type per sub-operation; §6 covers composition.
- Cost is no longer the only non-functional axis (see §7).

---

## 13. Sources

- Anthropic — *Equipping agents for the real world with Agent Skills* (anthropic.com/engineering).
- Anthropic — *Claude Code: Hooks, Subagents, and Skills* (Claude Code documentation).
- Claude API Docs — *Agent Skills overview* (platform.claude.com/docs).
- Microsoft Learn — *Agent Skills*, *Microsoft Agent Framework* (learn.microsoft.com/agent-framework).
- Microsoft DevBlogs — *Microsoft Agent Framework Version 1.0* (devblogs.microsoft.com/agent-framework, Apr 2026).
- Microsoft Learn — *Middleware and function-invocation filters in Agent Framework*.
- Towards Data Science — *How to Build a Production-Ready Claude Code Skill*.
- Anthropic *Best Practices for Claude Code* (code.claude.com/docs/en/best-practices).
- OWASP — *LLM Applications Top 10* (prompt injection, supply chain).
