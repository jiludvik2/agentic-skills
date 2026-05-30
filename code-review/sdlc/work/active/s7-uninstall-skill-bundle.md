---
id: s7-uninstall-skill-bundle
kind: story
project: code-review
status: active
parent: epic-analyzer-ga-hardening
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md, .claude/skills/code-review/SKILL.md]
created: 2026-05-30
updated: 2026-05-30
tags: [uninstall, cli, safety, agent-skills, cross-agent, ga-readiness]
---

# s7 — `polyreview uninstall` the skill bundle (agent-independent)

## Summary

There is no clean removal path. Once s6 lands `polyreview install` — which may
place the bundle in **several** user-level skills directories (the neutral
`~/.agents/skills/` plus any present agent homes) — a user has no first-class way
to take it back out without `rm -rf` next to host-owned files (Claude's
`agents/reviewer.md`) and sibling skills.

This story ships `polyreview uninstall`: remove the installed bundle from **every
target where s6 could have put it**, mirroring the install registry, **only** when
the directory is verifiably our bundle, idempotently, and never anything else. The
destructive nature is exactly why the safety guards (marker check, scoped target,
no-op-when-absent) are the heart of the story. It reuses the target registry, the
config resolver, and the bundle marker from s6. Design settled in ADR-0018 §5.

Depends on s6.

### Target resolution

Same registry as install. Default `uninstall` removes the bundle from the neutral
`agents` target **and every agent home where a marked bundle is found**;
`--agent <id[,id…]>` / `--all` scope it exactly as for install.

## Acceptance criteria

### Scenario: uninstall removes the bundle from every target it was installed to
- **Given** a bundle installed (per s6 default) at both `~/.agents/skills/code-review/`
  and `~/.claude/skills/code-review/`
- **When** the user runs `polyreview uninstall`
- **Then** exit 0 and **both** `code-review/` directories are gone.

### Scenario: --agent scopes the removal
- **Given** the bundle installed in both `agents` and `claude` targets
- **When** the user runs `polyreview uninstall --agent claude`
- **Then** only `~/.claude/skills/code-review/` is removed; the `agents` copy
  remains.

### Scenario: uninstall is a no-op when nothing is installed
- **Given** no `code-review/` under any registry skills dir
- **When** `uninstall` runs
- **Then** exit 0 with a clear "nothing to uninstall" message and no error.

### Scenario: uninstall refuses a directory that is not our bundle
- **Given** a `<skills-dir>/code-review/` that lacks the bundle marker (e.g. a
  collision or a mistargeted dir)
- **When** `uninstall` runs
- **Then** it refuses to delete that target, exits non-zero with a message naming
  the failed marker check, and the directory is left intact. (A refusal on one
  target does not silently skip reporting the others.)

### Scenario: uninstall never touches host-owned files or siblings
- **Given** a target whose parent also has `agents/reviewer.md` and a sibling
  `skills/other-skill/`
- **When** `uninstall` runs
- **Then** `reviewer.md`, `skills/other-skill/`, and the skills dir itself are
  unchanged; only `skills/code-review/` is removed.

### Scenario: install → uninstall round-trips clean across targets
- **Given** a fresh `polyreview install` (multi-target)
- **When** `polyreview uninstall` runs immediately after
- **Then** every touched skills dir returns to its pre-install state (no orphaned
  `code-review/` anywhere).

## Tasks

- **s7-t0 — `polyreview uninstall` command.** Registry-based multi-target,
  marker-gated, idempotent removal with `--agent`/`--all` scoping + tests.
  Depends on s6.

## Deferred

- **Removing user-level caches** — only relevant if the deferred user-level cache
  relocation (ADR-0018 §6) ever ships; not in scope while caches stay CWD-anchored.
- **Uninstalling a project-level bundle** — paired with the deferred project-level
  install target in s6.
