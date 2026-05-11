# Cross-cutting Guardrails

Apply *after* Tree A. Each guardrail can override or qualify the tree-derived answer.

## Cost

If the component will run more than ~100×/day at production volume, prefer code-skill or tool over prompt-skill. The token cost of carrying a prompt-skill in context grows linearly with invocation. Consider a hook for policies that a prompt-skill keeps re-explaining on every call.

## Compliance

Regulated decisions (credit, clinical, sanctions, legal advice, market risk) may not depend on a prompt-driven skill on the critical path. The audit story for "the model decided" is unacceptable to most regulators. Prompt-skills are acceptable for human-in-the-loop *drafting* only.

If the user's requirement falls in this category, the answer must be code-driven skill, tool, or hook — even if Tree A landed elsewhere.

## Vendor portability

Cross-platform requirements (Claude Code + Microsoft Agent Framework, or moving between providers) are best served by MCP tools and `SKILL.md` skills. Both ecosystems consume both natively.

Hooks/middleware are platform-specific. If portability matters, abstract the hook behind a tool with the same contract on each platform, or accept a per-platform implementation behind a portable interface.

## Latency SLO

Synchronous, user-facing path with a tight SLO (e.g. <500ms) → avoid prompt-skill on the critical path. Prompt-skill latency is token-bound and variable. Use a tool (with a function-calling LLM inside if you need judgement) so latency is bounded and measurable.

## How to apply

In the verdict's *Guardrails* section, briefly note each guardrail's status:
- "n/a" if it doesn't apply
- A short note if it does, e.g. "Compliance: regulated decision — confirms code-driven backend"
- An override if a guardrail flips the Tree A answer, e.g. "Compliance: regulated path overrides Q7 — must be tool-with-structured-output, not prompt-skill"
