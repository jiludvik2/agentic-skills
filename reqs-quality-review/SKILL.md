---
name: reqs-quality-review
description: Review whether a user story or epic is good enough to support implementation, against criteria verifiable from the requirement text itself. Use whenever the user shares a requirement, backlog item, Jira/Linear ticket, story, or epic and asks for a quality check, readiness assessment, "is this ready", "is this good enough", definition-of-ready review, INVEST check, gap analysis, or feedback. Use proactively when the user pastes a story or epic and asks for any kind of review — even if they don't say "quality" — and when they ask whether a requirement is implementable, splittable, or missing anything. Returns a structured verdict (Ready / Needs work) with graded gaps and team questions separated, drawn from Mike Cohn user stories, Gherkin acceptance criteria, INVEST, and the Humanizing Work splitting patterns.
---

# Requirements Quality Review

Evaluate whether a requirement is ready to support implementation. This skill applies to two artifact types: **user stories** and **epics**. PRDs and other higher-level artifacts are out of scope.

A requirement is "ready to support implementation" when a delivery team could pick it up and build it without needing to chase down missing context, reframe it, or guess at success criteria.

## The reviewer's honest scope

Some quality criteria can be verified from the requirement text alone (e.g. "is the Then measurable?", "is the persona generic?"). Others depend on team context the reviewer can't see (e.g. "can the team estimate this?", "is there a hard dependency on unfinished work?", "which edge cases apply to this domain?").

This skill is explicit about that line: it **grades** verifiable criteria and **surfaces** the rest as questions for the team. A requirement is judged Ready or Needs Work based on graded criteria only. Team questions are reported alongside but do not by themselves drive the verdict.

## How to use this skill

1. **Identify the artifact type.** Decide whether the input is an epic or a user story. If unclear, ask the user.
2. **Run the matching rubric.** Apply §2 for stories or §3 for epics. The detailed checklists live in `references/checklist-story.md` and `references/checklist-epic.md` — read whichever applies.
3. **Apply universal and cross-cutting checks** (§4).
4. **Look for known failure modes** in `references/failure-modes.md`.
5. **Return a verdict** in the format in §5.

If the user shares multiple items, review each one separately and produce one verdict per item.

If anything is genuinely ambiguous (e.g. you can't tell whether "user" means a real persona or generic placeholder), flag it as a gap rather than guess.

## 1. Universal quality dimensions

These apply to both epics and stories. Use them as filters during the level-specific review. Each is verifiable from the text itself.

- **User-centric** — a specific persona benefits, not "users" or "the system". Developers or internal teams are not valid personas for user-facing work; that signals a technical task, not a requirement.
- **Outcome-focused** — describes the change in user behaviour or experience, not the output being shipped.
- **Testable** — success can be observed and disproven. "Better experience" and "faster" fail unless paired with a concrete measure.
- **Negotiable** — frames intent without prescribing implementation pixel-by-pixel.
- **Vertically sliced** — crosses all layers needed for observable user value. "API for X" or "UI for X" on their own are horizontal slices and fail.

Scope completeness (whether the requirement covers everything it *should*) is not in this list. Knowing what should have been said requires domain knowledge the reviewer doesn't have. See §4 on how to handle obvious gaps without grading them.

## 2. User story rubric

A user story is ready when **all** of the following hold. Full checklist with examples is in `references/checklist-story.md`.

### 2.1 Format
- Mike Cohn use case: "As a [specific persona], I want to [action], so that [outcome]."
- At least one Gherkin scenario: Given / When / Then. Multiple Givens are fine; only one When and one Then per scenario.
- A short value-focused summary title.

### 2.2 Use-case quality
- Persona is specific (e.g. "trial user", "admin managing 1000+ items"), never bare "user".
- "I want to" is a user action, not an internal feature description.
- "So that" is a real motivation, not a paraphrase of the action.

### 2.3 Acceptance-criteria quality
- "When" aligns with "I want to"; "Then" aligns with "so that".
- "Then" is observable and measurable.
- Multiple Whens or Thens in one scenario are a fail at the AC-structure level (each scenario should have one When and one Then). This is also a textual signal that the story may need splitting — surfaced under §2.4 *Small*.

### 2.4 INVEST — what to grade vs what to surface

Only some INVEST letters can be judged from the text alone. The others depend on team context the reviewer doesn't have.

**Grade these (verifiable from the text):**

| Letter | What to check | Fail signal |
|---|---|---|
| **N**egotiable | Does the AC prescribe implementation (pixels, library names, exact field names) rather than behaviour? | Pixel-level or tech-stack prescription |
| **V**aluable | Is the persona an end user, and does the "so that" describe an observable user benefit? | Persona is a team/role (developer, QA, "the system"); or outcome is a tech change with no user-visible difference |
| **T**estable | Does every Then contain an observable, measurable predicate? | Subjective Then ("better", "faster", "happier") with no quantification or observable event |

**Surface these as team questions (not graded):**

- **Independent** — Does the description mention a dependency on other unfinished work? If so, name it in the verdict as a question for the team to confirm.
- **Estimable** — Does the description signal high uncertainty ("we don't know how", "needs research", "depends on a decision")? If so, surface as a spike candidate.
- **Small** — Multiple Whens/Thens in one scenario is a strong textual signal that the story should be split (see A5). Use that as the trigger; don't claim to judge sprint-fit directly.

A story is **Ready** when 2.1–2.3 pass and the graded INVEST letters (N, V, T) pass. Items surfaced as team questions are reported but do not by themselves make the story Needs Work — unless a textual signal explicitly fires (e.g. a named hard dependency, multiple Whens, an explicit "we don't know how to build this").

## 3. Epic rubric

An epic doesn't need to be framed as a hypothesis. It needs enough structure for a team to validate it can be split into INVEST-passing stories. Full checklist in `references/checklist-epic.md`.

### 3.1 Required content
1. **Identity** — title or ID.
2. **Description** — what the epic covers. Plain description is fine; a hypothesis frame (if/then with experiments and validation measures) is a quality enhancer but not required.
3. **Target persona** — specific, not "users".
4. **Acceptance criteria** — one or more Given/When/Then pairs at epic level. Multiple When/Then pairs are *expected* here; they're the splitting signal.
5. **Estimate field present** — grade only whether an estimate has been recorded. Whether the number is *right* is for the team to judge, not the reviewer.

### 3.2 INVEST — what to grade vs what to surface

Small is omitted at epic level: epics are expected to be too large for a sprint, which is the whole point of running a breakdown.

**Grade these (verifiable from the text):**

| Letter | What to check | Fail signal |
|---|---|---|
| **N**egotiable | Does the epic prescribe UI or implementation rather than framing behaviour? | Pixel-level or tech-stack prescription |
| **V**aluable | Is the persona an end user, and does the epic describe an observable user benefit? | Tech initiative (migration, refactor) with no user-visible change — STOP, reframe, do not split |
| **T**estable | Does the epic AC give observable pass/fail conditions? | Vague or absent AC |

**Surface these as team questions (not graded):**

- **Independent** — Does the text name a dependency on other unfinished epics? If so, surface as a question.
- **Estimable** — Does the text signal uncertainty so high that no estimate could be produced? If so, recommend a spike (Pattern 9) before treating it as a deliverable epic.

A *Valuable* failure is special: do not attempt to split. Reframe the epic or absorb the work into something that does deliver user value.

### 3.3 Splittability — suggest, don't grade

Whether an epic *can* be split into INVEST-passing stories is ultimately a team judgement: it depends on architecture, codebase, and the team's appetite. The reviewer can suggest which pattern looks plausible from the text, not guarantee it will work.

For each candidate pattern, look for the textual signal and surface a suggestion if it fires:

1. **Workflow steps** — text describes a multi-step flow (e.g. "review then approve then publish").
2. **Operations (CRUD)** — verbs like "manage", "handle", "maintain"; or multiple operations named.
3. **Business-rule variations** — different rules per user type, region, tier, or scenario named.
4. **Data variations** — different data types, formats, or structures named.
5. **Data-entry methods** — fancy UI elements (date pickers, autocomplete, drag-and-drop) named alongside core function.
6. **Major effort** — multiple instances of similar work named (e.g. "support 5 payment providers").
7. **Simple / complex** — a core case plus variations/edge cases named.
8. **Defer performance** — bundles a functional change with a performance requirement.
9. **Break out a spike** — text signals uncertainty too high for any of 1–8.

If none of these signals appear in the text, say so and ask the team which pattern they intend to use.

An epic is **Ready** when 3.1 passes, the graded INVEST letters (N, V, T) pass, and the AC contain enough specifics that at least one pattern signal is detectable. Items surfaced as team questions or splittability suggestions are reported but do not by themselves make the epic Needs Work.

## 4. Cross-cutting checks

Apply these on top of the level-specific rubric:

- **Vertical vs horizontal slicing** (verifiable from text) — flag any requirement framed as "front-end work for X", "API endpoint for Y", "database schema for Z". The text itself reveals the slice shape.
- **Persona consistency** (verifiable only when parent epic is provided) — if both the story and its parent epic are in front of the reviewer, check the personas match or that the story names a clear sub-segment. If only one artifact is provided, skip this check rather than guess.
- **Outcome traceability** (verifiable only when parent epic is provided) — same condition. With both artifacts in hand, check that the story's "so that" relates to the epic's intent. With only one, skip.

Scope completeness (whether unstated aspects *should* have been stated) is not a check the reviewer can perform: it requires domain knowledge of the system, the codebase, and what's been agreed elsewhere. If the reviewer spots something obviously missing — for example, a payments story with no mention of failure or refund — surface it as a question, not as a gap.

## 5. Output format

Always return the verdict in this structure:

```markdown
## Verdict: [Ready | Needs work]

**Artifact type:** [Epic | User story]
**Summary:** [One-sentence framing of what was reviewed]

### What's working
- [Concrete strengths against the rubric]

### Gaps (graded from the text)
For each gap:
- **[Rubric reference, e.g. "AC quality – measurable Then" or "INVEST – Valuable"]:** [What's missing or wrong]
  - **Suggested fix:** [Concrete rewrite, splitting pattern signal, or reframing]

### Questions for the team (not graded)
- [Any items surfaced under "Surface, don't grade" — dependencies, estimability, scope completeness, splittability pattern when no signal fired in the text]

### Recommendation
[One of:
- "Ready to implement."
- "Needs work before implementation. Address the graded gaps above, then re-review."
- "Reframe required — this is a technical task, not a user-facing requirement."
- "Split likely needed — text signals pattern [N: name]. Confirm with the team."
- "Spike likely needed before this can be estimated."]
```

The verdict is set by the **Gaps** section only. **Questions for the team** are surfaced for visibility but do not by themselves push a requirement to Needs Work. This separation matters: the reviewer is honest about what the text can tell it versus what only the team can.

If a story is **Ready** and no questions arose, the Gaps and Questions sections may be omitted.

If multiple findings share a root cause (e.g. a missing persona drives both "user-centric" and INVEST-Valuable), consolidate them into one entry with the root cause named.

## 6. Tone

Be direct but constructive. The goal is to help the user get the requirement to ready, not to grade them. Where a fix is obvious, suggest the rewrite verbatim. Where it isn't, ask the question the team would need to answer.

Avoid restating the whole rubric in the response — only cite the parts that are relevant to the gaps found.

## References

- `references/checklist-story.md` — Detailed story checklist with examples.
- `references/checklist-epic.md` — Detailed epic checklist with examples.
- `references/failure-modes.md` — Catalogue of common anti-patterns to scan for.

## Related skills

- `user-story` — canonical format for the Mike Cohn + Gherkin structure used in §2.
- `epic-breakdown-advisor` — owns the INVEST gate, the 9 splitting patterns, and the Step-0 content list used in §3.
- `epic-hypothesis` — optional richer framing for epics; not required by this rubric.
