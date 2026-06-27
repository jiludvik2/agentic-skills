# gsd-standard-enforcement

A GSD addon that patches three GSD core workflows to enforce architecture contracts,
generate Architecture Decision Records, and enable full-codebase code review audits.

Unlike project-skill addons (e.g. `gsd-api-first`), this addon patches GSD core files
directly and backs them up to `gsd-local-patches/` so the patches survive GSD upgrades
(`/gsd-update --reapply`).

## What it patches

| File | Change |
|------|--------|
| `gsd-core/workflows/code-review.md` | Adds `--audit` flag — Tier 0 scope that reviews the full codebase, short-circuiting phase-file scoping |
| `gsd-core/workflows/discuss-phase.md` | Adds `write_adrs` step — generates ADRs for significant architectural decisions captured during discuss-phase |
| `gsd-core/workflows/discuss-phase/steps/write-adrs.md` | Lazy-loaded step that implements ADR generation (new file, not in upstream GSD) |
| `agents/gsd-code-reviewer.md` | Adds architecture/standards contract loading — reviewer reads `docs/ARCHITECTURE.md`, `docs/STANDARDS.md`, and all active ADRs before reviewing |

## Prerequisites

These must be satisfied by the operator **before or after installation** — the installer does not create them.

### 1. Create `docs/adr/` (required for ADR generation)

The `write_adrs` step runs only when `docs/adr/` exists in the project root. Without
it the step exits silently — no ADRs, no error. Create the directory and at minimum
an initial ADR to establish the numbering scheme before using discuss-phase in projects
where you want ADRs:

```bash
mkdir -p docs/adr
```

ADRs are numbered with 4-digit zero-padded filenames (`0001-slug.md`, `0002-slug.md`, …).
The step counts existing files to determine the next number — start from `0001` if the
directory is empty or the first file is your seed.

### 2. Create architecture/standards docs (optional, recommended)

The patched reviewer loads these files if they exist:

- **`docs/ARCHITECTURE.md`** — layer constraints, module boundaries, forbidden patterns.
  Findings reference this document by section.
- **`docs/STANDARDS.md`** — coding conventions, naming rules, quality requirements.
- **`docs/adr/`** — all `.md` files whose status is not `Superseded`, `Rejected`,
  or `Deprecated` are read. Each accepted ADR becomes an enforceable contract.

None of these are required — if absent, the reviewer proceeds with generic review only.
Their value compounds over time: the more decisions you capture, the more precisely the
reviewer enforces your project's choices rather than generic best practices.

### 3. GSD installed

A working GSD install is required at the target scope:

- User level (`--user`): `~/.claude/gsd-core/VERSION` must exist.
- Project level (`--project PATH`): `PATH/.claude/gsd-core/VERSION` must exist.

---

## Installation

```bash
# Install at user level (patches ~/.claude/ — applies to all projects):
python3 path/to/gsd-standard-enforcement/install.py

# Install at project level (patches {project}/.claude/ — that project only):
python3 path/to/gsd-standard-enforcement/install.py --project /path/to/project

# Preview without writing anything:
python3 path/to/gsd-standard-enforcement/install.py --dry-run
```

The installer is idempotent — files already matching the patch are skipped. When a
file differs, a short unified diff is shown before overwriting.

---

## What each patch does

### `--audit` flag in `/gsd-code-review`

Standard `/gsd-code-review <N>` reviews only files changed during the phase. The
`--audit` flag adds a Tier 0 scope that short-circuits phase scoping and reviews the
full codebase (scope defined in the workflow file — see [Prerequisite 1](#1-adapt-the---audit-scope-to-your-project-required-if-using---audit)):

```
/gsd-code-review 5 --audit
```

Use for periodic full-codebase sweeps, pre-release checks, or standards-compliance
assessment across the entire codebase rather than just the latest changes.

### Architecture/standards contract in `gsd-code-reviewer`

Before reviewing any source files, the code reviewer loads project architecture and
standards documentation if it exists (`docs/ARCHITECTURE.md`, `docs/STANDARDS.md`,
`docs/adr/`). Each finding cites the source document and section:

> "violates ARCHITECTURE.md §Layer Rules — adapters must not aggregate data"

If none of these files exist, the reviewer proceeds with generic review only — the
patch is a no-op for projects without architecture docs.

### ADR generation in `discuss-phase`

After each `/gsd-discuss-phase` session, the `write_adrs` step evaluates locked
decisions in CONTEXT.md against four criteria:

1. Involves a real tradeoff (multiple viable approaches existed)
2. Constrains future phases (future work needs to know why)
3. Crosses a module or layer boundary
4. Rejects a common default

Decisions that meet the bar are written as ADRs in `docs/adr/` using the project's
Nygard format. Minor decisions and Claude's-discretion items are skipped. Cap: 3 ADRs
per session. ADRs are committed as part of the discuss-phase commit.

The step is skipped silently when `docs/adr/` doesn't exist or when
`workflow.adr_generation` is set to `false` in the GSD config.

---

## Upgrade safety

After patching, each file is backed up to `gsd-local-patches/` inside the GSD config
directory:

```
~/.claude/gsd-local-patches/
├── backup-meta.json                       # version, timestamp, pristine hashes
├── agents/
│   └── gsd-code-reviewer.md
└── gsd-core/
    └── workflows/
        ├── code-review.md
        ├── discuss-phase.md
        └── discuss-phase/
            └── steps/
                └── write-adrs.md
```

`backup-meta.json` records the GSD version the patches were applied against and
SHA-256 hashes of the upstream (pre-patch) file content. GSD's
`/gsd-update --reapply` reads these backups to restore patches after a GSD upgrade.

To re-apply after a GSD upgrade:

```bash
python3 path/to/gsd-standard-enforcement/install.py
```

The installer merges into any existing `gsd-local-patches/` content — it never
overwrites or deletes backup entries created by other installers.

---

## Saving local edits back to the installer

If you modify a patched file in the GSD install and want to save those changes back
to `target/` in this installer:

```bash
python3 path/to/gsd-standard-enforcement/install.py --update
# or for a project-level install:
python3 path/to/gsd-standard-enforcement/install.py --project /path/to/project --update
```

This copies each installed file from the GSD config dir back to `target/` so the next
`install.py` run distributes the updated version.
