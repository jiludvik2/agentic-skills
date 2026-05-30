---
id: s7-uninstall-from-claude
kind: story
project: code-review
status: active
parent: epic-analyzer-ga-hardening
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md, .claude/skills/code-review/SKILL.md]
created: 2026-05-30
updated: 2026-05-30
tags: [uninstall, cli, safety, claude-config-dir, ga-readiness]
---

# s7 — `polyreview uninstall` from the user's `.claude`

## Summary

There is no clean removal path for an installed skill bundle. Once s6 lands
`polyreview install`, a user who copied the bundle into
`${CLAUDE_CONFIG_DIR:-~/.claude}/skills/code-review/` has no first-class way to
take it back out — they would `rm -rf` by hand, with all the risk that carries
next to host-owned files (`agents/reviewer.md`) and sibling skills.

This story ships `polyreview uninstall`: remove **only** the installed bundle,
**only** when it is verifiably our bundle, idempotently, and never anything else
under the config dir. The destructive nature is exactly why the safety guards
(marker check, scoped target, no-op-when-absent) are the heart of the story rather
than an afterthought. Design is settled in **ADR-0018** §5 (authored in s6-t0);
this story carries the user-facing removal contract.

Depends on s6 (the install command, the shared config-dir resolver, and the bundle
marker all originate there).

## Acceptance criteria

### Scenario: uninstall removes the installed bundle
- **Given** an installed bundle at `<config>/skills/code-review/`
- **When** the user runs `polyreview uninstall`
- **Then** exit 0 and `<config>/skills/code-review/` no longer exists.

### Scenario: uninstall is a no-op when nothing is installed
- **Given** a config dir with no `skills/code-review/`
- **When** `polyreview uninstall` runs
- **Then** exit 0 with a clear "nothing to uninstall" message and no error.

### Scenario: uninstall refuses a directory that is not our bundle
- **Given** `<config>/skills/code-review/` that lacks the bundle marker
  (e.g. an unrelated dir a mistargeted `CLAUDE_CONFIG_DIR` happens to point at)
- **When** `polyreview uninstall` runs
- **Then** it refuses to delete, exits non-zero with a message naming the failed
  marker check, and the directory is left intact.

### Scenario: uninstall never touches host-owned files or siblings
- **Given** a config dir with `agents/reviewer.md` and a sibling `skills/other/`
  alongside an installed bundle
- **When** `polyreview uninstall` runs
- **Then** `agents/reviewer.md`, `skills/other/`, and `<config>` itself are
  byte-for-byte unchanged; only `skills/code-review/` is gone.

### Scenario: install → uninstall round-trips clean
- **Given** a fresh `polyreview install`
- **When** `polyreview uninstall` runs immediately after
- **Then** the config dir is returned to its pre-install state (no orphaned files
  under `skills/code-review/`).

## Tasks

- **s7-t0 — `polyreview uninstall` command.** Scoped, marker-gated, idempotent
  removal + tests. Depends on s6.

## Deferred

- **Removing user-level caches** (`node_modules/`, Trivy DB) — only relevant if the
  deferred user-level cache relocation (ADR-0018 §6) ever ships; not in scope while
  caches stay CWD-anchored.
- **Uninstalling a project-level (`./.claude`) bundle** — paired with the deferred
  project-level install target in s6.
