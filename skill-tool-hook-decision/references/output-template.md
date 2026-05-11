# Output Template

Use this exact structure for the verdict. Sections marked *omit if N/A* can be left out.

```
## Recommendation
**Primary component:** <prompt-driven skill | code-driven skill | tool | hook/middleware>
**Composition pattern:** <Skill+Tool | Tool wrapping LLM | Hook+Tool | Code-skill+Tool | Subagent+parent | Skill stack | none>

## Tree A walkthrough
- Q1 <short form of the question>: <Yes/No> → <next or "stop">
- Q2 <short form>: <Yes/No> → <next or "stop">
- (continue with the questions you actually answered, including Q5/Q6/Q7 if reached)

## Rationale
<1–3 sentences. Cite criteria by number from references/criteria.md, e.g. "Criterion #2 (state mutation) and #4 (auditability) drive this to a tool with an audit hook.">

## Composition detail
*(omit if single-component)*
- <Other component>: <why>
- ...

## Watch-outs
- <anti-pattern flagged from references/anti-patterns.md, named explicitly>
- <design risk specific to this requirement>

## Guardrails
- Cost: <note or "n/a">
- Compliance: <note or "n/a">
- Portability: <note or "n/a">
- Latency SLO: <note or "n/a">
```

## Tone

- Be direct. The user wants a recommendation, not three options.
- Name things explicitly. "Tool" is fine, "Tool wrapping LLM" is better when that's what's meant.
- Cite framework constructs: criteria by number, anti-patterns by name, composition patterns by name.
- Disagree with the user when the evidence supports it. If they proposed a SKILL.md and Tree A says Tool, say Tool — don't soften into "either could work".

## Scope discipline

This framework chooses a **component type** (and a composition pattern). It does **not** prescribe:

- Specific libraries or SDKs (e.g. Azure Document Intelligence vs LlamaParse, fine-tuned small LM vs vanilla LLM).
- Vendor or commercial-vs-build choices.
- Internal implementation mechanics of the chosen component type.
- Model selection or prompt-engineering details.

These are downstream decisions for the team that owns the component. If the user explicitly asks for them, treat it as a separate conversation and answer briefly without pretending the framework drove the choice. Calling them out when not asked is the *Implementation-detail leakage* anti-pattern.

## Length

A typical verdict fits on one screen. If the requirement is genuinely complex (multiple sub-operations with different routes), separate verdicts per sub-operation, then a one-line composition summary at the top.
