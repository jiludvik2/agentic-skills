---
title: Reimagined Software Delivery Lifecycle
purpose: How Claude Code should approach all development work in this repo
version: 6.6
updated: 2026-05-28
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

## Directory layout

    /sdlc/
      raw/                    unstructured capture, no rules
      work/
        active/               things being worked on, any shape
        done/                 archived
      docs/
        architecture/         long-standing architectural docs
          stack-pins.md       canonical pin list (runtime, libs, tools, security floors)
        strategy/             strategy docs
        decisions/            ADRs, point-in-time decisions
        runbooks/             operational guides
      SDLC.md                 this file
      STATE.md                current state, regenerated at session end
    /.claude/
      agents/                 sub-agent definitions (verifier, reviewer, etc.)
    CLAUDE.md                 repo-level context, points to /sdlc/SDLC.md
    [project code lives at root or in src/, etc.]

`/sdlc/raw/` holds anything captured. `/sdlc/work/` holds compiled artefacts being acted on. `/sdlc/docs/` holds compiled artefacts that explain the system. Items move between these by being compiled, not by being filed.

`.claude/` and `CLAUDE.md` stay at repo root because Claude Code's auto-discovery expects them there. `CLAUDE.md` should contain a one-line pointer to `/sdlc/SDLC.md` so the workflow is discoverable from the root entry point.

**`/sdlc/work/done/` shape.** The default is one file per artefact, matching how it was structured in `/sdlc/work/active/`. For bulk historical imports (pre-SDLC done items, legacy changelog entries), a single consolidated file is acceptable — name it `done-historical.md` or similar. Going forward under the SDLC, new done items get their own files.

**Pre-existing content.** Files that pre-date the SDLC (legacy backlogs, changelogs, scratch docs) are treated as raw material to be compiled. They live where they currently live until compilation moves them. Compilation of legacy content follows the same rules as compilation of `/sdlc/raw/` items: each item becomes a compiled artefact in the right destination, or is discarded, or is parked. Nothing is moved without being compiled.

**`stack-pins.md`** is the canonical, greppable pin list — flat tables by stack layer, not prose. Architecture explains *why* a pin was chosen; this file is the authoritative *what*. Created by the first compile cycle of a new project (not by any session-start ritual); every later pin decision lands here in the same commit as its justifying ADR or arch edit. No `stack-pins.md` ⇒ no dependency installs — escalate to capture/compile first.

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

**Review-spawned fix tasks** extend their parent's id with `-fix<N>-<slug>` where `N` is the remediation round number. Examples: `s1-t3-fix1-concurrent-retry-loop` (round-1 fix from a per-task Review on `s1-t3-transition-service`); `s1-t3-fix2-loop-exit-condition` (round-2 fix); `s1-fix1-telemetry-consistency` (round-1 fix from a story-level Review on `s1-state-machine-per-unit`). The `-fix` convention denotes auto-filed Review output; the older `-fu-` convention remains for human-discovered follow-ups filed manually.

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

**New-project first compile.** For a project starting from raw material (stories and/or architecture draft in `/sdlc/raw/`), the first compile cycle produces, in this order, in a single commit:

1. `adr-0001-publication.md` — publication target (github / gitlab / private host / nowhere; public/private; account/org; license). Captures the one-shot setup decision that previously lived in pre-flight.
2. Compiled architecture document → `/sdlc/docs/architecture/<project>-architecture.md`.
3. `stack-pins.md` — harvested verbatim from the architecture's pin sections.
4. ADRs for major stack choices → `/sdlc/docs/decisions/adr-NNNN-*.md`.
5. Stories/epics → `/sdlc/work/active/*.md`, each referencing the architecture sections they exercise.

Before proposing the compile plan, read all `/sdlc/raw/` material end-to-end and surface (a) coverage gaps between stories and architecture, (b) pins discovered in the raw architecture for operator confirmation, (c) decisions that should become ADRs. Once the compile commit lands, rule #1b's reconciliation trigger fires and the project manifest is synced against the new `stack-pins.md`.

### Plan

For an artefact in `/sdlc/work/active/` whose `kind` is `story` or `epic`, produce a task sequence. Each task entry must include:

- one-line outcome
- acceptance criteria
- test specification (defined before implementation)

Tasks are written as their own files in `/sdlc/work/active/` with `parent:` linking to the story. The plan is committed alongside the story. The operator reviews and edits the plan before execution.

**BDD-deferral annotations.** When a story's BDD or user-stories source references functionality that ships in a later story, the story spec must list the deferred items explicitly with the target story (e.g. "filter by status — deferred to s5"). The deferral belongs in acceptance criteria, not buried in task notes — otherwise the verifier will flag missing coverage that was never in scope, burning a round-trip.

### Execute

Act on a task. Tests first, then implementation. Claude writes the tests defined in the task spec, confirms they fail, then implements until they pass. No skipping tests. No "I'll add tests later." If the task spec didn't define tests, stop and update the plan.

When the task is complete: update `status: done`, commit with a message referencing the task id (e.g. `task-12: extract simulation engine module`), move the file to `/sdlc/work/done/`. Closing a task means Verify and Review have both signed off — see those verbs below.

**Auto-progress within a story.** Once a task closes cleanly — verifier signed off, reviewer signed off (CLEAN, MINOR-ONLY, or HAS-CRITICAL-OR-IMPORTANT with all such findings spawned as fix tasks), no unresolved gate escalations, commit landed — immediately begin the next `active` task under the same parent story without waiting for further operator approval. The operator approved the plan; executing the plan is what that approval covers. Review-spawned fix tasks slot into the front of the remaining task queue under their parent and are auto-progressed the same way, subject to rule #25's 2-round remediation bound. At the **story boundary** — when the last task of the story closes cleanly — run the story-level Review (Verify is implicit per-task and not re-run on the cumulative diff), remediate any Critical/Important findings via the same auto-progress chain, then **auto-progress into the next `active` story under the same epic without waiting for operator approval, provided that next story already has an operator-approved plan** (operator-approved story-boundary auto-cross). If the next story is unplanned, propose its plan and pause — plan approval stays human (see "What stays human"). Stop the loop at the **epic boundary**: when the last story of the epic closes cleanly, pause and report; the operator decides whether to start the next epic.

The loop also halts immediately on any of: verifier failure, reviewer's 2-round bound exceeded, an Autonomy-gate escalation, a hard-stop trigger, three failed attempts on the same sub-problem, **context-window usage at or above 75%** (read from the per-session transcript JSONL at `~/.claude/projects/<slug>/<session-uuid>.jsonl`: sum `input_tokens + cache_read_input_tokens + cache_creation_input_tokens` on the most recent assistant turn, divide by the active model's context window — default 200K; threshold configurable per project), or any operator directive ("pause", "stop", "hold on", or any instruction to do something else). Operator interruption always wins over auto-progression — there is no "let me finish this task first."

**Wrap on halt.** At every halt except operator interruption, the Wrap verb runs automatically before control returns to the operator. The context-pressure halt is the one trigger that branches on mid-task state: if it fires between tasks (no task is in mid-execution; working tree clean from the last task close), Wrap runs and the operator gets a `/clear`-and-resume suggestion; if it fires mid-task (a task is in mid-execution, with uncommitted work or an in-progress test loop), the loop halts and reports without wrapping — the operator drives Wrap explicitly so the in-flight handoff (Wrap step 3) can be authored with judgement about WIP-commit vs stash.

Within a task, consult the Autonomy gate before any action that isn't on the gate's free-pass list. Verify and Review still run at task close.

**Snapshot script as per-task checkpoint.** For projects with significant UI surface — pages exercising routing, dynamic rendering, or per-route configs — run the snapshot/screenshot script after each significant page change rather than only at story close. Compile-time issues that surface only on second-route-load (e.g. ESM/CJS interop bugs in framework configs) otherwise hide until story close, where the cost of disentangling them is highest.

### Verify

**Pre-dispatch self-check (mandatory).** Before invoking the verifier, walk the spec's acceptance criteria one by one and confirm each has corresponding evidence in the diff: a test, a render assertion, an integration check. For every new component or module, confirm a render or unit test exists. This costs ~2 minutes; missing it triggers FIX-AND-RESUBMIT cycles that cost ~20 minutes each and burn a verifier round on a gap a self-scan would have caught in seconds.

Then invoke the `verifier` sub-agent (defined in `.claude/agents/verifier.md`). It reads the spec, the plan, and the diff with no memory of how the implementation was built. It reports alignment, test coverage, architectural drift, and code smells at the AC level.

The operator reviews the verifier output. Pass → continue to Review (below). Fail → fix or kick the task back to active.

The verifier is non-negotiable. It is one of the two highest-leverage steps in the loop and the most consistently skipped.

### Review

After Verify passes, invoke the `reviewer` sub-agent (defined in `.claude/agents/reviewer.md`). It reads the diff, the spec, and the architectural context with no memory of how the implementation was built and reports **code-quality findings classified by severity**. Future scope includes security review and (potentially) architecture review as additional dispatch modes of the same sub-agent.

The reviewer is the *complement* to the verifier — not a replacement. Verify asks "did you build the right thing?" (AC alignment, test coverage). Review asks "did you build it well?" (quality, smells, eventually security and architecture).

**Severity taxonomy.**

- **Critical** — breaks correctness, security, or contract. Wrong behaviour on supported inputs, race condition, secrets leak, immutability violation, SoD/auth weakened, breaking API change.
- **Important** — real defect, ship-blocker for this story. Error-handling gap at a system boundary, missing input validation, inconsistent state handling across endpoints, regression against a spec'd NFR that Verify did not measure, missing required telemetry.
- **Minor** — code smell that doesn't block ship. Duplication, unclear naming, dead code, what-not-why comments, magic numbers without rationale.
- **Nit** — preference or style. Formatting, alternative phrasings.

**Auto-remediation.**

- **Critical** and **Important** findings → auto-file fix tasks as siblings under the same parent story; auto-kickoff per rule #22.
- **Minor** findings → captured in the parent task's `notes:` field for opportunistic cleanup. Not filed as tasks.
- **Nit** findings → dropped from the filed output.

Fix tasks carry `parent:` pointing to the parent story, `sources:` pointing to the reviewer's output, and an `id` following the `<parent-id>-fix<N>-<slug>` convention from the File conventions section. They are inserted at the front of the remaining task queue under the parent story (auto-progress handles them next).

**Recursion bound (rule #25).** Each remediation chain is bounded at 2 rounds.

- **Round 1** — fix tasks filed for the original Critical/Important findings.
- **Round 2** — if round-1 fix tasks themselves produce Critical/Important findings on their own Review pass, those become round-2 fix tasks.
- If a **round 3** would be needed (round-2 fix tasks produce Critical/Important findings on *their* Review pass), halt via the Autonomy gate's escalation interface. The operator decides whether to keep iterating, accept the findings as known debt (record in an ADR or in the parent task's notes), or rework the parent task.

The bound applies per finding chain, not per task — distinct round-1 findings can have independent round-2 fix tasks running in parallel, but no chain extends past round 2 without operator approval.

**Per-task vs story-level review.**

- **Per-task review** runs after every task's Verify pass. It looks at the task's diff in isolation.
- **Story-level review** runs after the last task in a story closes cleanly. It looks at the cumulative story diff and specifically targets considerations that cut across multiple tasks: architectural drift accumulated across tasks, redundant code patterns appearing in different modules, inconsistent error-handling or telemetry across endpoints, test-coverage gaps spanning task boundaries, missing cross-cutting concerns (logging, OTel attributes, idempotency). Same severity taxonomy and same auto-remediation rules.

Story-level review gates the story boundary: the story does not close (and the auto-progress loop does not pause for the operator) until all Critical/Important story-level findings — and their bounded fix-task chains — have been remediated.

The reviewer, like the verifier, is non-negotiable. It is the second of the two highest-leverage steps in the loop. Both sub-agents run once per dispatch; the SDLC owns the loop.

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

**Publication.** If a publication-target ADR exists (`adr-0001-publication.md` or equivalent) specifying a remote target (GitHub, GitLab, etc.), `file` _proposes_ the remote-setup commands once the first commit lands (`gh repo create …` or equivalent, then `git push -u origin main`). The operator approves and runs commands that affect remote state; Claude may execute purely-local git operations.

At epic close, `file` verifies:

- `git remote -v` shows a configured remote (if the publication ADR specifies one).
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

### Wrap

The final action of every working session, before `/clear` or session exit. A three-step routine — step 1 always; steps 2 and 3 fire only when applicable, and most sessions skip them.

**1. STATE refresh** (always). Update `/sdlc/STATE.md` so its three header lines (`Active focus`, `Last completed`, `Next`) reflect reality at session end, and any open question raised this session lands in the **Open questions** field. This subsumes the earlier **Refresh state** verb.

**2. Memory sweep** (only when applicable). If anything non-obvious surfaced during the session that isn't already in an artefact or commit — a gotcha, a workaround, a stack quirk, a tooling pitfall — file one memory entry per item per the project's memory rules. Skip when nothing surprising came up; most sessions skip this step.

**3. In-flight handoff** (only when applicable). If `git status` shows uncommitted edits or a task is mid-implementation, append a short handoff to `/sdlc/STATE.md` above **Open questions**:

    ## In-flight: <task-id>
    Next step: <one-sentence action>.  WIP in: <stash id | branch | wip-commit hash>.

If the working tree is too messy to leave, `git stash push -u -m "<task-id> wip"` first; reference the stash id in **WIP in**. If the in-flight state is committable as an intermediate checkpoint, a `wip: <task-id> — see STATE handoff` commit is acceptable — but the verifier will reject the WIP commit at task close, so the work must still be replaced by a real commit before closure.

**Automatic firing.** Wrap also runs automatically at every auto-progress halt where the operator did not initiate the halt themselves — verifier failure, reviewer's 2-round-bound exceeded, gate escalation, hard-stop, three failed attempts, and the context-pressure halt when it fires between tasks (per the Execute verb's halt list). At those halts, Wrap runs before control returns to the operator, so `STATE.md` is current the moment they look at it. Two exceptions where Wrap does **not** auto-fire: (a) operator interruption — the operator already has control and may redirect immediately, so Wrap doesn't pre-empt; (b) the context-pressure halt when a task is mid-execution — the in-flight handoff stays operator-driven, since the WIP-commit-vs-stash decision needs human judgement.

Wrap does **not** include `/clear` — the operator chooses when (and whether) to clear. Wrap prepares; it doesn't clear. At the context-pressure halt between tasks, Wrap closes with a one-line `/clear`-and-resume suggestion that the operator can act on or ignore.

## Autonomy gate

A pre-action decision procedure. The default stance is to proceed — escalate only when one of three gates clearly fails or a hard-stop applies. This section governs the _decision_; the session itself is responsible for actually pausing and waiting on the operator.

### When to run

Consult the gate before any action that is **not** on the free-pass list below. The hot path — writing code and tests inside an accepted story's tree — bypasses the gate entirely. Everything else flows through it.

Triggers include scaffolding a project, adding a dependency, choosing or changing a stack component, touching files outside the project tree, calling external systems, modifying CI or infra config, handling secrets, and any case where tests have failed three times on the same step.

### The three-question gate

Answer each in order. Stop and escalate the first time the answer is NO.

**1. Reversible?**
Can a wrong outcome be undone in under a minute, by you, with `git checkout`, `git reset`, deleting a local file, or uninstalling a package — and with no external side effects and no operator cleanup required? If the action writes outside the project tree, mutates an external system, commits a secret, force-pushes, deploys, sends a message, calls a paid API, or creates ongoing cost, the answer is NO.

**Sandbox note.** If the project enables an OS sandbox for Bash (e.g. `.claude/settings.json` → `sandbox`), a command that runs to completion *inside* the sandbox is reversible by construction — its writes are confined to the project tree and it has no network egress beyond the allow-list — so it answers Reversible? YES automatically. A command that must escape the sandbox (write outside the tree, reach a non-allow-listed domain) fails inside it and re-enters this gate via the permission prompt; that prompt is the escalation. Some toolchains cannot run under the sandbox and must be excluded from it (record which, and why, in an ADR); excluded commands are *not* contained and are judged on their own merits, exactly as before the sandbox existed.

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
- **(when an OS sandbox is enabled)** Any Bash command that runs to completion inside the sandbox — writes confined to the project tree, no egress beyond the allow-list. Containment is the reversibility guarantee (see Gate 1's Sandbox note). This subsumes the test/lint/format/typecheck/read commands above for the contained case. Commands **excluded** from the sandbox are not contained and remain subject to the gate.
- Adding a **non-license-significant** dependency (permissive licence, not paid SaaS, not abandoned) that an accepted story's acceptance criteria imply, *provided* it is pinned in `stack-pins.md` in the same commit; and internal-only library/module choices that do not change the runtime, framework, datastore, or public API (also recorded in `stack-pins.md`). The pin record preserves the audit trail. The major-stack hard-stop (language/framework/runtime/datastore/package-manager/CI) and the license-significant-dependency hard-stop are unchanged.

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

`/sdlc/STATE.md` is regenerated by the **Wrap** verb at the end of every Claude Code session and must contain at minimum:

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
- A task is `done` only when tests pass, the diff is committed, the verifier has signed off, and the reviewer has signed off (verdict `CLEAN` or `MINOR-ONLY`, or `HAS-CRITICAL-OR-IMPORTANT` with every Critical/Important finding already spawned as a fix task). If the gate escalated at any point during the task, the operator's decision must be recorded before the task closes.
- A story is `done` when all its child tasks are done, the spec's acceptance criteria are met, and the story-level Review has signed off with no unresolved Critical/Important findings.
- Done artefacts move from `/sdlc/work/active/` to `/sdlc/work/done/`.
- Doc artefacts in `/sdlc/docs/` carry `verified-on:` rather than status. They're either current (verified recently) or stale (not).

## Hard rules for Claude Code

1. **Session-start protocol.** In order, at the start of every session:
   - **1a.** Read `/sdlc/SDLC.md` and `CLAUDE.md` in full. No exceptions.
   - **1b. Stack reconciliation.** If `/sdlc/docs/architecture/stack-pins.md` exists, diff it against the project manifest (`pyproject.toml`, `package.json`, etc.), add missing pins, run the sync command, verify — before any other work. Pins are source of truth; the manifest tracks them. Also runs after any commit touching `stack-pins.md` within a session.
   - **1c. Memory snapshot.** List any per-project memory entries (`~/.claude/projects/<project>/memory/MEMORY.md`); flag any that contradict current repo state, name moved files, or duplicate compiled artefacts. Resolve before continuing — stale memory is worse than no memory.
   - **1d.** Read `/sdlc/STATE.md`. If absent (session 1 of a new project), create it with a "Session 0" entry capturing session time and which raw material exists in `/sdlc/raw/` awaiting compile.
2. **Never start coding without a task artefact.** If the operator asks for code directly, propose compiling it into a task first.
3. **Never write implementation before tests.** If there's no test spec, update the plan first.
4. **Never mark a task done without verifier AND reviewer sign-off.** If the gate escalated during the task, the operator's decision must be on record before close. If Review found Critical or Important findings, those must have been spawned as fix tasks (or, if rule #25's 2-round bound was hit, escalated to the operator) before close.
5. **Never edit an artefact's `id` field.** IDs are stable.
6. **Never introduce an external tracker.** If the operator suggests it, require an ADR documenting the decision.
7. **Never skip filing for architectural changes.** The next session depends on it.
8. **Never end a working session without running the Wrap verb** — which regenerates `/sdlc/STATE.md` and, when applicable, files a memory sweep and/or an in-flight handoff for uncommitted work.
9. **Never let `/sdlc/raw/` accumulate beyond 20 items without prompting the operator to compile.**
10. **Never delete from `/sdlc/raw/` without first producing a compiled artefact that references it as a source.** Compilation absorbs raw material; it doesn't discard it silently.
11. **Trust the document.** If a question can be answered by reading `/sdlc/SDLC.md`, `CLAUDE.md`, or any artefact already in the repo, read it and proceed. Do not ask the operator. Asking questions the repo answers is a failure mode, not a courtesy. **Stack/tooling sub-rule:** before any AskUserQuestion about a language, runtime, package manager, library version, lint/test/build tool — read `stack-pins.md` (if present) and grep `/sdlc/docs/` for pin/stack/toolchain sections in full. State the search in the question preamble. If pins are silent, do not improvise: capture the question into `/sdlc/raw/` and propose an ADR + `stack-pins.md` update. Stack decisions go through capture→compile, not in-the-moment Q&A.
12. **Trust the operator's instruction.** When the operator gives a clear directive ("do X to all Y"), execute it. Do not ask for re-confirmation of the directive itself. Ask only if a specific item genuinely needs disambiguation, and ask once — not per item.
13. **No re-asking.** If the operator has answered a question once in this session, do not ask it again in any phrasing. Re-asking signals the prior answer wasn't trusted or wasn't retained. If genuinely unsure, state the prior answer back and confirm — do not start over.
14. **Never bypass the gate.** If any of the three questions answers NO, stop and use the escalation interface. Stretching a YES to cover scope it doesn't, or acting on a NO without operator approval, is a discipline failure.
15. **Never proceed on a hard-stop without explicit operator decision in the current session.** A previous session's approval does not carry forward.
16. **First-compile completeness for new projects.** A project's first compile cycle must produce `adr-0001-publication.md` (or equivalent publication-target ADR) and, if any architectural raw material exists, `stack-pins.md` — both before any commit that could be pushed. The session-start protocol (rule #1) handles per-session work; rule #16 enforces the one-time new-project setup that previously lived in pre-flight.
17. **Run the `document` verb at epic close.** An epic in `/sdlc/work/done/` without a current `README.md` reflecting what shipped is incomplete and must be reopened.
18. **Verify publication state at epic close.** If a publication-target ADR exists (`adr-0001-publication.md` or equivalent) with anything other than "nowhere" as the target, `git remote -v` must be non-empty and `git log @{u}..HEAD` must be empty before the epic moves to `done/`. If not, pause and report.
19. **Audit dormant skills periodically.** If 10+ messages have passed in a session without a loaded skill being invoked, suggest the operator disable it via `/plugin`. Skills foundational to this repo's workflow are exempt — at minimum the project's `sdlc` skill itself; the operator declares any others.
20. **Commit at task boundaries.** Each task close ends in a commit before the next begins — uncommitted carryover mixes diffs and breaks the verifier's spec→diff alignment. No exceptions.
21. **Run the pre-dispatch verifier self-check** (see the Verify verb) before every verifier dispatch — the single largest source of verifier round-trips.
22. **Auto-progress within a story, and across already-planned stories within an epic; pause at the epic boundary.** Full close-clean conditions, the unplanned-next-story pause, and the halt triggers live in the Execute verb (operator-approved auto-cross).
23. **Save a `feedback` memory when a CLAUDE.md/SDLC.md guideline is violated in a session** (operator-caught or self-caught). Codify the rule with `Why:` (source + triggering incident) and `How to apply:` (the signal that should trigger compliance), so it loads as operator feedback in future sessions, not only via doc-reading.
24. **Audit the Bash allowlist at session close.** If ≥3 permission prompts fired for free-pass-safe commands (tests/lint/build/format, project reads, internal git), batch them through the `fewer-permission-prompts` skill (operator approves additions). Below 3, take the prompts — don't churn the allowlist with speculative entries.
25. **Bound code-review remediation at 2 rounds per finding chain** — a needed round 3 halts via the gate's escalation interface for an operator call (iterate / accept as debt / rework). Mechanics in the Review verb.
26. **Run the project's supply-chain/security gate at story close and record the result.** If the project defines a dependency-audit or security gate (e.g. a `make audit` target wrapping `pip-audit`, or `npm audit`, `cargo audit`, or equivalent), run it before a story moves to `/sdlc/work/done/` and record the outcome — pass or allow-listed exceptions — in the close notes or closure commit. A non-clean result blocks closure unless every finding is allow-listed with a rationale and an expiry. Where CI enforces the same gate on PRs/`main`, this rule makes the evidence explicit at the story boundary. Projects with no such gate skip this rule until one is introduced (via an ADR).

## What stays human

The operator decides:

- **Compilation outcomes** and **plan approval** — Claude proposes (and edits on request); the operator approves.
- **Gate escalations and hard-stop decisions** — Claude reports per the escalation interface; the operator decides, and the decision is recorded so future gate checks treat it as an in-scope default.
- **Verifier sign-off when the verifier flags issues**, and **reviewer rule-#25 2-round-bound escalations** — Claude reports, operator decides.
- **`CLAUDE.md` and `.claude/settings*.json` edits** — these encode permissions and harness behaviour; Claude may draft but never writes without explicit operator approval in the current turn (a previous directive does not authorise a later edit).
- **ADRs and README content** — Claude drafts; the operator approves before commit (README must sound like the operator).
- `git push` — governed by the repo's `CLAUDE.md` push policy, if it has one. A policy may pre-authorise push to `origin` after each local commit, but **force-push, branch deletion, and any non-`origin` remote always require explicit per-turn authorisation.** Repos without such a policy fall back to operator-runs-the-push.
- Release tags — Claude proposes; the operator approves and creates.

## What runs without further approval

Within an approved task spec, everything the **verbs** describe runs without further approval — tests-first implementation and iteration, behaviour-driven doc and runbook updates, the Verify and Review dispatches and their auto-remediation (filing `*-fix<N>-*` tasks per the Review verb, marking tasks done, moving them to `/sdlc/work/done/`), and **auto-progress** per the Execute verb — together with everything on the Autonomy gate's **free-pass list**. Claude also regenerates `/sdlc/STATE.md`, proposes the next compile/plan/task, and drafts README content, commit messages, and tag names (the operator approves README and tags before they land).

## Scaling note

This SDLC works for a single operator with AI agents. When a second human joins the loop, the substrate may need to change (filesystem → tracker), but the workflow stays identical: capture raw, compile into shape, plan when shape requires it, execute with tests-first, verify with fresh context, review with fresh context, file outputs back, refresh state on exit. Migrating substrate is a one-time mechanical change; migrating workflow would be a rebuild.

## References

External thinking that informed this SDLC:

- Spec-Driven Development (arXiv 2602.00180) — spec-anchored is the practical middle between vibe coding and full waterfall.
- Anthropic internal practice — fresh-context PR review by a separate Claude instance.
- Augment Code's Coordinator / Implementor / Verifier pattern.
- Andrej Karpathy's LLM-managed wiki pattern — raw sources compiled by an LLM into structured artefacts; structure emerges from content rather than being imposed upfront. This SDLC adapts that pattern from knowledge management to development work.
- Loose-coupling, shared-edges principle from Reimagined Industries' Agent OS architecture, applied to the workflow itself.
- Mark Stretfford's original SDLC harness: https://github.com/markstrefford/claude-skills/tree/main/sdlc
