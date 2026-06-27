---
name: gsd-discuss-phase
description: "Gather phase context through adaptive questioning before planning."
argument-hint: "<phase> [--all] [--auto] [--chain] [--batch] [--analyze] [--text] [--power] [--assumptions]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
  - Agent
  - mcp__context7__resolve-library-id
  - mcp__context7__query-docs
---

<!-- API-FIRST PATCH — project-local overlay over gsd-discuss-phase              -->
<!-- Reads and executes the base skill dynamically; does not duplicate it.       -->
<!-- To repatch after a GSD upgrade: python3 <installer>/install.py              -->

<patch name="api-first">
This file is a project-local patch. It discovers and executes the current base
`gsd-discuss-phase` skill at runtime, with one targeted addition.

**Step 1 — Load the API gray areas supplement:**
```bash
ls .claude/api-gray-areas.md 2>/dev/null || true
```
If `.claude/api-gray-areas.md` exists, Read it and hold as `<api_gray_areas>`.

**Step 2 — Discover and read the base skill:**

Find the first existing file from this list (`.agents/skills/` is excluded — that
is this patch file, not the base):
```bash
for p in \
  ".claude/skills/gsd-discuss-phase/SKILL.md" \
  "$HOME/.claude/skills/gsd-discuss-phase/SKILL.md" \
  "$HOME/.agents/skills/gsd-discuss-phase/SKILL.md"; do
  [ -f "$p" ] && echo "$p" && break
done
```
Read the discovered file. If none is found, stop and tell the user:
`gsd-discuss-phase base skill not found — check your GSD installation.`

**Step 3 — Execute the base skill in full.**
Follow every step exactly as the base skill defines — modes, flags, hooks,
checkpoints, output format, everything.

**Step 4 — Apply the patch during `analyze_phase` only:**
If the phase goal references any API surface change (endpoints, HTTP methods,
request/response fields, contracts, OpenAPI spec) — surface all items from
`<api_gray_areas>` as additional gray areas alongside the standard ones.

**Maintenance note:** the `allowed-tools` frontmatter tracks the base skill's tool
list. Update it here if GSD adds new tools to `gsd-discuss-phase`.
</patch>
