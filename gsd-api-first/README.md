# gsd-api-first

A GSD addon that adds contract-first API design to the standard workflow. For any phase
that touches the API surface, it inserts a structured design step between discuss-phase
and planning — producing a locked HTTP contract before the planner runs.

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
| `.agents/skills/api-phase/SKILL.md` | `/api-phase <N>` — design HTTP contract from functional requirements |
| `.agents/skills/api-plan/SKILL.md` | `/api-plan <N>` — run gsd-plan-phase with the contract auto-ingested |
| `.agents/skills/gsd-discuss-phase/SKILL.md` | Project-local patch — surfaces API gray areas in discuss-phase for API-touching phases |
| `.claude/api-gray-areas.md` | Reference doc read by the patched discuss-phase skill |
| `.claude/templates/API-SPEC.md` | Template used by `/api-phase` to write the design contract |
| `CLAUDE.md` | Injects the `## API-First Workflow` reference section |

## Prerequisites

The following must be in place before the installed skills will run:

- **GSD initialized:** `ROADMAP.md` and `.planning/` must exist in the project root.
  Run `/gsd-new-project` or `/gsd-new-milestone` if they do not.
- **Active phase:** the phase number you pass must exist in `ROADMAP.md`. Create phases
  with `/gsd-phase add` before running `/api-phase`.
- **Base `gsd-discuss-phase` skill** (for the discuss-phase patch only): the skill
  must be discoverable at `.claude/skills/gsd-discuss-phase/SKILL.md`,
  `~/.claude/skills/gsd-discuss-phase/SKILL.md`, or
  `~/.agents/skills/gsd-discuss-phase/SKILL.md`. The patch stops with an error message
  if none of these paths exists.

The installer does not create phases or initialize GSD — those are operator
responsibilities.

## Installation

```bash
# Install into the current directory
python3 path/to/gsd-api-first/install.py

# Install into a specific project
python3 path/to/gsd-api-first/install.py /path/to/project

# Preview what would be installed
python3 path/to/gsd-api-first/install.py --dry-run
```

The installer is idempotent — safe to run multiple times. It injects into an existing
`CLAUDE.md` rather than replacing it.

After installing, commit the added files:

```bash
git add .agents/ .claude/ CLAUDE.md
git commit -m "chore: install gsd-api-first workflow addon"
```

## Workflow

For phases that add or change the API surface, use this sequence instead of the
standard GSD flow:

```
/gsd-spec-phase <N>      lock WHAT (functional requirements)
/gsd-discuss-phase <N>   lock HOW decisions; API gray areas surface automatically
/api-phase <N>           design HTTP contract from functional requirements
/api-plan <N>            plan with the contract auto-ingested
/gsd-execute-phase <N>   execute; Wave 0 must regenerate the OpenAPI spec
/gsd-verify-work <N>     UAT against the locked contract
```

For phases with no API surface change, use the standard GSD sequence — `/api-phase`
and `/api-plan` are not needed.

### `/api-phase`

Reads the project context — existing OpenAPI spec, codebase, phase SPEC.md/CONTEXT.md,
ADRs, architecture docs — and derives a complete proposed API contract before asking
the user anything. The interaction is one round: the skill presents the draft and asks
for corrections, then writes the spec.

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
and error condition, validated against a REST/HTTP invariant checklist, and commits it
atomically.

### `/api-plan`

A thin wrapper around `gsd-plan-phase` that auto-discovers the phase's `API-SPEC.md`
and any project API governance documents (ADRs, architecture docs, prior contracts from
earlier phases) and injects them as `--ingest` sources so the planner sees the locked
contract without manual flag passing.

**Problem solved:** without this wrapper, the planner only sees governance docs if you
remember `--ingest` on every API phase. Under pressure that step gets dropped, and the
planner makes implementation decisions that conflict with the design contract. This
wrapper makes that omission structurally impossible.

Emits an escalating warning if `API-SPEC.md` is missing, and asks the user to confirm
before proceeding without a contract. All `gsd-plan-phase` flags (`--auto`,
`--skip-research`, `--tdd`, `--mvp`, etc.) are forwarded verbatim.

### discuss-phase patch

The patched `gsd-discuss-phase` skill reads `.claude/api-gray-areas.md` and surfaces
its items as additional gray areas when the phase goal involves API changes. The base
`gsd-discuss-phase` skill is discovered and executed at runtime — project-local GSD
installs and global installs are both supported. If the base skill cannot be found, the
patch stops immediately with a clear error message.

The `.claude/api-gray-areas.md` file installed alongside the patch documents the common
API design gray areas (versioning trigger, idempotency key obligation, bulk endpoint
decision, error granularity) that should be discussed before planning any API phase.

## Upgrade safety

The installed files live in `.agents/skills/` and `.claude/`, neither of which is
touched by GSD core upgrades. If a GSD upgrade changes `gsd-discuss-phase` in a way
that matters, re-run the installer to refresh the patch:

```bash
python3 path/to/gsd-api-first/install.py
```

## Saving local changes back to the installer

If you modify any installed file in the project and want to save those changes back
to the installer source:

```bash
python3 path/to/gsd-api-first/install.py --update
```
