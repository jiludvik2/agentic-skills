---
id: s5-subagent-integration-and-design-review
kind: story
project: code-review
status: done
parent: epic-reviewer-subagent
created: 2026-05-26
updated: 2026-05-28  # RETIRED — superseded by ADR-0010 (two-skill split) and replaced in epic position 5 by s5-review-selection-scheme. Integration/consumer ACs moved to intent-review-requirements (handoff for a future consumer project).
---

> **RETIRED 2026-05-28** — This story is preserved for traceability. The unified-reviewer integration premise it described was split into two independent same-format skills per **ADR-0010** (`code-review` deterministic + `intent-review` probabilistic, with the consumer/integration explicitly out of scope). The slot at epic position 5 is now occupied by **`s5-review-selection-scheme`** (`code-review`'s `--review`/`--depth` selection model; see ADR-0011). The integration/consumer ACs originally in this story are captured in **`sdlc/docs/strategy/intent-review-requirements.md`** for a future consumer project.

# s5 — Sub-agent integration with LLM design review inside the turn (RETIRED)

## Summary

Update `.claude/agents/reviewer.md` to read the SDLC skill's `review_scope` config (`lite` / `standard` / `full`) and branch accordingly. At `lite` scope, the sub-agent does LLM-only review (matching the current behaviour). At `standard` and `full` scope, it invokes the `code-review` skill's CLI for deterministic analysis, then performs LLM design review *as part of its own turn* using the deterministic SARIF as grounding context. This is the keystone story — every previous story builds toward this one, and the hypothesis is tested here.

The sub-agent's flow at `standard` / `full` scope:

1. Read the spec, plan, and diff.
2. Read `review_scope` from the SDLC skill's project-level config.
3. Invoke the `code-review` skill's CLI via the Bash tool: `python -m code_review.cli --review-scope <scope> --scope <timing> --diff <range> --output .claude/skills/code-review/runs/<id>.json`. The output path is project-relative so the file lands inside the sandbox's default writable region.
4. Read `.claude/skills/code-review/runs/<id>.json` — the consolidated, deduplicated, severity-mapped SARIF + metrics + ranked hotspots from s0–s4.
5. **In the same turn**, perform LLM design review: read the diff, read the deterministic findings, and surface only the design / naming-intent / architectural issues the rule-based layer can't catch.
6. Merge design findings into the SARIF (`ruleId` prefixed `llm-design.*`, `properties.severity` per the SDLC taxonomy).
7. File `-fix<N>-` tasks for Critical/Important per rule #25, append Minor to the parent task's `notes:`, drop Nit.

At `lite` scope, steps 2–4 are skipped — the sub-agent goes directly to step 5 without deterministic context.

Step 5 is the only LLM step at any scope. It happens inside the sub-agent's turn, drawing from the interactive Claude Code subscription pool by construction. No HTTP service, no Agent SDK credit, no separate process. The flow runs cleanly under the operator's `/sandbox`-enabled session without requiring any unsandboxed retries.

## Use Case

- **As a** SDLC operator running the Review verb at task close or story boundary
- **I want to** set a `review_scope` once per project (`lite` for PoCs, `standard` for production, `full` for complex brownfield) and have the single `reviewer` sub-agent adjust its behaviour accordingly — without configuring individual tools
- **so that** quick projects stay fast, production projects get security and quality coverage, complex projects get full coupling and contract testing, and the entire workflow stays on the interactive subscription pool

## Acceptance Criteria

### Scenario: Sub-agent invokes the skill CLI at per-task review time

- **Given** a task has just passed Verify (per the SDLC's Verify verb)
- **When** the SDLC loop dispatches the Review sub-agent
- **Then** the sub-agent invokes `python -m code_review.cli --scope per-task --diff <base>..<head> --output <path>` via the Bash tool with the task's commit range, then reads the output file; no analysis logic is inlined in the sub-agent's prompt — the analyzer set is determined by the skill's `capabilities.json` and any explicit `--analyzer` overrides

### Scenario: Sub-agent reads the skill's capabilities before invoking

- **Given** the sub-agent is preparing to invoke a review
- **When** it constructs the CLI invocation
- **Then** it first runs `python -m code_review.cli --capabilities` to discover which analyzers are available, verifies that any policy-required analyzers (e.g. gitleaks for the SDLC's secrets gate) have `status: available`, and escalates via the Autonomy gate if a required analyzer is unavailable rather than submitting an invocation that would silently lack coverage

### Scenario: LLM design review is performed inside the sub-agent's turn

- **Given** the deterministic CLI has produced `.claude/skills/code-review/runs/<id>.json` with consolidated SARIF, metrics, and hotspots
- **When** the sub-agent processes the result
- **Then** within the same turn, the sub-agent reads the diff, reads the deterministic findings, and emits design-review findings of its own; no separate process is spawned to call the Anthropic API; no `claude -p` is invoked; the LLM call counts against the operator's interactive subscription session

### Scenario: LLM design review does not duplicate deterministic findings

- **Given** the deterministic SARIF contains a finding at `src/auth.py:47` for `python.lang.security.audit.sql-injection`
- **When** the sub-agent performs LLM design review
- **Then** its emitted design findings do not include a finding at `src/auth.py:47` for the same vulnerability class, measured as: 0 design findings whose `(file, line, CWE)` triple matches a deterministic finding within a ±3-line tolerance. The sub-agent's design-review prompt explicitly instructs against duplication

### Scenario: LLM design review surfaces issues the deterministic layer missed

- **Given** a fixture diff where the deterministic layer produces no findings but the diff contains a clear design issue (e.g., a function named `process_data` that actually handles authentication — a domain-naming mismatch)
- **When** the sub-agent performs LLM design review
- **Then** its emitted findings include at least one design finding flagging the naming/intent issue with `properties.category` in {`naming-intent`, `design`, `architecture`} and `ruleId` prefixed `llm-design.`

### Scenario: Design findings carry SDLC severity directly

- **Given** the sub-agent emits a design finding
- **When** the finding is structured
- **Then** the finding carries `properties.sdlc_severity` (one of `critical`, `important`, `minor`, `nit`) directly — no second pass through the aggregator's mapper is needed because the sub-agent's own prompt enforces the taxonomy when emitting findings

### Scenario: Critical and Important findings auto-spawn fix tasks per rule #25

- **Given** the consolidated review (deterministic + design) contains 2 Critical and 1 Important finding
- **When** the sub-agent processes the result
- **Then** 3 new fix-task artefacts are created in `/sdlc/work/active/` with ids following the `<parent-task-id>-fix1-<slug>` convention, each with `parent:` pointing to the parent story, `sources:` referencing the consolidated review file, and inserted at the front of the remaining task queue per the SDLC's auto-progress rules

### Scenario: Minor findings append to parent task notes, not as separate tasks

- **Given** the consolidated review contains 4 Minor findings
- **When** the sub-agent processes the result
- **Then** no new fix tasks are filed for the Minor findings; the parent task's `notes:` field gains 4 entries, each summarising one Minor finding with file:line and the rationale

### Scenario: Nit findings are dropped

- **Given** the consolidated review contains 7 Nit findings
- **When** the sub-agent processes the result
- **Then** no fix tasks are filed, the parent task's notes are not modified by Nit findings, and the sub-agent's report records the count for audit but takes no other action

### Scenario: The 2-round remediation bound (rule #25) holds

- **Given** a parent task's round-1 fix tasks have themselves produced Critical/Important findings on their own Review (round-2 fix tasks filed)
- **and Given** the round-2 fix tasks produce yet more Critical/Important findings on Review (would be round-3)
- **When** the sub-agent processes the round-3-would-be result
- **Then** the sub-agent halts the auto-progress loop, invokes the Autonomy gate's escalation interface, and reports to the operator with the option to iterate, accept as known debt, or rework the parent task — exactly as the current sub-agent does

### Scenario: Story-level review runs at story boundary with story-level scope

- **Given** the last task in a story has just closed cleanly
- **When** the SDLC loop reaches the story-boundary Review per the Execute verb's auto-progress logic
- **Then** the sub-agent invokes the CLI with `--scope story-level` and the cumulative story diff (base = story's first commit's parent, head = last task's commit); the CLI runs cross-task analyzers (dependency-cruiser at full scope, contract adapters from s4); design review for the cumulative diff happens in the same turn; fix tasks for story-level Critical/Important are filed under the same parent story

### Scenario: A CLI failure does not silently close a task

- **Given** the CLI exits non-zero (e.g., a required adapter was unreachable, or the worktree was malformed)
- **When** the sub-agent reads the output
- **Then** the sub-agent does not mark the task `done`, does not advance auto-progress, surfaces the failure via the Autonomy gate's escalation interface (per rule #14: never bypass the gate), and records the failure context (CLI exit code, which analyzer failed, what the error was) in `STATE.md`

### Scenario: Sub-agent runs cleanly under the operator's sandbox

- **Given** the operator's Claude Code session has `/sandbox` enabled in auto-allow mode with the recommended strict settings (`failIfUnavailable: true`, `allowUnsandboxedCommands: false`)
- **When** the sub-agent is dispatched for a per-task review
- **Then** every Bash command the sub-agent runs (`python -m code_review.cli --capabilities`, the main `python -m code_review.cli ... --output ...` invocation, and the read of the output file) completes inside the sandbox without prompting the operator for filesystem or network widening; no `dangerouslyDisableSandbox` retry occurs; no fallback to unsandboxed execution is needed

### Scenario: Sub-agent refuses to retry failed commands unsandboxed

- **Given** a Bash command issued by the sub-agent fails with a sandbox-related error (e.g., bubblewrap's "operation not permitted", Seatbelt's deny, or a host-not-allowed network error)
- **When** Claude Code offers the sub-agent the option to retry with `dangerouslyDisableSandbox: true`
- **Then** the sub-agent's prompt explicitly forbids this retry — it does not invoke the escape hatch, even if doing so would let it complete the task. It surfaces the original failure to the operator via the Autonomy gate, naming what was blocked and what `settings.json` change would unblock it (e.g., "Schemathesis target `http://api.internal:8080` was blocked by the sandbox network policy. Add it to `sandbox.allowedDomains` and re-run.")

### Scenario: Context budget is respected on large story-level diffs

- **Given** a story-level diff containing 40+ changed files and 2000+ changed lines
- **When** the sub-agent runs the consolidated review
- **Then** the deterministic CLI completes within its own timeouts (orthogonal to context budget), and the LLM design review step either (a) completes successfully within the sub-agent's turn, or (b) emits a clear "context budget pressure" diagnostic and escalates to the operator suggesting the design review be re-dispatched as its own sub-agent. The sub-agent does not silently truncate the design review

### Scenario: No edits to /sdlc/SDLC.md are required for this story

- **Given** the integration is complete and tested
- **When** I `git diff /sdlc/SDLC.md` between before and after this story
- **Then** the diff is empty; only `.claude/agents/reviewer.md`, `.claude/skills/code-review/`, and possibly `CLAUDE.md`'s reviewer pointer have changed

### Scenario: Scope switch is instant and reversible

- **Given** a project running with `review_scope = "standard"` in the SDLC skill's config
- **When** the operator changes the config to `review_scope = "lite"` (or `"full"`)
- **Then** the next SDLC Review dispatch uses the corresponding scope; at `lite`, no deterministic CLI is invoked; at `full`, contract-testing adapters are included at story-level timing; no artefacts beyond the config need changing

### Scenario: `lite` scope matches the current SDLC reviewer's behaviour

- **Given** the `code-review` skill is installed but `review_scope = "lite"`
- **When** the SDLC loop dispatches the Review sub-agent for a per-task review
- **Then** the sub-agent does LLM-only review without invoking `python -m code_review.cli`; the output is functionally equivalent to the SDLC reviewer's behaviour before this epic existed; no deterministic findings appear; review speed is the same as before

## Test specification

- **Sub-agent invocation test** — given a fixture diff and a stub CLI that returns canned consolidated output, assert the sub-agent's dispatch produces the expected fix-task files with the right ids and parents.
- **Capability-check test** — fake `--capabilities` output with a policy-required analyzer marked `unavailable`; assert sub-agent escalates rather than submits a review with silent omission.
- **Design-finding fixture test** — small fixture diff with a known naming mismatch that no deterministic rule will catch; run a real sub-agent dispatch end-to-end; assert at least one design finding in the expected category appears.
- **Dedup-against-deterministic test** — fixture where deterministic SARIF contains a SQL-injection finding at a known line; run the sub-agent; assert no design finding duplicates that location/CWE within tolerance.
- **Severity routing test** — table-driven over the four SDLC severities × expected sub-agent action (file fix task / append to notes / drop / escalate).
- **Rule #25 bound test** — simulate round-1 → round-2 → round-3-would-be, assert escalation rather than silent round-3 filing.
- **CLI-failure test** — mock CLI to exit non-zero, assert sub-agent escalates via the Autonomy gate and does not close the task.
- **Sandbox-clean-run test** — run a full per-task review at `standard` scope in a `/sandbox`-enabled session with strict settings (`failIfUnavailable: true`, `allowUnsandboxedCommands: false`); assert successful completion with no permission prompts and no unsandboxed fallback.
- **Sandbox-bypass-refusal test** — simulate a Bash command failing with a bubblewrap "operation not permitted" error during a sub-agent dispatch; assert the sub-agent escalates with a remediation message rather than retrying with `dangerouslyDisableSandbox: true`.
- **Scope-dispatch test (lite)** — set `review_scope = "lite"` in a fixture SDLC config; run a Review; assert no `python -m code_review.cli` subprocess was spawned; assert LLM-only findings appear.
- **Scope-dispatch test (standard)** — set `review_scope = "standard"`; run a Review; assert the CLI was invoked with `--review-scope standard`; assert security + quality findings appear; assert no coupling/cohesion or contract-testing findings appear.
- **Scope-dispatch test (full)** — set `review_scope = "full"`; run a story-level Review; assert the CLI was invoked with `--review-scope full`; assert contract-testing and coupling/cohesion findings appear alongside security + quality.
- **Scope-switch test** — start at `standard`, switch to `lite`, run a Review (assert no CLI), switch to `full`, run a Review (assert full analyzer set). No artefacts touched between switches beyond the config line.
- **Story-level fixture test** — multi-task fixture with planted cross-task drift (e.g., inconsistent error handling across two files); assert story-level review at `standard` or `full` scope surfaces it where per-task reviews of either file alone would not.
- **Context-budget test** — fixture story-level diff sized close to the sub-agent's turn budget at `full` scope; assert either successful completion or a clean diagnostic escalation, never silent truncation.
- **End-to-end task close test** — run a real per-task Review at `standard` scope with deterministic + LLM design on a fixture diff with planted findings of all four severities; assert the resulting `/sdlc/work/active/` and `/sdlc/work/done/` states match expectations.
- **Subscription-pool assertion** — instrument the test environment to fail if any `ANTHROPIC_API_KEY` is set or if `claude -p` is invoked during a Reviewer dispatch at any scope.
- **No-SDLC-diff assertion** — automated check in CI: any PR that modifies `.claude/agents/reviewer.md` or files under `.claude/skills/code-review/` must NOT modify `/sdlc/SDLC.md`. Cross-cutting changes (if any) require a separate ADR.


## Out of scope (deferred)

- A Verifier counterpart that consumes deterministic findings — Verifier remains a sub-agent producing Decision-shaped output as the SDLC document already describes; a future epic could give it a similar deterministic layer if useful.
- Unattended / CI invocation of the Reviewer — that would mean using the Agent SDK credit pool or an API key, which this epic explicitly avoids. A separate future epic could add a thin CI wrapper if needed.
- Concurrent reviews — the sub-agent's turn is single-threaded; the SDLC's auto-progress loop is also single-threaded.
- A web UI for browsing past reviews — out of scope; filesystem is the source of truth per SDLC line 10.
- Prompt iteration based on operator feedback — a structured feedback loop on the design-review prompt is a future epic.
