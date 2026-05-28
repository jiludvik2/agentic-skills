---
id: adr-0010-split-deterministic-and-probabilistic-skills
kind: decision
project: code-review
status: accepted
parent: epic-reviewer-subagent
sources: [s5-subagent-integration-and-design-review.md, architecture-reviewer-subagent.md, epic-reviewer-subagent.md]
created: 2026-05-28
updated: 2026-05-28
---

# ADR-0010 — Split deterministic and probabilistic code review into two independent same-format skills

## Context

The original epic posited a single `reviewer` sub-agent that would, within one dispatch turn: (a) invoke a deterministic analyzer CLI, (b) perform LLM design review using the deterministic findings as grounding, (c) dedup/merge across the two, and (d) route fix-tasks per the SDLC's rule #25. Stories s0–s4 delivered the deterministic engine; the original s5 was to be the unified-reviewer integration.

During s5 design, the unified-reviewer prompt collapsed under its own weight: scope branching + CLI orchestration + in-turn LLM design review + dedup/merge logic + fix-task routing all packed into one `reviewer.md` markdown prompt. Two structural problems surfaced:

1. **Testability gap.** ~14 of the 21 ACs described prompt behaviour that can only be verified by a live LLM dispatch (non-deterministic, token-expensive, doesn't fit the SDLC's tests-first green-bar).
2. **Mixed responsibilities.** Deterministic mechanics (CLI invocation, fix-task filing, dedup math) and LLM judgment were tangled in one artefact; changes to either rippled to the whole prompt.

Operator direction during the s5 design conversation: split along the deterministic/probabilistic seam into two independent skills emitting the same finding format, with no aggregation between them, and the consumer/integration explicitly out of scope.

## Decision

Split the reviewer concept into **two independent same-format skills**, each in its own sibling subdir of the `agentic-skills` repository:

1. **`code-review`** (this subdir) — deterministic analyzer skill. Reads a diff, runs configured analyzers, emits consolidated SARIF + `properties.sdlc_severity` + metrics + ranked hotspots. Fully self-contained; standalone-invocable; no LLM inside.
2. **`intent-review`** (new sibling subdir, separate project) — probabilistic LLM-based review skill. Reads a diff, emits findings in the *same* SARIF + `sdlc_severity` format, with `intent.*` ruleIds and SDLC severities set directly by the prompt (no aggregator pass needed). Runs in-turn (subscription pool, no `claude -p`, no `ANTHROPIC_API_KEY`, no `anthropic` SDK).

**Invariants:**
- The two skills are **independently invocable** — neither depends on the other's output.
- They emit findings in a **shared format** (the contract): SARIF 2.1.0 runs with `properties.sdlc_severity` per the SDLC taxonomy.
- **No cross-skill aggregation / dedup / merge** is built. A future consumer LLM (out of scope) reads both outputs and dedups by judgment.

**Out of scope for this epic** — the **consumer** that would invoke both skills, dedup their findings, route fix-tasks, and orchestrate per-scope/per-story behaviour. The original s5 ACs that described this integration are captured in `sdlc/docs/strategy/intent-review-requirements.md` for a future consumer/integration project.

## Consequences

- **`code-review`** ships as a self-contained deterministic skill, fully testable with pytest, usable by any caller (human, CI, downstream LLM) without an LLM in the loop.
- **`intent-review`** is to be bootstrapped as a new sibling subdir under `agentic-skills/` (sharing the parent's single `.git`). Its requirements live in the handoff doc until that project is initialised. It will conform to `code-review`'s output schema for finding-format compatibility.
- **The consumer/integration** (the LLM that reads both and dedups) is deferred to a future project. The original s5 ACs covering this (reviewer-invokes-CLI, capability check, in-turn dedup, fix-task routing per rule #25, story-level orchestration, sandbox-bypass refusal, context-budget handling, scope-switch behaviour) move to the handoff doc.
- **Architecture §8** ("Sub-agent integration") is **superseded** by this ADR. Architecture §§1–7 and §§9–16 (the deterministic-layer architecture: analyzer protocol, SARIF aggregation, severity mapping, hotspots, sandbox compatibility, etc.) remain accurate and continue to describe `code-review`.
- **The original s5 story** is retired in favour of a redefined s5 covering only `code-review`'s review-selection scheme (see `s5-review-selection-scheme.md` and ADR-0011).
- **The bundled `reviewer.md`** in `code-review/.claude/skills/code-review/agents/`, the `setup.sh` reviewer-install step, and the tests asserting their content (`test_scope_dispatch.py` reviewer-content + setup-install tests) describe the now-out-of-scope consumer/integration. They are removed from `code-review` (Phase 3 of the closing plan) and the content is captured in the intent-review/consumer handoff.

## Alternatives considered

1. **Monolithic reviewer prompt** (original architecture §8 design). Rejected for prompt complexity and testability — see Context.
2. **Two skills with cross-aggregation inside `code-review`** (a `--extra-sarif` CLI fold-in that runs `intent-review`'s output through the s2 aggregator for dedup/severity-mapping). Rejected: still couples the two skills and adds CLI surface; a consumer LLM can dedup by judgment without mechanical merge, and the shared-format contract is enough.
3. **Selection mapping in `reviewer.md` (prompt) instead of `code-review`'s CLI.** Rejected: would break `code-review`'s standalone-invocability (a "quick review" via the CLI would need an LLM to interpret), loses determinism and pytest-testability, and forces every invocation to burn tokens on a mechanical mapping.

## Status

Accepted 2026-05-28. The `intent-review` sibling project will be bootstrapped in a separate session.
