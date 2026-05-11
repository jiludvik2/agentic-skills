# Epic Checklist — Detailed

Use this when reviewing an epic. Drawn from the `epic-breakdown-advisor` skill: an epic is quality when it has enough structure for a team to validate it can be split into INVEST-passing stories.

An epic does **not** need to be framed as a hypothesis. Hypothesis framing (if/then + experiments + validation measures) is a quality enhancer, not a gate.

## Required content

### C1. Identity
- Title or ID by which the epic can be referenced.
- **Fail signal:** Untitled paragraph of ideas.

### C2. Description
- What the epic covers, in enough detail that someone unfamiliar with it understands the scope.
- Plain description is fine. Hypothesis framing is fine. A bare title is not.

### C3. Target persona
- A specific user segment.
- **Pass:** "remote project managers juggling 3+ distributed teams".
- **Fail:** "users", "customers", "the business".

### C4. Acceptance criteria at epic level
- One or more Given/When/Then pairs that describe what "done" looks like across the epic.
- Multiple When/Then pairs are *expected* at this level — they're the splitting signal the breakdown advisor uses.
- **Fail signal:** No AC at all, or AC so vague that no When/Then can be derived.

### C5. Estimate field present
- The reviewer can check whether an estimate has been recorded (any size — t-shirt, points, sprint count).
- **Fail signal:** Estimate field absent or marked TBD.
- **Note:** The reviewer cannot judge whether the estimate is *right*. That's for the team. The check here is only that someone has stamped a size on it. If the description signals high uncertainty (see Estimable below), recommend a spike instead.

## INVEST — what's verifiable from text vs what isn't

Small is omitted at epic level: epics are expected to be too large for a sprint.

### Graded (verifiable from text)

#### N — Negotiable
- Does the epic frame behaviour, or does it prescribe UI, tech stack, or data model?
- **Fail signal:** Epic specifies exact UI, exact tech stack, exact schema, named third-party libraries.
- **Fix:** Strip prescription. Keep the user-observable behaviour.

#### V — Valuable — the critical gate
- Is the persona an end user, and does the epic describe an observable user change?
- **Fail signal:** "Migrate to new platform", "Refactor authentication service", "Improve test coverage" — persona is internal or outcome is invisible to users.
- **Critical rule:** Do not try to fix a Valuable failure by splitting. The breakdown advisor's rule is: STOP, reframe the epic, or absorb the work into something that does deliver user value. A horizontally-sliced tech initiative split into smaller horizontal slices is still not a quality epic.

#### T — Testable
- Do the epic-level AC contain observable pass/fail predicates?
- **Fail signal:** "Then the new system is better." Or AC absent altogether.
- **Fix:** Add at least one Given/When/Then with a measurable Then.

### Surfaced (not graded — depends on team context)

#### I — Independent
- The reviewer can't know which other epics exist or their status. **Textual signal to surface:** an explicit statement of dependency in the description.
- **If named in the text:** surface as a question. **If not:** don't grade.

#### E — Estimable
- The reviewer can't predict whether the team could size it. **Textual signal to surface:** explicit uncertainty language — "we don't know how", "needs research", "depends on a decision".
- **If the signal fires:** recommend a spike (Pattern 9) before treating it as a deliverable epic. **If not:** don't grade.

## Splittability — suggest, don't grade

Whether an epic *can* be split into INVEST-passing stories is a team judgement that depends on architecture and codebase the reviewer can't see. What the reviewer *can* do is scan the text for signals that a particular pattern looks plausible, and surface those as suggestions.

For each pattern, look for the textual signal listed under **Trigger**. If the signal is present, name the pattern in the verdict as a suggestion for the team to validate. If no signals fire across any of the 9 patterns, say so — and ask the team which pattern they intend to use.

### Pattern 1 — Workflow Steps
- **Trigger:** Multi-step workflow where a simple case could ship first.
- **Slice rule:** Thin end-to-end, not step-by-step. Each slice does the whole workflow at increasing sophistication.
- **Example:** "Publish content (editorial review, legal approval, staging)" → (a) author uploads, content goes live immediately; (b) add editorial gate; (c) add legal gate. Each delivers the full publish workflow.
- **Anti-pattern:** Splitting into "editorial review story" + "legal approval story" + "publish story" — horizontal.

### Pattern 2 — Operations (CRUD)
- **Trigger:** Words like "manage", "handle", "maintain". They bundle multiple operations.
- **Slice rule:** One story per Create, Read, Update, Delete.
- **Example:** "Manage user accounts" → create / view / edit / delete user account.

### Pattern 3 — Business Rule Variations
- **Trigger:** Same functionality, different rules per user type / region / tier / scenario.
- **Slice rule:** One story per rule variation.
- **Example:** "Flight search with flexible dates" → search by date range / by specific weekends / by date offsets.

### Pattern 4 — Data Variations
- **Trigger:** Different data types, formats, or structures.
- **Slice rule:** One story per data variation, simplest first, more added just-in-time.
- **Example:** "Geographic search" → by county; then add city/town; then add custom provider area.

### Pattern 5 — Data Entry Methods
- **Trigger:** Fancy UI elements (date pickers, autocomplete, drag-and-drop) that aren't essential to the core function.
- **Slice rule:** Simplest input first; sophisticated UI as a follow-up story.
- **Example:** "Search with calendar date picker" → (a) search by date with plain text input; (b) add calendar picker UI.

### Pattern 6 — Major Effort
- **Trigger:** First instance carries most of the complexity; additions are trivial.
- **Slice rule:** "Implement one + add remaining."
- **Example:** "Support 5 payment providers" → (a) implement Stripe; (b) add PayPal; (c) add the rest.

### Pattern 7 — Simple / Complex
- **Trigger:** Core simplest version exists; many edge cases or variations sit on top.
- **Slice rule:** Core happy path first, variations later.
- **Example:** "Tax calculation for US sales" → (a) flat-rate single-state case; (b) add multi-state rules; (c) add exemptions.

### Pattern 8 — Defer Performance
- **Trigger:** Story bundles "make it work" and "make it fast" together.
- **Slice rule:** Make it work first; performance becomes its own story.
- **Example:** "Generate report under 2 seconds" → (a) generate report (any speed); (b) optimise to <2s.

### Pattern 9 — Break Out a Spike
- **Trigger:** Uncertainty so high that none of patterns 1–8 can be applied.
- **Slice rule:** Time-box an investigation (e.g. 3 days) producing a written recommendation. Then re-evaluate.
- **Note:** A spike is not a deliverable to a user. It's a precondition for the epic becoming Estimable.

## Worked example

**Input:**
> Epic: Improve onboarding.
> Description: Make onboarding better for new users.
> AC: New users have a better onboarding experience.
> Estimate: ?

**Gaps:**
- C3 — "new users" is borderline; what kind? Trial, paid, invited?
- C4 — AC is not testable.
- C5 — no estimate.
- T — fails Testable.
- E — fails Estimable.
- No clear splitting pattern applies because the epic is too vague.

**Suggested rework:**
> **Epic:** Reduce 24-hour drop-off for trial users on the free plan.
> **Persona:** Non-technical solopreneurs signing up to the free trial.
> **Description:** Trial users currently abandon within 24 hours (Mixpanel, Jan 2026: 60% complete 0 actions). The epic introduces guided first-session steps to get users to their first meaningful action.
> **AC:**
> - **Scenario:** First-session guidance reduces immediate drop-off
> - **Given** a trial user lands on the empty dashboard for the first time
> - **When** they sign in
> - **Then** they are shown a 3-step checklist (create project / invite teammate / complete task)
> - **And** they reach their first completed action within 10 minutes in at least 50% of cases
> **Estimate:** ~3 sprints.
> **Splittability:** Pattern 1 (workflow steps) — start with the simplest checklist showing for all trial users, then add progress tracking, then add completion celebration.
