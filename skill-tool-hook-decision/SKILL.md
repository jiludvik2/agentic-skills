---
name: skill-tool-hook-decision
description: Use this skill whenever the user is deciding how to implement an agent capability or business requirement in Claude Code, Microsoft Agent Framework, or any agentic AI system — choosing between a prompt-driven skill, code-driven skill, tool (including MCP), or hook/middleware. Triggers include questions like "should this be a skill or a tool?", "how should I architect this?", "where does this belong?", "skill vs MCP", "should this run as a hook?", or any time the user is designing a new agent capability, refactoring an existing one, packaging an MCP server, or auditing an architectural decision. Use proactively whenever the user mentions agent design, SKILL.md, MCP server design, hooks, function calling, or framework-level component choices, even if they don't explicitly ask for help choosing. Returns a structured verdict naming the primary component type, the composition pattern if multiple components are needed, the rationale grounded in criteria, and any anti-patterns the design risks falling into.
---

# Skill / Tool / Hook Decision

A documented decision tree for choosing the right component type when realising a requirement on Claude Code, Microsoft Agent Framework, or any agentic AI system.

The output is a recommendation, not a prescription. Surface the trade-offs honestly so the user can override with project-specific knowledge they have and you don't.

## When to use

Reach for this skill whenever the user is:

- Designing a new agent capability and asking what kind of component it should be.
- Refactoring an existing capability and questioning its current shape (e.g. moving logic from a prompt-skill into a tool).
- Packaging a script, prompt, or service as an MCP tool, hook, or skill.
- Auditing an architectural decision against standard criteria.

The skill is most useful when the requirement has any of: regulatory implications, side effects on external systems, judgement that must be defensible, cross-team or cross-BU reuse, or significant invocation volume. For trivially obvious cases ("read this file") skip the tree and answer directly.

## Procedure

### Step 1 — Capture the requirement

Restate the requirement in one sentence with a single verb ("approve a credit-limit increase", "summarise overnight bulletins"). If the user gave a multi-step requirement, identify the sub-operations and route each one separately — composition is the norm, not the exception.

If important context is missing, ask one or two short clarifying questions before walking the tree. Things that flip the answer and should not be silently defaulted:

- Is this on the critical path of a regulated decision (credit, clinical, sanctions, legal)?
- What's the expected volume per day?
- Is the output consumed by downstream code (typed) or by a human (prose)?
- Does the user need a single agent or cross-team / cross-BU reuse?

### Step 2 — Walk the decision tree

Read `references/decision-tree.md` and walk Tree A from Q1. Stop at the first match. Show the user which questions you answered and how — the walkthrough is part of the value, not just the destination.

### Step 3 — Apply the cross-cutting guardrails

Read `references/guardrails.md` and check the four guardrails (cost, compliance, vendor portability, latency SLO). Each can override or qualify the Tree A answer. Do not skip this step.

### Step 4 — Identify the composition

Read `references/composition-patterns.md`. If the requirement needs more than one component — and it usually does — name the pattern (Skill+Tool, Tool wrapping LLM, Hook+Tool, Code-skill+Tool, Subagent, Skill stack) explicitly.

### Step 5 — Flag anti-patterns

Read `references/anti-patterns.md`. If the natural-sounding answer matches a known anti-pattern (e.g. "use a SKILL.md to call this curl" → *Skill for an external API*), name it. If the user has proposed a design, audit their proposal against the anti-pattern list, not just the tree-derived answer.

### Step 6 — Return the structured verdict

Use the format in `references/output-template.md`. Be concise — the verdict should fit on one screen.

## Output format

Always use this exact structure (sections may be omitted if truly N/A):

```
## Recommendation
**Primary component:** <prompt-driven skill | code-driven skill | tool | hook/middleware>
**Composition pattern:** <Skill+Tool | Tool wrapping LLM | Hook+Tool | Code-skill+Tool | Subagent+parent | Skill stack | none>

## Tree A walkthrough
- Q1 <short form>: <Yes/No> → <next or "stop">
- (continue only with the questions you actually answered)

## Rationale
<1–3 sentences naming the criteria from references/criteria.md that drove the answer>

## Composition detail
<Which other components are needed and why; omit if single-component>

## Watch-outs
- <anti-pattern flagged or design risk>

## Guardrails
- Cost: <note or "n/a">
- Compliance: <note or "n/a">
- Portability: <note or "n/a">
- Latency SLO: <note or "n/a">
```

If the answer is genuinely obvious and the framework would add no value (e.g. "should I read a file with the Read tool?"), say so plainly and skip the template.

## Reference files

Load these on demand — don't read them all up front.

| File | When to read |
|---|---|
| `references/decision-tree.md` | Always — Tree A is the core procedure |
| `references/criteria.md` | When citing a criterion in the Rationale |
| `references/composition-patterns.md` | Always when the requirement has more than one sub-operation |
| `references/anti-patterns.md` | Always — audit the answer (and any user proposal) against this |
| `references/nfr-matrix.md` | When the user asks "why this type and not that one?" — this is the comparative answer |
| `references/guardrails.md` | Always — these can override the Tree A answer |
| `references/output-template.md` | Reference only when you need the exact format |

## A worked example

**Requirement:** "We need to approve credit-limit increases for retail customers per our internal policy v3.2."

- Q1 Cross-cutting policy concern? **No** — this is a domain decision, not a runtime guardrail.
- Q2 External system / state mutation? **Yes** — the decision writes to the credit system and notifies the customer. → **Tool**. Stop.

Guardrails: Compliance — this is a regulated decision, so prompt-skill is forbidden on the critical path. Confirms Tool with a deterministic backend.

Composition: Hook+Tool (audit hook for dual-control sign-off) + Tool (customer notification).

Anti-pattern check: A naive answer might propose a *credit-policy skill* with the rules in markdown — that would be *Prompt-driven calculation* (and likely a regulator finding). Avoid.

Verdict: **Tool** (deterministic policy engine), composed with a **Hook** (audit + dual control) and a **Tool** (notification).

## Common watch-outs

- **Defensibility ≠ regulated decision.** A judgement surfaced to a human for action (e.g. "next-best-action suggestion") often still needs typed reasoning and audit. Route to *Tool wrapping LLM*, not prompt-skill, when downstream code or compliance reviewers consume the output.
- **Cross-BU is not automatically prompt-skill.** High-volume cross-BU judgement is often better as *Tool wrapping LLM* — typed, observable, versionable.
- **Wrapping the LLM doesn't always mean a Tool.** Q6's "Yes" branch can land on a *Code-skill wrapping LLM* when the capability is single-agent, has no external invocation need, and doesn't need an independent release lifecycle. The typing is what matters; the packaging follows Q4's reuse logic.
- **Code-skill vs Tool.** The four-factor test in Q4 (dependency footprint, latency budget, external invocation need, independent versioning) decides this. Lines-of-code is not a useful proxy.
- **Reusable policy logic does not belong inside a hook.** PII redaction, sanctions screening, content moderation, suitability checks — these are reusable business capabilities. The *Tool* holds the policy logic; a thin per-platform *Hook* invokes it. That's the *Hook-invoked Tool* composition. Burying the same logic inside a hook locks it to one platform and forces re-implementation elsewhere.
- **"Just put it in the prompt" for policy.** Anti-pattern. Policies that must run on every call belong as a Tool invoked by a Hook, not in instructions.

## Stay in scope

This skill chooses a **component type** and a **composition pattern**. It is not the place to recommend specific libraries (e.g. Azure Document Intelligence vs LlamaParse), specific model variants, vendor selection, or internal implementation details of the chosen component. Those are downstream decisions for the team that owns the component. Mentioning them as part of a routing verdict is the *Implementation-detail leakage* anti-pattern — it invites debate about the wrong question and dilutes the framework's value. If the user explicitly asks for implementation guidance, treat it as a separate conversation.

## Why this skill exists

Without it, architects default to whatever component type they happen to know best — and the result is mega-skills doing arithmetic, prompt-skills calling external APIs, policies hidden inside prose, and regulated decisions quietly depending on LLM judgement. The framework's value is consistency: same requirement type → same answer, with the rationale on the record.
