---
title: Reimagined Software Delivery Lifecycle
purpose: How Claude Code should approach all development work in this repo
version: 5.6
updated: 2026-05-11
---

# SDLC

This repository follows an AI-native, spec-anchored, compile-on-demand SDLC. The filesystem is the source of truth. Git history is the audit trail. Claude Code is the primary development agent. There is no external tracker (Jira, Notion, etc.) and none should be introduced without an ADR.

The entire SDLC working area lives under `/sdlc/`. Project code lives outside it.

## Principle

Capture is unstructured. Compilation gives material its shape. Execution acts on what's been compiled. The hierarchy — epic, story, task, decision, runbook — is emergent, not imposed. Nothing is pre-classified at capture; nothing is forced into a destination it doesn't fit.

## Glossary

Terms used throughout this document with specific meaning:

- **Operator** — the human in charge of the repo. References to "the operator decides X" mean a human approval is required.
- **Operator approval** — explicit affirmation in the chat session ("yes," "go ahead," "approved"), or an edit to the artefact in question that constitutes the approval. Silence is not approval. A previous session's approval does not carry forward to a new session.
- **Artefact** — any file under `/sdlc/work/` or `/sdlc/docs/` carrying frontmatter. Files under `/sdlc/raw/` are not artefacts; they are raw material.
- **Session** — a single Claude Code invocation, from start until the operator ends it.

## Pre-flight

Run at session 1 of every new SDLC project. Four items:

1. **Tool environment check** — run version checks for whatever's relevant (`node --version`, `python --version`, build tooling, browsers if Playwright is in scope). Catch missing prerequisites once, at start.
2. **Publication target** — three sub-questions: Will this project live on GitHub / GitLab / a private host / nowhere? If hosted: public or private? Account / org? If public: licence choice (`MIT`, `Apache-2.0`, `GPL-3.0`, etc.)?
3. **Memory snapshot** — list any existing per-project memory entries (`~/.claude/projects/<project>/memory/MEMORY.md`); flag any that contradict current repo state, name moved files, or duplicate compiled artefacts. Resolve before continuing — stale memory is worse than no memory.
4. **STATE.md session-0 entry** — capture the items above as a "Session 0 setup" entry in `STATE.md` so subsequent sessions inherit them.

Pre-flight adds ~2 messages at session 1 and prevents mid-session friction.

## Directory layout

    /sdlc/
      raw/                    unstructured capture, no rules
      work/
        active/               things being worked on, any shape
        done/                 archived
      docs/
        architecture/         long-standing architectural docs
        strategy/             strategy docs
        decisions/            ADRs, point-in-time decisions
        runbooks/             operational guides
      SDLC.md                 this file
      STATE.md                current state, regenerated at session end
    /.claude/
      agents/                 sub-agent definitions (verifier, etc.)
    CLAUDE.md                 repo-level context, points to /sdlc/SDLC.md
    [project code lives at root or in src/, etc.]

`/sdlc/raw/` holds anything captured. `/sdlc/work/` holds compiled artefacts being acted on. `/sdlc/docs/` holds compiled artefacts that explain the system. Items move between these by being compiled, not by being filed.

`.claude/` and `CLAUDE.md` stay at repo root because Claude Code's auto-discovery expects them there. `CLAUDE.md` should contain a one-line pointer to `/sdlc/SDLC.md` so the workflow is discoverable from the root entry point.

**`/sdlc/work/done/` shape.** The default is one file per artefact, matching how it was structured in `/sdlc/work/active/`. For bulk historical imports (pre-SDLC done items, legacy changelog entries), a single consolidated file is acceptable — name it `done-historical.md` or similar. Going forward under the SDLC, new done items get their own files.

**Pre-existing content.** Files that pre-date the SDLC (legacy backlogs, changelogs, scratch docs) are treated as raw material to be compiled. They live where they currently live until compilation moves them. Compilation of legacy content follows the same rules as compilation of `/sdlc/raw/` items: each item becomes a compiled artefact in the right destination, or is discarded, or is parked. Nothing is moved without being compiled.

## File conventions

Files in `/sdlc/raw/` have no required structure. Free-form notes. They have no frontmatter, no id, no status.

Compiled artefacts (anything in `/sdlc/work/` or `/sdlc/docs/`) have YAML frontmatter:

    ---
    id: stable-id
    kind: task | story | epic | decision | runbook | strategy | architecture
    project: <project-name>             # operator-defined; e.g. constellation, decision-log, sdlc
    status: active | blocked | done       # for /sdlc/work/ items only
    parent: optional-parent-id            # when relationships exist
    children: [optional-child-ids]        # when relationships exist
    sources: [paths-to-raw-sources]       # what this was compiled from
    blocker: [text]                       # required when status is blocked
    created: 2026-04-29
    updated: 2026-04-29
    verified-on: 2026-04-29               # for /sdlc/docs/ items
    tags: [optional]
    ---

Filename matches `id`. IDs are stable; never rename once assigned. The `kind` field describes what the artefact _is_, not what folder it sits in. The folder follows the kind.

**Sequential numbering reflects hierarchy.** Stories under an epic carry a sequential `s<N>-` prefix in their `id` and filename. Tasks under a story carry the parent story's prefix _plus_ a sequential `t<M>-` suffix: `s<N>-t<M>-<slug>`. `<N>` is the story's position in the epic's `children:` list (zero-indexed); `<M>` is the task's position under the story (zero-indexed). Examples: `s0-story-cc-audit`, `s1-t0-pin-cc-and-smoke-import`, `s2-t0-galaxy-graph-builder`, `s2-t1-galaxy-facade-on-graph`. The hierarchical encoding makes parentage visible at a glance and stable in `ls` output — tasks group under their story alphabetically. Inserting a story or task mid-list is a deliberate re-numbering operation: `children:` lists, `parent:` fields, and cross-references update together.

**Co-locate active work.** While an epic is in flight in `/sdlc/work/active/`, any new architecture docs, ADRs, runbooks, or strategy notes drafted as part of that epic cluster alongside it in `/sdlc/work/active/` — not in `/sdlc/docs/architecture/`, `/sdlc/docs/decisions/`, etc. They move to their semantic home (`/sdlc/docs/architecture/`, `/sdlc/docs/decisions/`, `/sdlc/docs/runbooks/`, `/sdlc/docs/strategy/`) at the same time the epic moves to `/sdlc/work/done/`. The principle: discoverability during iteration, structure once settled. Existing docs already in `/sdlc/docs/...` are not pulled back — the rule applies to new drafts.

## The verbs

Work is a small set of verbs applied as needed. They are not a sequence. You apply whichever fits.

### Capture

Drop material into `/sdlc/raw/`. Anywhere, anytime, any shape. No structure, no decisions. The only rule: don't lose the thought.

### Compile

Read `/sdlc/raw/` (and any other unstructured sources). For each item, decide what it should become and produce the compiled artefact. Possible outputs:

- a task in `/sdlc/work/active/` (one commit's worth of work)
- a story in `/sdlc/work/active/` (one coherent change worth specifying)
- an epic in `/sdlc/work/active/` (one strategic commitment)
- a decision in `/sdlc/docs/decisions/`
- an entry in `/sdlc/docs/strategy/` or `/sdlc/docs/architecture/`
- an addition to an existing artefact (link the source to it)
- discard

Compilation is a Claude operation. The operator approves the proposed compilation; Claude executes the file moves. The raw source is referenced in the `sources:` field of the compiled artefact and then deleted from `/sdlc/raw/` — once compiled, it's been absorbed.

Compilation replaces what older workflows called triage, strategic planning, and story planning. They were always the same operation at different scales.

**Summarise migrations at the high level.** Where source material describes a migration, the compiled artefact summarises the high-level shape (core logic, phases, modules, functions, methods) and enumerates them with a one-line description each. The operator signs off on the artefact, not the raw source. Faithful reproduction of long source content into the artefact is not required and usually undesirable — it bloats the artefact and creates two sources of truth.

### Plan

For an artefact in `/sdlc/work/active/` whose `kind` is `story` or `epic`, produce a task sequence. Each task entry must include:

- one-line outcome
- acceptance criteria
- test specification (defined before implementation)

Tasks are written as their own files in `/sdlc/work/active/` with `parent:` linking to the story. The plan is committed alongside the story. The operator reviews and edits the plan before execution.

**BDD-deferral annotations.** When a story's BDD or user-stories source references functionality that ships in a later story, the story spec must list the deferred items explicitly with the target story (e.g. "filter by status — deferred to s5"). The deferral belongs in acceptance criteria, not buried in task notes — otherwise the verifier will flag missing coverage that was never in scope, burning a round-trip.

### Execute

Act on a task. Tests first, then implementation. Claude writes the tests defined in the task spec, confirms they fail, then implements until they pass. No skipping tests. No "I'll add tests later." If the task spec didn't define tests, stop and update the plan.

When the task is complete: update `status: done`, commit with a message referencing the task id (e.g. `task-12: extract simulation engine module`), move the file to `/sdlc/work/done/`.

**Auto-progress within a story.** Once a task closes cleanly — verifier signed off, no unresolved gate escalations, commit landed — immediately begin the next `active` task under the same parent story without waiting for further operator approval. The operator approved the plan; executing the plan is what that approval covers. Stop the loop at the **story boundary**: when the last task of the story closes, pause and report; the operator decides whether to start the next story.

The loop also halts immediately on any of: verifier failure, an Autonomy-gate escalation, a hard-stop trigger, three failed attempts on the same sub-problem, or any operator directive ("pause", "stop", "hold on", or any instruction to do something else). Operator interruption always wins over auto-progression — there is no "let me finish this task first."

Within a task, consult the Autonomy gate before any action that isn't on the gate's free-pass list. The verifier still runs at task close.

**Snapshot script as per-task checkpoint.** For projects with significant UI surface — pages exercising routing, dynamic rendering, or per-route configs — run the snapshot/screenshot script after each significant page change rather than only at story close. Compile-time issues that surface only on second-route-load (e.g. ESM/CJS interop bugs in framework configs) otherwise hide until story close, where the cost of disentangling them is highest.

### Verify

**Pre-dispatch self-check (mandatory).** Before invoking the verifier, walk the spec's acceptance criteria one by one and confirm each has corresponding evidence in the diff: a test, a render assertion, an integration check. For every new component or module, confirm a render or unit test exists. This costs ~2 minutes; missing it triggers FIX-AND-RESUBMIT cycles that cost ~20 minutes each and burn a verifier round on a gap a self-scan would have caught in seconds.

Then invoke the `verifier` sub-agent (defined in `.claude/agents/verifier.md`). It reads the spec, the plan, and the diff with no memory of how the implementation was built. It reports alignment, test coverage, architectural drift, and code smells.

The operator reviews the verifier output. Pass → continue. Fail → fix or kick the task back to active.

The verifier is non-negotiable. It is the single highest-leverage step in the loop and the most consistently skipped.

### File

At the end of any session that touches architecture, strategy, or operational behaviour, file the outputs back. Useful sessions don't dissipate, they compound.

- architectural decisions → `/sdlc/docs/decisions/NNNN-title.md` (ADR format)
- operational changes → update relevant runbook in `/sdlc/docs/runbooks/`
- strategy shifts → update or create in `/sdlc/docs/strategy/`
- repo-wide conventions → update `CLAUDE.md`
- spec divergences → update the story spec to match what was actually built

If a session produced a thinking artefact worth keeping (architectural reasoning, a useful framing), file it as a doc with `sources:` pointing to where it came from. The system gets denser over time.

If nothing is worth filing, skip. Don't write filler.

While an epic is in flight, drafts of these documents may co-locate in `/sdlc/work/active/` per the Co-locate active work convention; they move to `/sdlc/docs/...` at epic close.

**Publication.** If a publication target was chosen during Pre-flight (GitHub, GitLab, etc.), `file` _proposes_ the remote-setup commands at session 1 (`gh repo create …` or equivalent, then `git push -u origin main` after the first commit lands). The operator approves and runs commands that affect remote state; Claude may execute purely-local git operations.

At epic close, `file` verifies:

- `git remote -v` shows a configured remote (if a target was chosen).
- `git log @{u}..HEAD` is empty (everything pushed upstream).
- Optionally proposes a release tag: `v0.1.0` for an MVP; semver onwards.

User-facing documentation is produced by the `document` verb (below), not `file`. Claude drafts commands, commit messages, and tag names; the operator runs `git push`, `gh repo create`, and tag-creation commands.

### Document

At epic close — when an epic moves from `/sdlc/work/active/` to `/sdlc/work/done/` — produce user-facing documentation for the project.

Outputs:

- `README.md` at repo root: project description, install, usage, screenshot if visual. Mandatory.
- `DEPLOYMENT.md`, `CHANGELOG.md`, `LICENSE` — only if genuinely needed; not produced speculatively.

`README.md` starts as a stub at first epic compile and grows across epics — at each epic close, the verb reconciles `README.md` with what the epic just shipped.

The operator approves README content (it encodes opinions). Drafting is Claude's; the operator must read and approve before commit. See "What stays human" below.

### Refresh state

The final action of every working session: regenerate `/sdlc/STATE.md`. See the STATE.md section below.

## Autonomy gate

A pre-action decision procedure. The default stance is to proceed — escalate only when one of three gates clearly fails or a hard-stop applies. This section governs the _decision_; the session itself is responsible for actually pausing and waiting on the operator.

### When to run

Consult the gate before any action that is **not** on the free-pass list below. The hot path — writing code and tests inside an accepted story's tree — bypasses the gate entirely. Everything else flows through it.

Triggers include scaffolding a project, adding a dependency, choosing or changing a stack component, touching files outside the project tree, calling external systems, modifying CI or infra config, handling secrets, and any case where tests have failed three times on the same step.

### The three-question gate

Answer each in order. Stop and escalate the first time the answer is NO.

**1. Reversible?**
Can a wrong outcome be undone in under a minute, by you, with `git checkout`, `git reset`, deleting a local file, or uninstalling a package — and with no external side effects and no operator cleanup required? If the action writes outside the project tree, mutates an external system, commits a secret, force-pushes, deploys, sends a message, calls a paid API, or creates ongoing cost, the answer is NO.

**2. In-scope?**
Does the action follow directly from one of:

- an accepted user story's acceptance criteria,
- the stack and conventions already locked in for this run,
- a previous operator decision in this session (recorded in `/sdlc/docs/decisions/` or carried in `STATE.md`'s Open questions field)?

If the action requires inventing intent the stories don't dictate — naming the product, choosing the data model, deciding what "fast enough" or "secure enough" means, adding a feature adjacent to but not in a story, picking a default that will become load-bearing — the answer is NO.

**3. Confident?**
Can you describe the next 3–5 concrete steps without guessing at API surfaces, library behavior, schema shape, or operator preference? Have you made fewer than three distinct attempts on this same sub-problem? If you're pattern-matching from training data without verification, or you've already cycled through multiple failed attempts at the same red test, the answer is NO.

If all three are YES, proceed.

### Hard-stop list (always escalate, even if the gate would proceed)

These are the operator's decisions even when individually reversible. Escalating once produces a default the gate can rely on for the rest of the run.

- Choice of language, framework, runtime, datastore, hosting target, package manager, or CI system
- Auth model (session vs token vs OAuth, identity provider, password policy)
- Public API shape — endpoint paths, request/response schemas, versioning policy, error format
- Data model migrations once data exists
- License-significant dependency choices: GPL/AGPL, native bindings, paid SaaS, abandoned packages
- Anything that creates ongoing cost (cloud resources, paid APIs, domains, SSL certs)
- Anything that touches production, real users, real money, or real credentials
- Test failures whose simplest explanation is that the user story itself is wrong, ambiguous, or self-contradictory
- Edits to `CLAUDE.md` or `.claude/settings.json` / `.claude/settings.local.json` — these govern session behaviour itself; each edit requires an operator directive in the current turn

### Free-pass list (proceed without consulting the gate)

The TDD/BDD inner loop. Gating these would defeat the point of the harness.

- Writing or modifying source files inside the project tree to make a failing test pass
- Writing or modifying tests derived from an accepted story's acceptance criteria
- Running tests, linters, formatters, type checkers, and reading their output
- Refactoring within a module to clean up after green tests, with no change to public behavior
- Choosing internal variable names, function decomposition, and file organization inside an existing package
- Reading any file in the project tree, the user story log, or the decisions log

### Escalation interface (minimal)

When the gate fails or a hard-stop applies, stop and send the operator a single message containing:

1. **Action**: what you were about to do, in one sentence.
2. **Why this stopped**: which gate failed (or which hard-stop applied), in one sentence.
3. **Options**: 2–3 viable choices, with one marked recommended and a one-line reason.
4. **Blast radius**: what breaks or has to be unwound if the recommended choice turns out wrong.

Do not take any further action — including "preparatory" work on the chosen option — until the operator has answered.

### Notes

- Operator answers to escalations should land in `/sdlc/docs/decisions/` as ADRs (or, for lighter session-scoped calls, as a resolved entry in `STATE.md`'s Open questions field) so future gate checks can treat them as in-scope defaults.
- "Three attempts" in gate 3 is per sub-problem, not per session. Reset the counter when moving to a new story or a new failing test.
- The free-pass list is deliberately narrow. If you find yourself wanting to add "small infra tweaks" or "obvious config changes" to it, that is a signal the gate is correctly catching scope drift — escalate instead.

## STATE.md — bridge to thinking sessions

`/sdlc/STATE.md` exists because Claude in the chat app cannot read the repo directly. The operator pastes `STATE.md` at the start of any conversation in the chat app that involves this repo. This is the only sanctioned bridge between repo state and architectural conversations elsewhere; do not introduce others without an ADR.

`/sdlc/STATE.md` is regenerated at the end of every Claude Code session and must contain exactly:

    # State — last updated [ISO date]

    **Active focus:** [one line — what's currently being worked on]
    **Last completed:** [id — one line]
    **Next:** [id — one line]

    ## Open questions
    - bullet
    - bullet

Rules:

- Keep `STATE.md` under 30 lines. If it grows beyond a screen it stops getting pasted.
- "Active focus" is whatever shape best describes the current work — could be a story, a task, an epic, a doc compilation, anything. Don't force it into a typed slot.
- The "Open questions" field is the highest-value content. If Claude Code hits something during execution that needs architectural judgment, it goes here. Empty is fine; padding is not.
- When `STATE.md` has no open questions, the operator does not need a thinking session — they need to be in Claude Code executing.

When GitHub MCP becomes reliable in the chat app, `STATE.md` and this section can be removed. The workflow does not change.

## Memory and SDLC artefacts

Claude Code's per-project memory system (`~/.claude/projects/<project>/memory/`) is a fourth persistence layer alongside `STATE.md`, `/sdlc/work/`, and `/sdlc/docs/`. Each layer has a distinct role; they must not duplicate each other.

- **Memory** holds facts about the operator, working norms, and durable feedback that should outlast individual sessions. It is governed by the auto-memory system prompt (types: `user`, `feedback`, `project`, `reference`).
- **STATE.md** is the cross-session bridge: what's active right now, what's next, open questions. Regenerated every session.
- **`/sdlc/work/active/`** is in-flight work. **`/sdlc/work/done/`** is the archive. **`/sdlc/docs/`** is settled record (architecture, decisions, runbooks, strategy).

Boundary rules:

- Memory **references** SDLC artefacts; it does not duplicate their content. A memory entry can say "see ADR 0001" but should not restate the ADR's decision.
- Memory must not contradict CLAUDE.md, SDLC.md, or any ADR. If a memory disagrees with the canonical document, the canonical document wins and the memory is updated or removed.
- Project-state facts that change session-to-session (active focus, last completed, next) belong in `STATE.md`, not memory. Memory is for facts that survive across many sessions.
- Architectural decisions belong in `/sdlc/docs/decisions/` as ADRs, not as `project` or `reference` memory entries. Memory may point at the ADR; the decision lives in the file.

When in doubt, prefer the SDLC artefact over the memory entry. Memory is a convenience; the filesystem is the source of truth.

## Status discipline

- An artefact in `/sdlc/work/active/` is `active` if it's being worked on, `blocked` with a `blocker:` field if it isn't, `done` only when complete.
- A task is `done` only when tests pass, the diff is committed, and the verifier has signed off. If the gate escalated at any point during the task, the operator's decision must be recorded before the task closes.
- A story is `done` when all its child tasks are done and the spec's acceptance criteria are met.
- Done artefacts move from `/sdlc/work/active/` to `/sdlc/work/done/`.
- Doc artefacts in `/sdlc/docs/` carry `verified-on:` rather than status. They're either current (verified recently) or stale (not).

## Hard rules for Claude Code

1. **Read `/sdlc/SDLC.md` and `CLAUDE.md` at the start of every session.** No exceptions.
2. **Never start coding without a task artefact.** If the operator asks for code directly, propose compiling it into a task first.
3. **Never write implementation before tests.** If there's no test spec, update the plan first.
4. **Never mark a task done without verifier sign-off.** If the gate escalated during the task, the operator's decision must be on record before close.
5. **Never edit an artefact's `id` field.** IDs are stable.
6. **Never introduce an external tracker.** If the operator suggests it, require an ADR documenting the decision.
7. **Never skip filing for architectural changes.** The next session depends on it.
8. **Never end a working session without regenerating `/sdlc/STATE.md`.**
9. **Never let `/sdlc/raw/` accumulate beyond 20 items without prompting the operator to compile.**
10. **Never delete from `/sdlc/raw/` without first producing a compiled artefact that references it as a source.** Compilation absorbs raw material; it doesn't discard it silently.
11. **Trust the document.** If a question can be answered by reading `/sdlc/SDLC.md`, `CLAUDE.md`, or any artefact already in the repo, read it and proceed. Do not ask the operator. Asking questions the repo answers is a failure mode, not a courtesy.
12. **Trust the operator's instruction.** When the operator gives a clear directive ("do X to all Y"), execute it. Do not ask for re-confirmation of the directive itself. Ask only if a specific item genuinely needs disambiguation, and ask once — not per item.
13. **No re-asking.** If the operator has answered a question once in this session, do not ask it again in any phrasing. Re-asking signals the prior answer wasn't trusted or wasn't retained. If genuinely unsure, state the prior answer back and confirm — do not start over.
14. **Never bypass the gate.** If any of the three questions answers NO, stop and use the escalation interface. Stretching a YES to cover scope it doesn't, or acting on a NO without operator approval, is a discipline failure.
15. **Never proceed on a hard-stop without explicit operator decision in the current session.** A previous session's approval does not carry forward.
16. **Run the Pre-flight checklist at session 1 of a new SDLC project.** No exceptions. The checklist is in the Pre-flight section.
17. **Run the `document` verb at epic close.** An epic in `/sdlc/work/done/` without a current `README.md` reflecting what shipped is incomplete and must be reopened.
18. **Verify publication state at epic close.** If a publication target was chosen at session 1, `git remote -v` must be non-empty and `git log @{u}..HEAD` must be empty before the epic moves to `done/`. If not, pause and report.
19. **Audit dormant skills periodically.** If 10+ messages have passed in a session without a loaded skill being invoked, suggest the operator disable it via `/plugin`. Skills foundational to this repo's workflow are exempt — at minimum the project's `sdlc` skill itself; the operator declares any others.
20. **Commit at task boundaries.** Each task close ends in a commit before the next task begins. Starting a new task with uncommitted work from the previous one mixes diffs, breaks the verifier's spec→diff alignment check, and forces re-sequencing. No exceptions.
21. **Run the pre-dispatch verifier self-check.** Before invoking the verifier sub-agent, walk the spec's AC bullets and confirm each has evidence in the diff. Skipping the self-check is the single largest source of verifier round-trips.
22. **Auto-progress within a story; pause at the boundary.** When a task closes cleanly (verifier signed off, commit landed, no unresolved gate escalations), begin the next `active` task in the same story without waiting for operator approval. Do not auto-cross the story boundary — pause at story close and let the operator decide. Halt the loop on verifier failure, gate escalation, hard-stop, or any operator directive to pause or change course.
23. **Save a `feedback` memory when a CLAUDE.md or SDLC.md guideline gets violated within a session.** Documentation alone is not enough — documented rules can slip across long execution stretches. When the operator catches a violation (or you catch one mid-session), save a `feedback` memory codifying the rule with `Why:` (the rule's source and the incident that triggered the save) and `How to apply:` (the concrete signal that should trigger compliance). The memory makes the rule load as operator-given feedback in future sessions rather than only via documentation reading.
24. **Audit the Bash allowlist at session close.** If three or more permission prompts fire during a session for commands that the autonomy gate's free-pass list considers safe (running tests/lint/build/format, reading files inside the project, internal git inspection), batch them through the `fewer-permission-prompts` skill. The operator approves the proposed additions before they land in `.claude/settings.json`. Below the three-prompt threshold, take the prompts and move on rather than churning the allowlist with speculative entries.

## What stays human

The operator decides:

- compilation outcomes — Claude proposes, operator approves
- plan approval — Claude proposes, operator edits, operator approves
- gate escalations and hard-stop decisions — Claude reports per the escalation interface, operator decides; decisions are then recorded so future gate checks can treat them as in-scope defaults
- verifier sign-off when the verifier flags issues — Claude reports, operator decides
- `CLAUDE.md` edits and any change to `.claude/settings.json` or `.claude/settings.local.json` — these encode opinions, permissions, and harness behaviour. Claude may draft specific changes but never writes to these files without explicit operator approval in the current turn. A previous directive does not authorise a later edit.
- ADRs — Claude can draft, operator must approve
- README content — encodes opinions; must sound like the operator. Operator approves drafts before commit.
- `git push` to remote — Claude drafts commit messages and the push command; the operator runs the push. An earlier `gh repo create --push` or any prior session's push is _not_ implicit authorization for subsequent pushes. Each `git push` requires an explicit operator instruction in the current turn.
- Release tags — Claude proposes; the operator approves and creates.

## What runs without further approval

Within an approved task spec, Claude executes freely:

- writing tests as specified
- writing implementation against tests
- iterating on test failures
- updating documentation when behaviour changes
- generating runbook updates
- regenerating `/sdlc/STATE.md`
- proposing the next compilation, plan, or task
- on tasks that pass verification with no unresolved gate escalations: marking the task done and moving it to `/sdlc/work/done/`
- after a task closes cleanly, starting the next `active` task under the same parent story (auto-progress; see Execute). Stop at the story boundary.
- drafting README content (operator approves before commit)
- drafting commit messages and tag names

## Scaling note

This SDLC works for a single operator with AI agents. When a second human joins the loop, the substrate may need to change (filesystem → tracker), but the workflow stays identical: capture raw, compile into shape, plan when shape requires it, execute with tests-first, verify with fresh context, file outputs back, refresh state on exit. Migrating substrate is a one-time mechanical change; migrating workflow would be a rebuild.

## References

External thinking that informed this SDLC:

- Spec-Driven Development (arXiv 2602.00180) — spec-anchored is the practical middle between vibe coding and full waterfall.
- Anthropic internal practice — fresh-context PR review by a separate Claude instance.
- Augment Code's Coordinator / Implementor / Verifier pattern.
- Andrej Karpathy's LLM-managed wiki pattern — raw sources compiled by an LLM into structured artefacts; structure emerges from content rather than being imposed upfront. This SDLC adapts that pattern from knowledge management to development work.
- Loose-coupling, shared-edges principle from Reimagined Industries' Agent OS architecture, applied to the workflow itself.
- Mark Stretfford's original SDLC harness: https://github.com/markstrefford/claude-skills/tree/main/sdlc
