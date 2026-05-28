---
name: sdlc
description: AI-native, spec-anchored, filesystem-as-source-of-truth delivery workflow for a solo operator working with AI agents — no external tracker. Use at the start of any session in a repo that uses (or should use) this SDLC, and whenever doing development work: capturing or compiling /sdlc/raw, planning a task/story/epic, executing tests-first, running Verify or Review, filing outputs, refreshing STATE.md, or judging whether an action needs operator approval (the autonomy gate). Triggers include "set up the SDLC", "start an SDLC project", "capture this", "compile the raw", "plan this story", "verify this task", "review the diff", or any spec-anchored, no-tracker delivery work. On first use in a project it bootstraps the framework; thereafter it routes to the project-local copy.
---

# SDLC

This skill carries an AI-native, spec-anchored delivery workflow: the filesystem is the source of truth, git history is the audit trail, Claude Code is the primary agent, and there is no external tracker. The canonical process is the bundled `references/SDLC.md`. **This skill is a router and bootstrapper — it does not restate or fork the canonical process.**

## Step 1 — bootstrap-or-route (do this first, always)

Check whether the current project is SDLC-initialised: **does `./sdlc/STATE.md` exist?**

**No → the project is not initialised. Bootstrap it (this is the install step):**

1. Scaffold the tree: `sdlc/raw/`, `sdlc/work/active/`, `sdlc/work/done/`, `sdlc/docs/architecture/`, `sdlc/docs/strategy/`, `sdlc/docs/decisions/`, `sdlc/docs/runbooks/`.
2. Copy the bundled `references/SDLC.md` (alongside this `SKILL.md`) → `./sdlc/SDLC.md`. This becomes the project's pinned, authoritative copy.
3. Copy the bundled `references/verifier.md` and `references/reviewer.md` → `./.claude/agents/`. Without these, Verify and Review cannot run.
4. Add a pointer to `CLAUDE.md` at the repo root (create it if absent): `See /sdlc/SDLC.md for how to work in this repo.`
5. Create `./sdlc/STATE.md` with a "Session 0" entry (per the STATE.md section of the canonical doc): session time and which raw material exists in `/sdlc/raw/` awaiting compile.
6. Report what was created and stop for operator approval. Bootstrapping the substrate is not a licence to start compiling or coding.

**Yes → the project is initialised. Route to the project-local copy:**

1. Read `./sdlc/SDLC.md` in full — it, not this skill's bundled copy, is the source of truth for this project (it may have been customised or version-pinned).
2. Run the version check (Step 2).
3. Follow the session-start protocol (rule #1 of the project's SDLC.md): reconcile `stack-pins.md` against the manifest if present, check per-project memory, read `STATE.md`.

## Step 2 — version check (initialised projects only)

Compare the `version:` in `./sdlc/SDLC.md`'s frontmatter against the bundled `references/SDLC.md`.

- **Match** → proceed.
- **Project behind the bundle** → mention it once, offer to upgrade with a one-line summary of what changed, and **wait for an explicit operator decision**. Never auto-apply — a mid-stream SDLC swap churns a running project's workflow. The project's pinned copy stays authoritative until the operator approves the upgrade.
- **Project ahead of the bundle** → the project copy wins; say nothing.

## Rule

Do not restate or fork the canonical process here or anywhere else. For any specific convention — the verbs, the autonomy gate, the hard rules, file frontmatter, the `s<N>-t<M>` / `-fix<N>` id scheme, the severity taxonomy, the escalation interface, the exact `STATE.md` shape — read that section of the project's `./sdlc/SDLC.md`.

## Adapting the canonical copy

`references/SDLC.md` is a starting point harvested from a live project, so a few hard rules are project-specific examples rather than universal law — most obviously rule #26's `make audit` (a Python pip-audit supply-chain gate) and the ADR-0008 sandbox references. During a project's first compile, adapt or drop the rules that don't fit the stack and renumber as needed. The workflow itself — the verbs, the autonomy gate, tests-first, fresh-context Verify/Review, filesystem-as-truth — is stack-agnostic.
