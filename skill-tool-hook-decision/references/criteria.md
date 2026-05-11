# Decision Criteria

Cite these by name in the Rationale of your verdict so the user can trace the reasoning. Criteria #1–#4 usually decide the answer.

| # | Criterion | What to ask |
|---|---|---|
| 1 | Determinism required | Same input → same output? Temperature=0 is *not* determinism — only code is. |
| 2 | Side effects / state mutation | Does it write, send, charge, or otherwise change state? Mutating ops need idempotency, retries, audit — almost always tools or hooks. |
| 3 | Operation nature | Judgement / synthesis (LLM-shaped) vs transformation / computation (code-shaped) vs external interaction (tool-shaped) vs cross-cutting policy (hook-shaped). |
| 4 | Auditability & blast radius | Must each invocation be replayable and signed off? How wide is the blast radius if the component misbehaves? |
| 5 | Reuse scope | Single workflow, single agent, multiple agents, or cross-BU? Wider reuse → typed tool with versioning. |
| 6 | Observability budget | What traces / metrics / logs do you need? Tools have first-class observability; prompt-skills require LLM-trace tooling. |
| 7 | Security surface | Prompt-injection exposure, secret handling, IAM scopes, data residency. Mutating-on-untrusted-input → tool guarded by hook. |
| 8 | Token cost / latency / SLO | Volume × token cost. Synchronous user-facing path? Prompt-skill latency is variable; tool latency is bounded. |
| 9 | Invocation pattern | Always-needed (default-loaded tool) vs conditionally needed (lazy-loaded skill) vs runtime-injected (hook). |
| 10 | Implementation & ops complexity | Prompt engineering ≪ bundled script ≪ packaged MCP server ≪ middleware in the agent runtime. Pick the cheapest mechanism that satisfies #1–#7. |
