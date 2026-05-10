---
id: 2026-05-10-decision-log-mvp-retro
kind: strategy
project: decision-log
sources: []
created: 2026-05-10
updated: 2026-05-10
verified-on: 2026-05-10
tags: [retrospective, sdlc, decision-log]
---

# Decision-log MVP retrospective

A retro on the *execution* of the decision-log MVP under the SDLC v4.0 framework. Companion to the previous-project retro at `2026-05-09-workflow-and-skills-retro` (the one that drove the v4 update itself). This one feeds whatever the v5 update will be.

## What worked

### The verb cycle held up across 6 stories

Capture → compile → plan → execute → verify → file → document → refresh-state covered everything that came up. The plan-then-execute split (with a separate plan-commit per story) kept the audit trail readable: 6 plan commits + 18 task commits + epic-close + 1 file/document commit = clean linear history.

### `excludedCommands` removed the previous project's biggest pain

The retro that drove v4 flagged "9 extra exchanges per project" from sandbox-blocking-Playwright. With `npm install` / `npm test` / `npm run e2e` / `npm run snapshots` in `sandbox.excludedCommands`, all test execution stayed in-session. **Zero operator handoffs for testing across the entire MVP.** The original goal was per-story handoff at story close; we got per-task in-session.

### Verifier sign-off caught real issues

Out of 18 task verifier dispatches, 4 returned FIX-AND-RESUBMIT:

- **s0-t0** — drift in `excludedCommands` (added `npm install` and `npm test` beyond ADR 0002's sanctioned set). Resolution: amend the ADR with the empirical sandbox finding, then re-add the commands.
- **s0-t3** — test file naming mismatch (`persist.test.ts` vs spec's `actions.test.ts`); form discarded server-validation errors. Resolution: rename + plumb `setError`.
- **s3-t1** — page-level test coverage gap (FilterPanel, ActiveFilterChips, Home `?status=` validation untested). Resolution: extract `TagFilterIndicator` for testability + add four mocked `Home` tests.
- **s4-t2** — task sequencing: t1 was unverified/uncommitted when t2 verifier ran, mixing diffs. Resolution: rewind, commit t1 properly, then commit t2.

Each was a real gap. The fresh-context verifier consistently saw what self-review missed.

### Test layers behaved as designed

ADR 0002 predicted ~80% of behaviour would be testable without a browser via Layer 2 (in-memory SQLite + integration tests). Final count: **124 unit + integration tests vs 5 Playwright specs** — a 25:1 ratio. The fast inner loop (`npm test`, ~2s) ran constantly; the heavier E2E runs (Playwright + dev server, ~10s) ran at task close.

### v4 SDLC updates landed mid-project and got applied immediately

Mid-session we shipped SDLC.md v4.0 (new `document` verb + Pre-flight + autonomy default + Hard Rules 16–19), then partially reverted three items (CL-5/CL-6/TDD Guard) at the operator's call. The reverts surfaced a coherence-pass need (orphan references, count mismatches), which got cleaned up. Subsequent stories applied v4 conventions cleanly — `document` verb fired at epic close (this README), publication checkpoint fired (Hard Rule 18), ADRs migrated to `docs/decisions/` per the co-locate convention.

### Pattern reuse across stories

- **Pure-helper + thin-action-wrapper** (s0-t3) reused for status-change in s5-t1
- **Server-component form with optional `onSubmit` prop** (s2 SearchBox) reused for FilterPanel (s4) and StatusChangeForm (s5)
- **Shared `tests/setup-db.ts` helper** (introduced in s3-t0) absorbed every subsequent migration with zero per-test changes
- **`<Component>Chip` extraction pattern** (TagChip in s3, ActiveFilterChips superseding TagFilterIndicator in s4) — when a chip-style affordance was needed in two places, it was its own file before duplication crept in

## What didn't work

### Forgot to commit s4-t1 before starting s4-t2

t1's UI work and t2's E2E/snapshot work ended up in the same working tree; the verifier on t2 caught the entanglement. Resolution required disentangling diffs and committing t1 separately. **Cost:** one extra verifier round, ~15 min of re-sequencing.

### Verifier round-trips were heavier than necessary

For tasks where I missed coverage (page-level tests in s3-t1, status-filter test extensions in s5-t0), the round-trip cost ~20 min including verifier dispatch + fix + re-dispatch. A pre-dispatch self-check ("for each AC bullet: is there a test? for each new component: is there a render test?") would have caught these without burning a verifier round.

### `SQLITE_ERROR` flake from Playwright concurrency

3-4 Playwright workers writing to a shared `db.sqlite` produced transient `SQLITE_ERROR` in dev-server logs (sometimes failing tests, sometimes just noise). Resolution: pinned `workers: 1` in `playwright.config.ts`. **Identified in s3 follow-ups, deferred to s4-t2** — the deferral was correct (it was tolerable noise) but the fix should have been pinned earlier the moment it surfaced.

### Tailwind `require()` failed in Next 15 ESM

`tailwind.config.ts` used CJS `require('tailwindcss-animate')` which blew up the dev server on second-route compile. **Caught only by s0-t5's snapshot script** (which exercises multiple routes). Resolution: switch to ESM `import animate from 'tailwindcss-animate'`. **Cost:** confused debugging until snapshot script revealed the failure mode.

### Status filter was in s4's BDD but ships in s5

The user-stories file's BDD for s4 explicitly mentions filtering by status. But status doesn't exist until s5. Workaround: s4 ships filter for tag/date/owner with a note that status is deferred; s5 augments. **The story spec didn't flag this clearly upfront.** Future: when a story's BDD references functionality that ships in a later story, the spec should call out the deferral explicitly.

### Page-level testing pattern took two stories to settle

s3-t1's verifier flagged that `app/page.tsx` branching wasn't tested. The fix (mock `@/db/index` + `@/lib/decisions/list` + `@/lib/decisions/search` + `await Home(...)`) became the standard for page-level coverage in s4 and s5. Earlier stories (s0-s2) didn't have equivalent coverage. **Acceptable as evolutionary — the pattern emerged when needed — but the test gap was real for the earlier home page.**

## What to change next time

### Pre-dispatch self-check before invoking verifier

Before each `Agent` dispatch for verification, mentally walk the spec's AC bullets one by one and confirm each has a corresponding test or evidence in the diff. The four FIX-AND-RESUBMIT cycles were all coverage gaps the verifier found in seconds — the same scan would have caught them without burning a round.

### Commit at task boundaries; never carry uncommitted work into the next task

s4-t2's verifier specifically caught this. The discipline is simple: each task close ends in a commit. The next task starts from a clean tree. No exceptions.

### Run snapshots earlier in story development

s0-t5's snapshot script exposed the Tailwind ESM issue *after* t0-t4 had all shipped. A "smoke screenshot" pass after each significant page change (instead of only at story close) would have surfaced compile-time issues earlier.

### Story specs should explicitly call out deferred BDD items

When story X's BDD references functionality that ships in story Y (where Y > X), the X spec should say so. s4's spec mentioned status as in-scope per the BDD but actually deferred to s5; the deferral was correct but the spec should have flagged it in the acceptance criteria, not just task notes.

### Consider `db.sqlite` rotation for E2E concurrency

Pinning Playwright `workers: 1` is fine for demo scale but won't hold at larger test suites. Per-test or per-worker DB instances (env var → unique sqlite file) would let parallel workers coexist. **Defer** unless a future project surfaces the problem.

## Specific candidates for SDLC v5

In rough priority order:

1. **Pre-dispatch verifier checklist** — codify the self-check above as part of the Verify verb. Before dispatching the verifier, Claude walks the AC bullets and confirms each has evidence. The verifier still runs, but most FIX-AND-RESUBMIT cycles disappear.

2. **Commit-at-task-boundary as a Hard Rule** — currently implicit. Promote to Hard Rule 20: "Each task close ends in a commit. Starting the next task with uncommitted work from the previous one is a process violation."

3. **Snapshot script as a per-task checkpoint** (not just per-story) — for projects with significant UI surface, run snapshots in-loop. Tailwind/Next config issues that compile-on-second-route-load otherwise surface only at story close.

4. **BDD-deferral annotations in story specs** — small SDLC-template addition: when a story's BDD touches functionality outside its scope, the story spec lists the deferred items with the target story.

5. **Per-worker DB isolation for E2E** — defer until a project surfaces it. Optional improvement to ADR 0002's testing approach.

## Numbers

- **6 stories** shipped (s0–s5) over the MVP
- **18 task closes** with verifier sign-off
- **4 FIX-AND-RESUBMIT** cycles (22% of tasks), all coverage/sequencing gaps
- **0 KICK-BACK-TO-ACTIVE** (no design-level rework needed)
- **124 unit + integration tests** + **5 Playwright specs** + **9 snapshot states**
- **25 commits** on `main`, linear history, no merges
- **0 operator handoffs for testing** (cf. ~9 in the previous project)
- **3 SDLC framework changes during the project**: v4.0 implementation, three reverts, coherence pass — all tracked through the v4-update story in `/sdlc/work/done/`

## Closing observation

The previous retro's two load-bearing improvements were (1) shifting autonomy from `attended` to `review` and (2) wiring user-facing docs and publication into the SDLC. The autonomy shift didn't get applied to this project (the epic stayed at `attended` for continuity); the docs-and-publication wiring did, and worked. The autonomy default change probably gets revisited when the next project starts fresh under v4.0 from session 1.
