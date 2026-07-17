# gsd-api-first

A GSD addon that adds contract-first API design to the standard workflow. For any phase
that touches the API surface, it inserts one design step — `/api-spec` — between
discuss-phase and planning, producing a locked HTTP contract before the planner runs.

The addon is **purely additive**: it ships one new skill and a template and adds a small
fenced block to the project's agent-instructions file (`CLAUDE.md` or `AGENTS.md`). It does
not modify or shadow any GSD skill, so GSD upgrades never touch it.

## Design authorities

Every API design decision produced by this addon is derived from published industry
standards — not from asking the user to make design choices:

| Standard | Applies to |
|----------|-----------|
| [Google API Design Guide (AIP)](https://google.aip.dev/) | Resource naming, sub-resource nesting, custom action pattern, long-running operations |
| [Zalando RESTful API Guidelines](https://opensource.zalando.com/restful-api-guidelines/) | URL casing (kebab-case MUST rule), naming convention selection, collection envelope shape, error format |
| [Microsoft Azure REST API Best Practices](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design) | Versioning strategy selection, idempotency key guidance, pagination approach |
| [RFC 9457 — Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457) | Error response format (`application/problem+json`, `type` URI stability, `title` immutability) |
| [OpenAPI Specification 3.x](https://spec.openapis.org/oas/v3.1.0) | Contract structure, schema representation, nullable semantics |

The user is asked only for functional requirements (what resources, what operations,
who the consumers are, what domain-specific errors can occur). Everything derivable
from those inputs — HTTP methods, status codes, URL paths, error bodies, pagination
strategy — is decided by the skill.

## What it installs

| File | Purpose |
|------|---------|
| `.agents/skills/api-spec/SKILL.md` | `/api-spec <N>` — design the HTTP contract (new or existing API) and register it in `CONTEXT.md` `<canonical_refs>` for the planner |
| `.claude/templates/API-SPEC.md` | Template `/api-spec` fills to write the design contract |
| `CLAUDE.md` / `AGENTS.md` | A fenced `## API-First Workflow` routing block, added to whichever of these already exists |

Nothing here shadows or edits a GSD skill, so there are no backups, no restore step, and
no "re-apply after a GSD upgrade" dance.

## Prerequisites

- **GSD initialized:** `ROADMAP.md` and `.planning/` must exist in the project root.
  Run `/gsd-new-project` or `/gsd-new-milestone` if they do not.
- **Active phase:** the phase number you pass must exist in `ROADMAP.md`. Create phases
  with `/gsd-phase add` before running `/api-spec`.

The installer does not create phases or initialize GSD — those are operator
responsibilities.

## Installation

```bash
# Install into the current directory
./install.sh

# Install into a specific project
./install.sh /path/to/project
```

`install.sh` copies the two files into the project and appends the fenced
`## API-First Workflow` block to the project's agent-instructions file. It is tool-neutral:
it updates `CLAUDE.md` and/or `AGENTS.md` when they exist, adds the block only if it isn't
already there (checked by marker and by heading, so re-running never duplicates it), and
**never creates** an instructions file — if neither exists it installs the skill and prints
a warning telling you to add the block manually.

The installer only ever adds the current payload; it does not delete anything. If you
installed a pre-release version, remove any leftover `api-plan`, `api-phase`, or
`gsd-discuss-phase` skills and `.claude/api-gray-areas.md` by hand — `git` makes that a
one-step review and revert.

After installing, commit the added files:

```bash
git add .agents .claude CLAUDE.md
git commit -m "chore: install gsd-api-first addon"
```

## Uninstallation

There is no uninstall command — removal is two steps:

```bash
rm -rf <project>/.agents/skills/api-spec <project>/.claude/templates/API-SPEC.md
```

Then delete the block between `<!-- gsd-api-first:start -->` and
`<!-- gsd-api-first:end -->` in whichever of `CLAUDE.md` / `AGENTS.md` the installer updated.
Everything is git-tracked, so `git diff` / `git checkout` will show and revert exactly what
changed.

## Workflow

For phases that add or change the API surface, insert one step — `/api-spec` — into the
standard GSD flow. There is no replacement planner; `/api-spec` registers the contract
where `/gsd-plan-phase` already looks.

```
/gsd-spec-phase <N>      lock WHAT (functional requirements)
/gsd-discuss-phase <N>   lock HOW decisions
/api-spec <N>            design HTTP contract; register it in CONTEXT.md <canonical_refs>
/gsd-plan-phase <N>      standard GSD planner; reads the contract via <canonical_refs>
/gsd-execute-phase <N>   execute; Wave 0 must regenerate the OpenAPI spec
/gsd-verify-work <N>     UAT against the locked contract
```

For phases with no API surface change, use the standard GSD sequence — `/api-spec` is
not needed.

### `/api-spec`

Reads the project context — existing OpenAPI spec, codebase, phase SPEC.md/CONTEXT.md,
ADRs, architecture docs — and derives a complete proposed API contract before asking
the user anything. The interaction is one round: the skill presents the draft and asks
for corrections, then writes the spec.

It works for both a **new API surface** and a **change to an existing one**. It first
determines the mode: with no committed baseline it designs greenfield from industry
practice and defaults; with a baseline present it treats the established conventions
(naming, envelope, error format, versioning, pagination) as binding constraints, diffs the
proposal against the current surface, tags each endpoint NEW / MODIFIED / DEPRECATED /
UNCHANGED, and classifies every change as additive or breaking (breaking changes are gated
and recorded with migration notes).

Design decisions derived automatically from context:

| Decision | Inferred from |
|----------|--------------|
| Consumer type | Frontend code presence, README, project description |
| Naming convention | Existing API field names; consumer type if greenfield |
| Resources & operations | Phase SPEC.md / CONTEXT.md / UAT criteria |
| HTTP methods & status codes | Industry practice (fixed) |
| Pagination strategy | Existing endpoints; domain scale heuristic if greenfield |
| Filterable/sortable fields | Phase spec and existing query parameters |
| Domain error conditions | State machine fields, unique constraints, phase spec |
| Versioning policy | Existing URL prefix or ADRs; consumer type if greenfield |
| Null semantics | Existing conventions; RFC 9457 defaults |
| Idempotency key need | Consumer type (proposed for mobile/external POST operations) |

The single confirmation question presents the full draft and at most three open
questions for things that could not be inferred. User corrections are applied without
opening additional question rounds. If any proposed change is **breaking**, a second
gate asks for explicit approval and a change-ledger entry.

Produces `{phase_dir}/XX-API-SPEC.md` with concrete JSON examples for every endpoint
and error condition, validated against a REST/HTTP invariant checklist. It then registers
that spec's path in the phase `CONTEXT.md` `<canonical_refs>` block and commits the spec and
the registration together atomically.

### Planning (no wrapper)

There is no separate planning command. Once `/api-spec` has registered the contract in
`CONTEXT.md` `<canonical_refs>`, you plan the phase with the ordinary `/gsd-plan-phase <N>`.

GSD requires planning and implementing agents to read every file listed in
`<canonical_refs>` before planning or implementing, so the planner, `gsd-phase-researcher`,
and `gsd-plan-checker` all pick up `API-SPEC.md` automatically — no wrapper command, no
`--ingest` flag, and nothing extra to remember. Because the reference lives in the phase's
own sealed context, it can't be bypassed by forgetting a flag or typing the wrong command:
the only way to plan the phase is through the context that already points at the contract.

The registration is written idempotently, so re-running `/api-spec` (after corrections or a
breaking-change gate) updates the entry in place rather than adding a duplicate. It is the
one sanctioned edit to the discuss-owned `CONTEXT.md`; every other block is left untouched.

## Upgrade safety

The addon is purely additive and shadows no GSD skill, so a GSD upgrade cannot break or
overwrite it. The `/api-spec` skill lives in `.agents/skills/` and the template in
`.claude/`, both git-tracked in your project and outside GSD's managed paths
(`~/.claude/gsd-core/`, `~/.claude/skills/`). Re-run the installer any time to pull the
latest addon version into a project; use git to review or revert the change.
