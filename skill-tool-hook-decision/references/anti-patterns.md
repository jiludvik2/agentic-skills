# Anti-patterns

Audit every recommendation against this list. If the user has proposed a design, audit *their* design too — the anti-patterns are usually how teams talk themselves into a wrong answer that sounded reasonable.

- **The mega-skill.** A 2,000-line `SKILL.md` doing six unrelated jobs. Lazy-loading misfires and context bloats. *Fix:* Split by responsibility.

- **Prompt-driven calculation.** Using LLM judgement for arithmetic, parsing, validation, format conversion, hashing, IBAN checks. *Fix:* Move to code (code-driven skill or tool).

- **Skill for an external API.** Telling the model in markdown to "run this curl". Loses retries, auth secrets, observability, rate limits, idempotency. *Fix:* Use a tool.

- **Description leakage.** Vague skill descriptions trigger spurious or missed loads. *Fix:* Treat the description as a public API; review it.

- **Determinism via temperature=0.** Sampling reduction is not reproducibility. *Fix:* If reproducibility matters, the operation belongs in code.

- **Hidden cross-component dependencies.** Skill A silently assumes skill B is loaded, or assumes a tool is available. *Fix:* Document in the description, or merge.

- **Untyped LLM extraction.** Returning free-form JSON-in-prose to a downstream parser. *Fix:* Use function-calling / structured output via a tool.

- **Policy in the prompt.** "Remember to redact PII before posting" inside a SKILL.md. *Fix:* Move to a hook so it runs deterministically and is testable.

- **No kill switch.** Skill or tool with no runtime way to disable it without a deployment. *Fix:* Build the kill switch in v0.

- **Model-version drift unmanaged.** Prompt-skill behaviour shifts when the underlying model upgrades. *Fix:* Pin the model and re-run the eval suite on changes.

- **Hook bloat.** Hooks that do business logic, not policy. Hooks should be cheap and orthogonal. *Fix:* Push logic into the tool or skill the hook intercepts.

- **Reusable policy buried in a hook.** Implementing a cross-app policy (PII redaction, sanctions screening, content moderation) inside a platform-specific hook means it can't be reused by other agents and must be re-implemented per platform. *Fix:* Use the *Hook-invoked Tool* composition — the Tool holds the reusable policy, the hook is a thin invocation point on each platform.

- **Implementation-detail leakage.** The framework chooses a *component type* (and composition). It is not the place to prescribe specific libraries (Azure Document Intelligence vs LlamaParse), model variants (small fine-tuned LM vs vanilla LLM), vendor selections, or framework-internal mechanics. Mentioning these as part of a routing verdict invites users to debate implementation when they need to commit to a type first. *Fix:* Stop at the type and composition. If the user explicitly asks for implementation guidance, treat that as a separate decision.

## How to use this list

When you arrive at a recommendation, scan this list with the user's *original* phrasing in mind. If they said "I'll put the policy in a SKILL.md", call out *Policy in the prompt* even if your tree-derived answer is correct — you want them to know *why* their first instinct was wrong, so they don't redo it next time.
