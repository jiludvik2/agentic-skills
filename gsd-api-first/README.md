# gsd-api-first

A GSD addon that adds contract-first API design to the standard workflow. For any phase
that touches the API surface, it inserts a structured design step between discuss-phase
and planning — producing a locked HTTP contract before the planner runs.

## What it installs

| File | Purpose |
|------|---------|
| `.agents/skills/api-phase/SKILL.md` | `/api-phase <N>` — design HTTP contract from functional requirements |
| `.agents/skills/api-plan/SKILL.md` | `/api-plan <N>` — run gsd-plan-phase with the contract auto-ingested |
| `.agents/skills/gsd-discuss-phase/SKILL.md` | Project-local patch — surfaces API gray areas in discuss-phase for API-touching phases |
| `.claude/api-gray-areas.md` | Reference doc read by the patched discuss-phase skill |
| `.claude/templates/API-SPEC.md` | Template used by `/api-phase` to write the design contract |
| `CLAUDE.md` | Injects the `## API-First Workflow` reference section |

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

Interviews you for functional requirements only: what resources exist, what operations
are needed, who the consumers are, and what domain-specific error conditions arise. All
API design decisions — HTTP methods, URL structure, status codes, naming convention,
pagination strategy, error format, null semantics — are derived from REST and HTTP
industry practice (Google AIP, Zalando, RFC 9457, OpenAPI) without asking you to make
them.

Produces `{phase_dir}/XX-API-SPEC.md` and commits it.

### `/api-plan`

A thin wrapper around `gsd-plan-phase` that auto-discovers the phase's `API-SPEC.md`
and any project API governance documents (ADRs, architecture docs, prior contracts)
and injects them as planner context. Use in place of `/gsd-plan-phase` for any phase
that touches the API surface.

### discuss-phase patch

The patched `gsd-discuss-phase` skill reads `.claude/api-gray-areas.md` and surfaces
its items as additional gray areas when the phase goal involves API changes. It
discovers the base `gsd-discuss-phase` skill at runtime — project-local GSD installs
and global installs are both supported.

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
