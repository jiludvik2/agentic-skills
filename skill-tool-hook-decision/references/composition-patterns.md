# Composition Patterns

Most useful capabilities combine multiple component types. Reach for these patterns by name; resist mono-component designs.

| Pattern | Shape | When to use |
|---|---|---|
| **Skill + Tool** | Prompt-skill instructs the model when/how to call a domain tool. | Cross-BU judgement that needs to act (e.g. "draft and post a Jira update"). |
| **Tool wrapping LLM (function-calling)** | Tool whose internals call an LLM with a JSON-schema response format. | Typed extraction, classification, routing — when callers need a parseable object **and** the capability is reused across agents / BUs. |
| **Code-skill wrapping LLM** | Code-driven skill whose bundled script calls an LLM with a JSON-schema response format. | Same as above, but for a single agent with no cross-app reuse and no independent versioning need. Lighter packaging than a tool. |
| **Code-skill + Tool** | Code-skill orchestrates deterministic steps and calls tools at well-defined points. | Multi-step workflows with auditable orchestration (e.g. month-end close). |
| **Hook + Tool** | Pre-tool hook enforces an *agent-local* policy (scope check, debug logging); tool executes. | Policies that apply to a single agent and aren't reusable across apps. |
| **Hook-invoked Tool** | Thin Hook on each platform calls a shared **Tool** that holds the reusable policy logic. | Cross-app reusable policies — PII / secret redaction, sanctions screening, content moderation, identity checks. The Tool is the policy implementation; the Hook is the per-platform invocation point. |
| **Subagent + parent toolset** | Parent spawns a focused subagent with a narrow tool budget for a long task. | Research-style tasks; jobs that would bloat the parent's context. |
| **Skill stack** | Lightweight "meta-skill" describes when to load several specific skills. | Domain entry-points that branch into specialised judgement paths. |

## How to choose a pattern

1. From the Tree A walk you already have a *primary* component type for the main responsibility.
2. Identify each remaining responsibility: external systems → tools; cross-cutting policies → hooks; internal deterministic steps → code-skills; isolation/parallelism → subagent.
3. Pick the named pattern whose shape matches.
4. If the answer doesn't fit a named pattern, that's a signal to double-check Tree A — usually one of the responsibilities was mis-routed.
