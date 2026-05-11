# Decision Tree A — Choosing the Primary Component Type

Walk top to bottom. Stop at the first match that fits the *primary* responsibility. Composition still applies — see `composition-patterns.md`.

## Q1. Is this a cross-cutting policy concern?

(auth, redaction, audit, rate-limit, prompt-injection defence, content moderation, sanctions screening, content filtering)

- **Yes →** Continue to **Q1a**.
- **No →** Continue to Q2.

### Q1a. Is the policy *logic itself* reusable across multiple agents or applications, or does it need to be portable across platforms (Claude Code, MS Agent Framework, etc.)?

- **Yes →** **Tool** as the primary component (the Tool *is* the policy implementation), invoked via a thin **Hook / middleware** at each agent's interception point. Composition pattern: **Hook-invoked Tool**. The Tool holds the reusable, versioned, testable, observable logic; the Hook is the per-platform glue that guarantees the Tool runs on every relevant call.

  Examples that fit here: PII / secret redaction, sanctions screening, content moderation, profanity filters, suitability-style checks shared across desks, identity / authorisation checks shared across products.

- **No →** **Hook / middleware** as the primary component, with the policy logic implemented inside the hook. Use this only when the policy is genuinely scoped to a single agent or platform (e.g. an agent-specific debug logger).

*Why the split:* hooks are deterministic but platform-specific. Putting reusable business policy *inside* the hook means re-implementing it on every platform and locking out other agents that need the same check. Putting the policy in a Tool — invoked via a thin hook on each platform — gives reuse, portability, semver, observability, and a single audit trail. The Hook still ensures the policy is unskippable.

*Why this is Q1:* policy concerns apply to many tool calls, not one. Putting them in a skill or a domain tool makes them skippable and re-explained. Q1 keeps the deterministic-interception property; Q1a separates the *logic* (Tool, reusable) from the *invocation point* (Hook, per-platform).

## Q2. Does the operation interact with an external system, or otherwise mutate shared state?

(network call, database, SaaS API, persistent storage, message bus, payment, anything that "writes" or "sends")

- **Yes →** **Tool.** Local function for in-process work, MCP server for cross-agent / cross-language reuse. Tools own auth, retries, observability, idempotency, and versioning. Stop.
- **No →** Continue to Q3.

*Why this is Q2:* anything mutating state needs idempotency, retries, audit, and an explicit failure mode. Skills can't provide that contract; tools can.

## Q3. Does the requirement demand deterministic, repeatable output and/or full audit traceability?

- **Yes →** Continue to Q4. (Prompt-driven skill is disqualified — sampling reduction is not reproducibility.)
- **No →** Skip to Q5.

## Q4. Does the deterministic logic meet *all* of the following?

(a) Bounded dependency footprint that fits the agent runtime.
(b) Executes within the agent's per-call latency budget.
(c) No need for invocation from outside the agent.
(d) No need for an independent versioning / release lifecycle.

- **All yes →** **Code-driven skill.** Bundle the script with a `SKILL.md` that explains when and how to invoke it. Script output enters context, source does not — cheap on tokens, deterministic, locally auditable.
- **Any no →** **Tool**, exposed via MCP. Packaging as a server gives observability, scaling, dependency isolation, independent release lifecycle, and reuse across agents and languages.

*Why these four factors:* they capture the actual deployment-boundary question. Lines of code is not a useful proxy.

## Q5. Does the requirement involve judgement, synthesis, classification with fuzzy criteria, or natural-language production?

- **Yes →** Continue to Q6.
- **No →** Reconsider — most non-judgement operations belong in Q1, Q2, or Q4. Avoid prompt-driven skills for arithmetic, parsing, format conversion, or rule lookups.

## Q6. Does the consumer need a typed, machine-parsable result?

(downstream code branches on the output; values are stored or compared; reason codes are enumerated)

- **Yes →** Wrap the LLM call in a typed envelope. Choose the packaging by reuse, just like Q4:
  - *Reused across agents / BUs, or needs an independent release lifecycle?* → **Tool with a structured-output LLM call inside** (MCP / function-calling). Versioned, observable, schema-stable across consumers.
  - *Single-agent, single-app, no external invocation?* → **Code-driven skill that wraps a structured-output LLM call** in its bundled script. Same typed-output property; lighter packaging when reuse isn't needed.
- **No →** Continue to Q7.

*Why Q6 matters:* "untyped LLM extraction" is an anti-pattern. If the output enters code, it should be typed. The wrapper gives you that without losing the LLM judgement. The wrap can be a Tool *or* a code-driven skill — the typing is what counts; the packaging follows the same reuse logic as pure-deterministic Q4.

## Q7. Will multiple agents or business units rely on this judgement?

- **Yes →** **Prompt-driven skill** published to the shared skill registry. Invest in a tight, disambiguating description so lazy loading triggers correctly.
- **No →** Inline the prompt in the agent system prompt, or keep a local prompt-driven skill scoped to that agent.
