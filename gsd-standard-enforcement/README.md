# gsd-standard-enforcement

A GSD addon that patches GSD core workflows to enforce architecture contracts,
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
| `CLAUDE.md` (project root) | Inserts a marker-wrapped block instructing every agent to read `docs/ARCHITECTURE.md`, `docs/STANDARDS.md`, and `docs/adr/*.md` before any structural work |

The `CLAUDE.md` block always targets the **project** file (the instructions reference
project-relative docs): `PATH/CLAUDE.md`, or `./CLAUDE.md` when `--project` is omitted.
It is created if absent, replaced in place on re-install (idempotent via the
`<!-- gsd-standard-enforcement:begin/end -->` markers), and removed on `--uninstall`
without disturbing the rest of the file.

## Prerequisites

### 1. `docs/adr/` (created automatically on install)

The installer creates `docs/adr/` if it does not exist. The `write_adrs` step runs
only when this directory is present — if it is removed after installation, the step
exits silently.

ADRs are numbered with 4-digit zero-padded filenames (`0001-slug.md`, `0002-slug.md`, …).
The step counts existing files to determine the next number.

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

### 3. Project-level GSD installed

This addon is **project-scoped only** — it patches a project's GSD install and seeds
that project's `CLAUDE.md`. There is no user-level install mode. A project-level GSD
install is required: `PATH/.claude/gsd-core/VERSION` must exist (install with
`npx -y @opengsd/gsd-core@latest --claude` run inside the project).

---

## Installation

```bash
# Install into the current project (patches ./.claude/ and ./CLAUDE.md):
python3 path/to/gsd-standard-enforcement/install.py

# Install into another project (patches {project}/.claude/ and {project}/CLAUDE.md):
python3 path/to/gsd-standard-enforcement/install.py --project /path/to/project

# Preview without writing anything:
python3 path/to/gsd-standard-enforcement/install.py --dry-run
```

`--project` defaults to the current directory. The installer is idempotent — files
already matching the patch are skipped. When a file differs, a short unified diff is
shown before overwriting.

---

## What each patch does

### `--audit` flag in `/gsd-code-review`

Standard `/gsd-code-review <N>` reviews only files changed during the phase. The
`--audit` flag adds a Tier 0 scope that short-circuits phase scoping and reviews all
git-tracked files (`git ls-files`):

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

## Uninstallation

```bash
# Uninstall from the current project:
python3 path/to/gsd-standard-enforcement/install.py --uninstall

# Uninstall from another project:
python3 path/to/gsd-standard-enforcement/install.py --project /path/to/project --uninstall

# Preview without writing anything:
python3 path/to/gsd-standard-enforcement/install.py --uninstall --dry-run
```

Uninstall restores each patched GSD file to its pristine original (saved during
installation), deletes `write-adrs.md` (which has no upstream original), removes
`gsd-local-patches/` entirely, and strips the contract block from the project
`CLAUDE.md` (deleting the file only if the block was its sole content). `docs/adr/`
is left in place — it may contain ADRs you want to keep.

---

## Upgrade safety

After patching, each file is backed up to `gsd-local-patches/` inside the GSD config
directory:

```
~/.claude/gsd-local-patches/
├── backup-meta.json                       # version, timestamp, pristine hashes
├── pristine/                              # originals saved before patching (for --uninstall)
│   ├── agents/gsd-code-reviewer.md
│   └── gsd-core/workflows/
│       ├── code-review.md
│       └── discuss-phase.md
├── agents/
│   └── gsd-code-reviewer.md              # patched versions (for --reapply)
└── gsd-core/
    └── workflows/
        ├── code-review.md
        ├── discuss-phase.md
        └── discuss-phase/steps/write-adrs.md
```

`backup-meta.json` records the GSD version the patches were applied against and
SHA-256 hashes of the upstream (pre-patch) file content. GSD's
`/gsd-update --reapply` reads the patched-version backups to restore patches after a
GSD upgrade.

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
