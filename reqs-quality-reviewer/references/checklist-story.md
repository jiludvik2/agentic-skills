# User Story Checklist — Detailed

Use this when reviewing a user story. Each check has a fail signal and an example fix.

## Format

### F1. Mike Cohn use case present
- **Required form:** "As a [persona], I want to [action], so that [outcome]."
- **Fail signal:** Free-form description with no role / action / outcome structure, or missing one of the three clauses.
- **Fix:** Rewrite into the three-part form. If the "so that" is genuinely unknown, that's a deeper gap — flag it.

### F2. At least one Gherkin scenario
- **Required form:** A scenario with Given / When / Then. Multiple Givens are fine. Only one When and one Then per scenario.
- **Fail signal:** AC written as bullet lists of features, or as paragraphs, with no Given/When/Then structure.
- **Fix:** Convert to Gherkin. If multiple Whens or Thens appear, that's a split signal (see U4-Small).

### F3. Value-focused summary
- **Required:** A short title naming the value, not the feature.
- **Fail signal:** "Add delete button", "Implement API endpoint".
- **Fix:** Re-title around the user benefit, e.g. "Bulk delete to save time for power users".

## Use-case quality

### U1. Persona specificity
- **Pass:** "trial user visiting for the first time", "admin managing 1000+ items", "paid subscriber on the Pro tier".
- **Fail:** "user", "the customer", "people".
- **Fix:** Replace generic placeholder with the actual segment that benefits.

### U2. "I want to" is a user action
- **Pass:** "log in with Google", "bulk delete archived items".
- **Fail:** "have a login button", "use the new API".
- **Fix:** Reframe from feature-having to user-doing.

### U3. "So that" is a real motivation
- **Pass:** "so that I can access the app without creating a new password", "so that I don't lose progress if the page crashes".
- **Fail:** "so that I can log in" (after "I want to log in") — just restates the action.
- **Fix:** Ask "and then what?" until you reach a genuine motivation.

## Acceptance-criteria quality

### A1. When aligns with "I want to"
- The trigger event in the AC should be the same action the user said they wanted.

### A2. Then aligns with "so that"
- The expected outcome should be the realisation of the motivation, observable from outside the system.

### A3. Then is measurable
- **Pass:** "page loads in under 2 seconds", "success confirmation message appears".
- **Fail:** "user has a better experience", "the system is faster".
- **Fix:** Replace subjective language with a concrete, observable check.

### A4. Edge cases — surface, don't grade
- Empty states, error states, permission failures, partial data — knowing *which* edge cases apply requires domain knowledge of the system the reviewer doesn't have.
- If an obvious case is missing for the domain (e.g. a payments story silent on failure or refund), surface it as a question for the team rather than a graded gap.
- Multiple edge cases bundled into one scenario, on the other hand, *is* text-verifiable — see A5.

### A5. One When + one Then per scenario
- **Fail signal:** Three or more Whens, or chained Thens. This is the strongest signal that the story is actually multiple stories.
- **Fix:** Split. Each When/Then pair becomes its own scenario or its own story.

## INVEST — what's verifiable from text vs what isn't

Three letters are verifiable from the text alone. Three depend on team context the reviewer doesn't have, and should be surfaced as questions, not graded.

### Graded (verifiable from text)

#### N — Negotiable
- Does the AC describe behaviour, or does it prescribe implementation?
- **Fail signal:** AC specifies UI pixel positions, exact API field names, specific library or framework choices.
- **Fix:** Strip implementation; keep behaviour.

#### V — Valuable
- Is the persona an end user, and does the "so that" describe an observable user benefit?
- **Fail signal:** "As a developer, I want to refactor…", "As the system, I want to…", "As QA, I want test coverage…". Or a persona that is an end user but a "so that" that names a tech change with no user difference.
- **Critical fix:** Don't try to pass this by tweaking the persona alone. If there's no user-visible change, it's an engineering task. Move it to a tech-task tracker or absorb it into a story that does deliver value.

#### T — Testable
- Does every Then contain an observable, measurable predicate?
- **Fail signal:** "Then it feels intuitive", "Then performance improves", "Then it's faster".
- **Fix:** Quantify, or define the observable event (e.g. "confirmation banner appears", "row count matches input").

### Surfaced (not graded — depends on team context)

#### I — Independent
- The reviewer can't know which other stories exist or their status. What the text *can* reveal: an explicit statement like "depends on story X being done first" or "blocked by Y".
- **If a dependency is named in the text:** surface it as a question for the team to confirm.
- **If nothing is named:** don't claim Independent passes or fails — say nothing.

#### E — Estimable
- "Can the team size it?" depends on the team's familiarity with the domain, not the text.
- **Textual signal to surface:** explicit uncertainty language — "we don't know how", "requires research", "depends on a decision we haven't made".
- **If the signal fires:** recommend a spike before estimation. If it doesn't fire: don't grade.

#### S — Small
- "Deliverable in a sprint" depends on team velocity and sprint length. Not in the text.
- **Textual signal to surface:** multiple Whens or multiple Thens in one scenario (already caught by A5); a "manage" verb (CRUD bundle); multiple personas in scope; multiple data types in scope.
- **If the signal fires:** suggest a splitting pattern from `checklist-epic.md`. If not: don't grade.

## Worked example

**Input:**
> As a user, I want a dashboard so that I can see things. AC: dashboards work.

**Gaps:**
- F2 — no Gherkin AC.
- U1 — "user" is generic.
- U2 — "want a dashboard" describes a feature, not an action.
- U3 — "see things" restates the feature.
- A3 — "dashboards work" is not measurable.
- V — borderline; what does the user actually do differently?
- T — nothing to test against.

**Suggested rewrite:**
> **Summary:** Surface real-time project status to PMs to cut status-update overhead.
>
> As a project manager running 3+ active projects, I want to see each project's current phase, blockers, and next milestone on one screen, so that I can answer "where are we?" without messaging each team lead.
>
> **Scenario:** PM checks status across active projects
> **Given** I have at least one active project assigned to me
> **And Given** that project has logged blockers or milestone updates in the last 7 days
> **When** I open the dashboard
> **Then** I see each active project's current phase, top blocker, and next milestone, refreshed within the last 5 minutes.
