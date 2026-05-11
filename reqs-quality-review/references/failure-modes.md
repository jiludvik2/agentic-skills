# Failure-Mode Catalogue

Scan for these patterns when reviewing. Each one points to a specific gap. Use this as a quick checklist before composing the verdict.

# Failure-Mode Catalogue

Each entry is tagged **Graded** (text-verifiable, contributes to the verdict) or **Surfaced** (the reviewer cannot judge from text alone; surface as a question for the team). Use this as a quick checklist before composing the verdict.

## Persona problems

### FM-P1. Generic persona — Graded
- **Symptom:** "As a user, …", "As a customer, …".
- **Where it bites:** Universal — User-centric; INVEST – Valuable (often).
- **Fix:** Replace with a specific segment.

### FM-P2. System or team as persona — Graded
- **Symptom:** "As a developer, I want to refactor…", "As QA, I want test coverage…", "As the system, I want…".
- **Where it bites:** INVEST – Valuable.
- **Fix:** This is a technical task, not a user story. Reframe or move out of the user-story backlog. Do **not** try to rescue it by swapping the persona.

### FM-P3. Persona drift — Graded only when parent epic provided
- **Symptom:** Story persona differs from parent epic persona without explanation.
- **Where it bites:** Cross-cutting – Persona consistency.
- **Verifiable only if both story and parent epic are in front of the reviewer.** If only one artifact is provided, skip this check.
- **Fix:** Either align with the epic, or name the sub-segment and justify why it differs.

## "So that" problems

### FM-S1. So-that restates the action — Graded
- **Symptom:** "I want to click save, so that I can save."
- **Where it bites:** Use-case quality U3.
- **Fix:** Dig into the real motivation. Often the actual outcome is risk-avoidance or time-saving.

### FM-S2. So-that is unrelated to the parent epic — Graded only when parent epic provided
- **Symptom:** Outcome doesn't ladder up to the epic's intent.
- **Where it bites:** Cross-cutting – Outcome traceability.
- **Verifiable only if both story and parent epic are provided.** If only one is provided, skip.
- **Fix:** Either the story belongs to a different epic, or the epic intent is wrong.

## Acceptance-criteria problems

### FM-A1. AC is a feature list, not scenarios — Graded
- **Symptom:** AC reads as bullets of capabilities, no Given/When/Then.
- **Where it bites:** Format F2.
- **Fix:** Convert each capability into a Given/When/Then scenario.

### FM-A2. Untestable Then — Graded
- **Symptom:** "Then it's faster", "Then the experience is better", "Then users are happy".
- **Where it bites:** AC quality A3; INVEST – Testable.
- **Fix:** Quantify or specify the observable check.

### FM-A3. Multiple Whens / Thens in one scenario — Graded
- **Symptom:** AC has 3+ Whens or chained Thens.
- **Where it bites:** AC quality A5; story-level signal that splitting is needed.
- **Fix:** Split. Each When/Then pair should be its own scenario, often its own story.

### FM-A4. Edge cases absent — Surfaced
- **Symptom:** Only the happy path is covered; empty / error / permission cases are silent.
- **Why surfaced:** Knowing *which* edge cases apply requires domain knowledge of the system the reviewer doesn't have.
- **Action:** If an obvious edge case is missing for the domain (e.g. a payments story silent on failure), surface it as a question. Otherwise, say nothing.

## Sizing and splitting problems

### FM-Sz1. Explicit uncertainty about size — Surfaced
- **Symptom:** Text says "we don't know how big this is", "depends on research", "can't size yet".
- **Why surfaced:** Whether the team could actually size it depends on team context. What's text-verifiable is that someone has said they can't.
- **Action:** Recommend a spike (Pattern 9) before treating it as a deliverable.

### FM-Sz2. Horizontal slice — Graded
- **Symptom:** "Front-end work for X", "API endpoint for Y", "Database schema for Z".
- **Where it bites:** Universal – Vertically sliced.
- **Fix:** Reframe so the slice crosses all needed layers and produces user-observable change.

### FM-Sz3. Epic fails Valuable, being split anyway — Graded
- **Symptom:** Tech initiative (migration, refactor, infra) being broken into smaller tech tasks.
- **Where it bites:** INVEST – Valuable. Special rule: do not split.
- **Fix:** Either reframe around user-visible value, or take it out of the user-facing backlog entirely.

### FM-Sz4. Epic with no AC at all — Graded
- **Symptom:** Title + description only; nothing to derive splits from.
- **Where it bites:** Epic C4.
- **Fix:** Add at least one Given/When/Then at epic level.

## Prescription and negotiability

### FM-N1. Implementation-prescribed story — Graded
- **Symptom:** AC specifies UI pixels, exact field names, specific libraries.
- **Where it bites:** Universal – Negotiable; INVEST – Negotiable.
- **Fix:** Strip implementation; describe behaviour.

### FM-N2. Solution stated before problem — Graded
- **Symptom:** Description names "the dashboard" or "the new API" without articulating what user need it serves.
- **Where it bites:** Outcome-focused; Use-case quality.
- **Fix:** Move the problem and outcome to the front. The solution name is a hint, not the requirement.

## Missing-field problems

### FM-M1. Required field absent — Graded
- **Symptom:** Persona missing, AC missing, estimate field missing, identity missing — any required content field absent or marked TBD.
- **Where it bites:** Story F1/F2 or Epic C1–C5 (whichever applies).
- **Fix:** Fill the field. If the team genuinely can't, that's a discovery problem, not a wording problem.

## Hypothesis-specific (optional, epic only)

These apply *only* if the epic is framed as a hypothesis. They are quality enhancers, not gates.

### FM-H1. Hypothesis restates the feature — Graded
- **Symptom:** "If we build a dashboard, then users will have a dashboard."
- **Fix:** Replace the "then" with an outcome — a change in user behaviour or metric.

### FM-H2. No experiments — Graded
- **Symptom:** Hypothesis stated; "we'll test by building it."
- **Fix:** Define lightweight experiments (prototype, concierge, landing page) before commitment.

### FM-H3. Validation timeframe vague — Graded
- **Symptom:** "We'll know eventually", or no timeframe at all.
- **Fix:** State a timeframe and a specific leading indicator.
- **Note:** Whether the chosen timeframe is *realistic* for the metric chosen is a team judgement, not text-verifiable. Only the *presence* of a stated timeframe is graded.
