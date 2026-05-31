---
id: intent-review-requirements
kind: strategy
project: code-review
sources:
  - sdlc/work/done/s5-subagent-integration-and-design-review.md
  - sdlc/work/active/adr-0010-split-deterministic-and-probabilistic-skills.md
  - sdlc/work/active/architecture-reviewer-subagent.md
created: 2026-05-28
updated: 2026-05-28
verified-on: 2026-05-28
---

# `intent-review` — requirements handoff (to a future sibling project)

This document captures the requirements for the probabilistic LLM-based code-review skill, **`intent-review`**, which will be bootstrapped as a new sibling subdir under `agentic-skills/` per ADR-0010. It lives here as a strategy/handoff artefact until that sibling project is initialised.

The content harvests the parts of the retired s5 story and the original architecture §8 that describe the LLM-design and integration concerns — splitting them into (a) requirements for the **`intent-review` skill itself** (the LLM design-review producer) and (b) requirements for a **future consumer** (the LLM that reads both skills' outputs and dedups / routes fix-tasks). The consumer is **out of scope** for both `code-review` and `intent-review` and is recorded here as a future project's brief.

---

## Part A — Requirements for `intent-review` (the probabilistic skill)

### A1. Purpose

LLM-based review of a diff for **intent / purpose / clarity** issues that rule-based analyzers cannot catch:

- **Domain-naming mismatches** — function/class/variable names that don't match what the code actually does (e.g. `process_data()` that handles authentication).
- **Architectural drift** — implementation diverges from the spec/story's stated intent or from documented architecture.
- **Abstraction quality** — incoherent responsibilities, leaky abstractions, missing or wrong indirection.
- **Missing tests for spec-implied edge cases** — gaps the rule-based test-coverage analyzers can't see because they require understanding the spec.
- **Intent-vs-spec misalignment** — the code does X, the spec implies Y.

### A2. Output format (the shared contract with `code-review`)

`intent-review` emits a SARIF 2.1.0 run, structurally compatible with `code-review`'s output so a downstream consumer can read either without special-casing.

- `tool.driver.name = "intent-review"` (or equivalent; the consumer keys on the field's presence).
- `ruleId` prefixed `intent.*` — e.g. `intent.naming-mismatch`, `intent.architectural-drift`, `intent.coverage-gap`.
- `properties.sdlc_severity` set **directly** by the skill to one of `critical` · `important` · `minor` · `nit` per the SDLC taxonomy. **No aggregator pass needed** — the skill enforces the taxonomy in its own prompt.
- `properties.category` in `{naming-intent, design, architecture, coverage, drift}` for downstream classification.
- Either the bare SARIF run, or the same `review-response.json` envelope `code-review` uses (TBD by the `intent-review` project — bare SARIF run is sufficient if the consumer wraps it).

### A3. Independence

- **No dependency on `code-review`'s output.** `intent-review` is invoked independently with the diff; it does **not** read `code-review`'s findings or use them as grounding context. Cross-skill dedup is the consumer's responsibility (Part B).
- **Standalone invocable.** Like `code-review`, `intent-review` must be usable by any caller (a consumer LLM, CI, or a developer) without coupling to the other skill.

### A4. Subscription-pool invariants (in-turn LLM)

- Runs **in-turn** inside the calling agent's dispatch — instructions/prompt loaded into the active turn, no separate process spawned.
- **No `claude -p`** invocation anywhere in the flow.
- **No `ANTHROPIC_API_KEY`** consulted; the env var, if set, is never propagated to any subprocess.
- **No `anthropic` SDK** imported in any code shipped by `intent-review`.
- The LLM call counts against the operator's interactive Claude Code subscription session, not the Agent SDK credit pool.
- These are CI-checkable invariants (string greps + a subprocess-env assertion).

### A5. Sandbox-clean operation

- Must operate inside Claude Code's `/sandbox` with the recommended strict settings (`failIfUnavailable: true`, `allowUnsandboxedCommands: false`).
- **No runtime network egress** required by `intent-review` itself (the diff and any spec context are passed in by the caller).
- **Refuses `dangerouslyDisableSandbox` retries** — if a Bash command issued by the skill fails with a sandbox-related error, the skill surfaces the failure via the Autonomy gate's escalation interface rather than retrying with the escape hatch.

### A6. Repository layout

- New sibling subdir: `agentic-skills/intent-review/`.
- Shares the `agentic-skills` git repository (same single `.git` at the agentic-skills root); not a separate repo. Same layout convention as `code-review` — see `sdlc/STATE.md`'s note that `code-review` is a subdir of the `agentic-skills` parent repo.
- Mirrors `code-review`'s SDLC scaffolding: own `sdlc/` (with its own SDLC.md, raw, work, docs), own `.claude/skills/intent-review/`, own `CLAUDE.md` pointer.
- The skill's verification methodology is `superpowers:writing-skills` (verification-before-deployment for prompt artefacts), not `pytest` — the deliverable is a prompt, not Python code.

### A7. The validation runbook (not unit tests)

Because the deliverable is a prompt, most behavioural assertions need a live LLM dispatch. These become a **recorded validation runbook** (operator-run) rather than CI tests. Each item below is a fixture + dispatch + observable pass condition; results recorded over the validation window:

1. **Design surfacing** — fixture diff with a `process_data()` that handles authentication; dispatch `intent-review`; observe ≥1 `intent.*` finding in `{naming-intent, design, architecture}`.
2. **Architectural drift** — fixture diff that diverges from a referenced spec; observe a finding flagging the divergence with `properties.category = drift`.
3. **Coverage gap** — fixture diff implementing a feature with a spec that implies edge cases not covered by tests; observe an `intent.coverage-gap` finding.
4. **Severity discipline** — across the fixture corpus, sample emitted findings; confirm `properties.sdlc_severity` is set, conforms to the four-value taxonomy, and is broadly calibrated (operator review).
5. **Subscription-pool invariants** — automated greps confirm no `anthropic`/`claude -p`/`ANTHROPIC_API_KEY` references in the shipped code.
6. **Sandbox-clean** — a real dispatch inside `/sandbox` strict mode completes without permission prompts or `dangerouslyDisableSandbox` retries.

---

## Part B — Requirements for a future consumer project (out of scope for both skills)

A future project will provide the **consumer LLM** that integrates the two skills into the SDLC's Review flow. Its requirements (harvested from the original s5 ACs) are recorded here for that project to pick up:

### B1. Orchestration

- Read `review_scope` from the SDLC skill's project-level config (`lite` / `standard` / `full`).
- At **`lite`** — invoke `intent-review` only (LLM-only review, matching the SDLC's current reviewer behaviour).
- At **`standard`** — invoke `code-review --depth quick` (or the relevant `--review`) **and** `intent-review`.
- At **`full`** — invoke `code-review --depth full` **and** `intent-review`; story-level review uses `--scope story-level` to include `contracts/conformance`.
- Per-task vs story-level timing dispatched per the SDLC Review verb's existing rules.

### B2. Cross-skill consumption

- Read both skills' SARIF outputs.
- **Dedup by judgment** — when `code-review` reports a finding at `auth.py:47` for `python.lang.security.audit.sql-injection` (or similar) and `intent-review` reports the same issue at the same location, drop the duplicate. The consumer's LLM reasoning handles this; no mechanical aggregator is needed (ADR-0010).
- **Route fix-tasks** per SDLC rule #25: Critical/Important → file `-fix<N>-` tasks as siblings under the parent story; Minor → append to the parent task's `notes:`; Nit → drop.
- Respect the **rule #25 2-round bound** — escalate via the Autonomy gate if a round-3 fix would be needed.

### B3. Capability check + escalation

- Before invoking `code-review`, run `python -m code_review.cli --capabilities` to verify policy-required analyzers (e.g. `gitleaks` at standard, `schemathesis` at full+story-level) are `available`; escalate via the Autonomy gate if any are missing.
- On `code-review` CLI non-zero exit, **do not silently close the task**; surface the failure via the Autonomy gate.

### B4. Sandbox-bypass refusal

- The consumer's prompt **explicitly forbids** invoking `dangerouslyDisableSandbox: true`, even if doing so would let it complete the task.
- On a sandbox-blocked Bash command, surface the original failure with a remediation message naming the specific `sandbox.allowedDomains` / `allowWrite` widening that would unblock it (per the conventions established in `code-review`'s SKILL.md).

### B5. Context-budget on large story-level diffs

- On story-level diffs exceeding safe headroom for the consumer's turn, **do not silently truncate**. Either complete the review or emit a clean "context budget pressure" diagnostic and escalate, suggesting the design review be re-dispatched as its own sub-agent.

### B6. Scope-switch is instant and reversible

- Changing `review_scope` between `lite`/`standard`/`full` takes effect on the next Review dispatch with no other artefact changes. `lite` reverts to LLM-only (no `code-review` invocation).

### B7. SDLC contract — no edits to `/sdlc/SDLC.md` to integrate

- The consumer integrates against the SDLC's Review-verb contract surface without requiring edits to `SDLC.md`. CI assertion: a PR that modifies the consumer's prompt or the skills must not modify `SDLC.md`.

---

## References

- SARIF 2.1.0 schema — finding format. **Note (s2-t1, 2026-05-31):** `code-review` no longer carries this schema (removed per ADR-0020; nothing in `code_review/` loads it after the SARIF normalisation layer was deleted in s1-t3). `intent-review` must vendor its own copy when bootstrapped.
- `code-review/code_review/schemas/review-response.json` — envelope format. **Note (s2, 2026-05-31):** this file was removed in s1 (ADR-0020); `intent-review` must define its own envelope schema when bootstrapped.
- ~~`code-review/code_review/severity.py`~~ — **deleted in s1 (ADR-0020)**; SDLC severity taxonomy (critical/important/minor/nit) now lives as prose in `SKILL.md § Interpreting the bundle › Severity judgment`.
- `code-review/code_review/capabilities.json` — analyzer registry + the s5 review-selection taxonomy.
- ADR-0010 (this repo, `sdlc/work/active/`) — the two-skill split decision.
- The retired `s5-subagent-integration-and-design-review.md` in `sdlc/work/done/` — the original unified-reviewer ACs, preserved for traceability.
