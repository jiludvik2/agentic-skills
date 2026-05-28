---
id: adr-0001-publication
kind: decision
project: code-review
status: accepted
parent: epic-reviewer-subagent
sources: [architecture-reviewer-subagent.md]
created: 2026-05-26
updated: 2026-05-26
tags: [publication, governance]
---

# ADR-0001: Publication target

## Status

Accepted — records the project's already-established published state (rule #16 first-compile requirement).

## Context

The SDLC requires a publication-target ADR on first compile so that the `file` verb and epic-close checks know whether (and where) to propose pushing commits. The `code-review` project is not a standalone repository — it is a subdirectory of the `agentic-skills` monorepo, which is already published.

## Decision

- **Target:** GitHub — `https://github.com/jiludvik2/agentic-skills` (the monorepo; `code-review/` is a subdirectory within it).
- **Visibility:** public.
- **Account/org:** `jiludvik2`.
- **License:** MIT (repo-root `LICENSE`).
- **Default branch:** `main`; commits push directly to `main` (solo-operator workflow, matching established repo history).

## Consequences

- `file` and epic-close may propose `git push` against the existing remote (`origin`); no `gh repo create` is needed — the remote is already configured.
- Per SDLC rule #18, at epic close `git remote -v` must be non-empty and `git log @{u}..HEAD` empty before the epic moves to `done/` — satisfied by the existing remote.
- All artefacts published here are public; nothing project-confidential should be committed.
