# Architecture

> **Authoring contract (gsd-standards-guard).** This file is a **standing-rule
> ledger**, not decision prose. It has the sections below and only these. It
> never restates a decision an ADR owns — it points. Decisions live in
> `docs/adr/*` (binding, append-only); this file and `docs/adr/index.yaml` are
> two renderings of the same standing rules and must agree row-for-row. Run
> `node .claude/skills/gsd-standards-guard/engine.js --lint` after edits.

## Governance

- **Authority order:** `docs/adr/*` (binding, append-only) > `docs/STANDARDS.md` > this file.
  If this file disagrees with an ADR, the ADR wins — fix this file.
- **Drift discipline:** reconcile this ledger **and its `docs/adr/index.yaml` mirror** at
  every `/gsd-ship`. A new ADR is unindexed (⇒ unenforced) until it gets a rule row + globs;
  a superseded ADR moves from the standing table to the superseded line in the same change.

## Context / pipeline

{One paragraph or a small sketch: what this system is and how data/requests flow through it.}

## Repo layout

{The top-level directories and what each owns — one line each.}

## Serving-layer boundaries

{A small table of the layers/components and what may call what — the boundary contract.}

| Layer | May depend on | Must not |
|---|---|---|
| … | … | … |

## Invariants

Things we never do (violations are findings regardless of ADR coverage):

- {e.g. "No view/DDL runs inside a repository — DDL lives at the composition root."}
- {e.g. "Adapters never import the HTTP client directly."}

## Decision index — standing-rule ledger

A three-tier ledger. Keep it row-for-row identical to `docs/adr/index.yaml`.

### Standing rules

One row per live rule. The reader checks the rule here; opens `docs/adr/<NNN>-*.md`
only for rationale/edge detail.

| ADR | Binding rule (one line) | Applies to (path globs) |
|---|---|---|
| {024} | {View DDL runs at the composition root, not in a repository.} | `{backend/src/**/repositories/**}` |

### Superseded — do not read

{NNN→successor arrows. Steers readers away from reversed decisions.}

- {015 → 024, 018 → 024}

### Historical / process

{Number + title only — context, no standing rule.}

- {001 — initial architecture context}

## Further reading

- `docs/STANDARDS.md` — code-level conventions.
- `docs/adr/` — the binding decision record.
