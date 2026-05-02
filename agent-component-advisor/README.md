# agent-component-advisor

A Claude Code skill for choosing the right component type when realising a business requirement on Claude Code, Microsoft Agent Framework, or any agentic AI system. Walks a documented decision tree (Tree A) and returns a structured verdict naming the primary component type, the composition pattern, the rationale grounded in named criteria, and any anti-patterns the design risks falling into.

## What this skill does

When you describe an agent capability or business requirement, the skill walks the decision tree and returns:

- **Primary component:** prompt-driven skill, code-driven skill, tool (incl. MCP), or hook / middleware.
- **Composition pattern:** Skill+Tool, Tool wrapping LLM, Code-skill wrapping LLM, Hook-invoked Tool, Hook+Tool, Code-skill+Tool, Subagent+parent, or Skill stack.
- **Walkthrough:** which tree questions you answered and how — the path matters as much as the answer.
- **Rationale:** the 1–10 criteria that drove the choice (determinism, side effects, audit, reuse, observability, security, cost, etc.).
- **Watch-outs:** anti-patterns the design risks (Mega-skill, Prompt-driven calculation, Reusable policy buried in a hook, Untyped LLM extraction, Implementation-detail leakage, ...).
- **Guardrails:** cost, compliance, vendor portability, latency SLO — each can override the tree.

The skill **chooses a type and composition**. It deliberately does not prescribe specific libraries, model variants, vendors, or internal implementation mechanics — those are downstream decisions for the team that owns the component.

## When it triggers

Reach for it whenever you're:

- Designing a new agent capability and asking what kind of component it should be.
- Refactoring an existing capability and questioning its current shape (e.g. moving logic from a prompt-skill into a tool).
- Packaging a script, prompt, or service as an MCP tool, hook, or skill.
- Auditing an architectural decision against standard criteria.

The description is "pushy" by design — it triggers on questions like "should this be a skill or a tool?", "where does this belong?", "skill vs MCP", "should this run as a hook?", and on any mention of agent design, SKILL.md, MCP server design, hooks, or function calling.

It deliberately does **not** trigger for trivial cases ("read this file with the Read tool"). For those, the skill says so plainly and skips the template.

## Installation

Drop `agent-component-advisor.skill` into your Claude Code skills directory:

```
~/.claude/skills/
```

Or distribute via a plugin marketplace.

To extract and inspect first:

```
unzip agent-component-advisor.skill -d agent-component-advisor/
```

## What's inside

```
agent-component-advisor/
├── README.md                            (this file)
├── SKILL.md                             (entry point: when to trigger, procedure, output template)
├── evals/
│   └── evals.json                       (10 test cases used to develop the skill)
└── references/
    ├── decision-tree.md                 (Tree A, Q1–Q7, with rationale per branch)
    ├── criteria.md                      (the 10 decision criteria, cited by number in verdicts)
    ├── composition-patterns.md          (8 named patterns for combining components)
    ├── anti-patterns.md                 (12 anti-patterns to audit any design against)
    ├── nfr-matrix.md                    (4 component types × 9 non-functional concerns)
    ├── guardrails.md                    (cost, compliance, portability, latency SLO)
    └── output-template.md               (the exact verdict format)
```

The skill loads `decision-tree.md`, `composition-patterns.md`, `anti-patterns.md`, and `guardrails.md` on every invocation; `criteria.md`, `nfr-matrix.md`, and `output-template.md` are loaded on demand.

## The framework behind the skill

The skill operationalises a longer reference document, *Decision Framework: Skills, Code-Skills, Tools, and Hooks* (v1.2). Both the framework and the skill recognise four component types and acknowledge subagents and structured-output (function-calling) hybrids as first-class composition primitives. Hooks are routed via a reusability sub-question — reusable cross-app policies (PII redaction, sanctions screening, content moderation) belong in a Tool invoked by a thin Hook, not in a hook with the logic baked in.

## How it was built

The skill was developed in two iterations against ten realistic enterprise cases (banking-biased: sanctions screening, KYC extraction, email triage, portfolio commentary, credit approval, regulatory bulletins, month-end close, PII redaction, VaR calculation, next-best-action). Each case was run with-skill and without-skill in parallel; outputs were graded against assertions; the user reviewed.

| | Iter 1 (loose) | Iter 2 (strict) |
|---|---|---|
| with-skill pass rate | 98% | 96.6% |
| without-skill pass rate | 79% | 62% |
| **skill lift (delta)** | **+19pp** | **+35pp** |

The widening delta in iter 2 reflects that user feedback led to *stricter* assertions (Hook-invoked Tool composition, scope discipline, no implementation-detail leakage) — the skill kept passing them; the baseline didn't.

## Scope and non-goals

In scope: choose a component **type** and a composition **pattern**. Cite criteria and anti-patterns by name.

Out of scope: pick a specific library, model variant, vendor, or internal implementation. Mentioning these is the *Implementation-detail leakage* anti-pattern — they are downstream decisions made by the team that owns the component.

## Limitations

- The skill assumes the platform is Claude Code or Microsoft Agent Framework 1.0. Other platforms (LangGraph, AutoGen, OpenAI Assistants) map roughly onto the same primitives but the framework's Tree A may need adjustment.
- The decision tree is a heuristic, not a proof. For genuinely ambiguous cases the verdict surfaces the trade-offs rather than forcing one answer.
- The four-factor test in Q4 (dependency footprint, latency, external invocation, independent versioning) and the Q6 reuse split between *Tool wrapping LLM* and *Code-skill wrapping LLM* are the most subtle decisions in the tree — verdicts on these benefit from human review.

## Version

`agent-component-advisor` v2.1 — May 2026.
