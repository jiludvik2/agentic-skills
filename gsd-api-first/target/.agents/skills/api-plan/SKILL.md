---
name: api-plan
description: "Run gsd-plan-phase for phases that touch the API surface, with the phase API-SPEC.md and any project API governance documents auto-discovered and injected as planner context. Use instead of /gsd-plan-phase for any phase that adds or modifies API endpoints."
argument-hint: "<phase> [gsd-plan-phase flags: --auto --skip-research --research --tdd --mvp ...]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Agent
  - AskUserQuestion
  - WebFetch
  - mcp__context7__resolve-library-id
  - mcp__context7__query-docs
---

<objective>
Thin wrapper around `gsd-plan-phase` that auto-discovers the project's API design contract (API-SPEC.md) and any API governance documents (ADRs, API standards, architecture docs), then injects them as `--ingest` sources so the planner sees the locked contract without manual flag passing.

**Problem solved:** Without this skill, the planner only sees governance docs if you remember `--ingest` on every API phase. Under pressure that step gets dropped, and the planner makes implementation decisions that conflict with the design contract — the exact failure mode contract-first design exists to prevent.

**Use after:** `/api-phase <N>` has produced and committed `XX-API-SPEC.md`.
**Use instead of:** `/gsd-plan-phase <N>` for any phase that adds or modifies the API surface.

**Pass-through:** All flags valid for gsd-plan-phase (`--auto`, `--skip-research`, `--research`, `--tdd`, `--mvp`, `--skip-verify`, etc.) are forwarded verbatim.
</objective>

<context>
Arguments: $ARGUMENTS

First token is the phase number. Remaining tokens are extra flags for gsd-plan-phase.
</context>

<process>
## Step 1 — Parse arguments

Split $ARGUMENTS on whitespace. The first token is the phase number. Remaining tokens are extra flags for gsd-plan-phase. If $ARGUMENTS is empty, ask the user for the phase number.

## Step 2 — Resolve phase and locate API-SPEC.md

Find the phase directory under `.planning/phases/` matching the phase number (by numeric prefix). Check whether `{phase_dir}/XX-API-SPEC.md` exists. Note the result.

## Step 3 — Discover API governance documents

Search the project in parallel for documents that constrain API design decisions. Include only files that actually exist:

**Decision records:**
- `docs/adr/*.md`, `adr/*.md`, `docs/decisions/*.md`, `decisions/*.md`

**Architecture and standards docs:**
- `docs/STANDARDS.md`, `docs/standards.md`
- `docs/ARCHITECTURE.md`, `docs/architecture.md`
- `docs/API.md`, `docs/api.md`, `docs/api-*.md`

**Prior API contracts from earlier phases (established patterns):**
- `.planning/phases/*/[0-9][0-9]-API-SPEC.md` — exclude the current phase's spec (it's already the primary source)

Print the list of discovered files so the user can confirm what's being loaded.

## Step 4 — Warn on missing API-SPEC.md

If `XX-API-SPEC.md` does not exist for this phase, print:

> ⚠️  No API-SPEC.md found for phase XX. Run `/api-phase XX` first to produce the API design contract. The planner will have no locked contract to plan against.

Ask: "Continue without a contract (governance docs only), or stop and run /api-phase first?"

If the user confirms: proceed. If governance docs AND API-SPEC.md are both absent, warn more strongly:

> ⚠️  No API-SPEC.md and no API governance documents found. The planner will have no API design context. The resulting plan may not honour REST best practice.

Confirm before proceeding.

## Step 5 — Build ingest source list

Order:
1. `{phase_dir}/XX-API-SPEC.md` — first, if present (most specific, highest priority)
2. Governance docs from Step 3 — in discovery order

## Step 6 — Invoke gsd-plan-phase

Use the Skill tool to invoke `gsd-plan-phase` with:
- Phase number as parsed
- One `--ingest <path>` per source in the Step 5 list
- All extra flags from Step 1 verbatim

`gsd-plan-phase` handles research, planning, verification, and iteration.
</process>

<success_criteria>
- Phase number correctly parsed
- API-SPEC.md included first when it exists, with a clear escalating warning when it does not
- All discovered governance documents included as ingest sources and listed for the user
- Extra flags passed through verbatim
- gsd-plan-phase completes normally
</success_criteria>
