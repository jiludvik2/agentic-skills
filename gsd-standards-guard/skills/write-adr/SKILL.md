---
name: write-adr
description: "Generate an Architecture Decision Record (ADR) in docs/adr/ for a load-bearing decision, in the project's house Nygard format, numbered as the next ADR with the project's existing prefix width auto-detected. Run manually at discuss/ship time when a phase logged decisions worth preserving (real tradeoff, constrains future work, crosses a boundary, rejects a default). Replaces GSD's absent native ADR generation; project-owned so it survives GSD upgrades."
argument-hint: "[phase]"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
---

# write-adr — generate an Architecture Decision Record

Generate ADRs in `docs/adr/` for significant architectural choices — the *why*
(alternatives considered, what was chosen, consequences) in a form that outlasts
the phase planning artifact. Manual, project-owned; ported from the retired
`discuss-phase` overlay step so ADR generation survives GSD upgrades.

## Guard conditions (exit silently if true)

```bash
# No docs/adr/ directory → nothing to generate into.
[ -d "docs/adr" ] || { echo "(write-adr: docs/adr/ not found — skipping)"; exit 0; }
```

## ADR-worthiness criteria

An ADR is warranted when a decision:

1. **Involves a real tradeoff** — multiple viable approaches existed; one was chosen for reasons not obvious from the code alone.
2. **Constrains future phases** — future work needs to know WHY to avoid accidentally reversing it.
3. **Crosses a module or layer boundary** — affects more than one component.
4. **Rejects a common default** — goes against what most developers would naturally do.

Explicitly **NOT** ADR-worthy (skip without comment): implementation details and
"discretion" choices, naming/formatting, self-documenting code, minor preferences.

**Cap: max 3 ADRs per session.** If more qualify, choose the 3 most consequential — ADR inflation reduces signal.

## Steps

### 1. Identify candidates

Read the decision log for the phase — the `<decisions>` block of the phase
`CONTEXT.md` if a phase is given, otherwise the decisions the current session
locked. Assess each against the criteria; produce a shortlist (≤ 3). **If none
qualify, skip the rest silently** — do not generate ADRs for minor decisions.

### 2. Determine the next number — DETECT the prefix width

ADRs use a zero-padded numeric prefix and NO `ADR-` prefix in the *filename*
(e.g. `024-slug.md` or `0024-slug.md`, depending on the project's house width).
**Detect the width from the existing files — never hard-code it.** This is the
one behavioural change from the old overlay, which pinned a 4-digit `^[0-9]{4}`
grep that silently mismatched any project not on 4 digits.

```bash
# Highest existing ADR file, its numeric prefix, and that prefix's width.
LAST_FILE=$(ls docs/adr/[0-9]*-*.md 2>/dev/null | xargs -n1 basename 2>/dev/null \
            | grep -oE '^[0-9]+' | sort -n | tail -1)
if [ -z "$LAST_FILE" ]; then
  WIDTH=3; NEXT=1                       # empty docs/adr/ → default width 3, start at 001
else
  WIDTH=${#LAST_FILE}                   # preserve the existing prefix width
  NEXT=$((10#$LAST_FILE + 1))
fi
NEXT_NUM=$(printf "%0${WIDTH}d" "$NEXT")  # e.g. 066  (3-digit)  or  0067 (4-digit)
```

### 3. Write each ADR

Create `docs/adr/{NEXT_NUM}-{slug}.md` where `{slug}` is a 3–6-word kebab-case
summary. Match the project's existing house **Nygard format** exactly (open one
or two existing ADRs and mirror their heading style, including whether the `#`
title uses `ADR-{NUM}:` or a bare title):

```markdown
# ADR-{NUM}: {Title — the decision as a noun phrase}

- **Status:** Accepted
- **Date:** {ISO date}
- **Deciders:** {deciders, matching existing ADRs}
- **Related:** {related ADRs, the phase dir, and any docs/STANDARDS.md or docs/ARCHITECTURE.md sections}

## Context

{Why this decision was needed. What problem it solves. What alternatives were
available and why they were rejected. 2–4 sentences.}

## Decision

{What was decided, stated concretely — what was chosen AND what was rejected.
Reference exact identifiers — function names, file paths, flag names — from the
implementation. 3–6 sentences.}

## Consequences

**Positive:**
- {Concrete benefit}

**Negative / watch-out:**
- {Tradeoff or risk introduced by this decision}

**For future phases:** {What later phases need to know — the constraint this
decision creates for downstream work.}
```

Ground each ADR in the concrete implementation: real function names, file paths,
and identifiers — not abstractions.

### 4. Index the new ADR — reconcile the rule ledger

A new ADR is **unenforced until it is indexed** (§5.3/§5.7 of the design). After
writing it:

- If it carries a **standing code rule**, add a row to `docs/ARCHITECTURE.md`'s
  standing-rule ledger *and* a `rules[]` entry to `docs/adr/index.yaml`
  (`adr`, `area`, `rule`, `globs`, optional `check`). Keep the two in sync.
- If it **supersedes** an earlier ADR, move that ADR from the standing table to
  the superseded line/bucket in the same change.
- If it is **historical/process** (no standing rule), add it to the historical bucket.

Then validate:

```bash
node .agents/skills/gsd-standards-guard/engine.js --lint --pretty
```

### 5. Register in CONTEXT.md and report

If a phase `CONTEXT.md` exists, append each ADR to its `<canonical_refs>` under
an `### Architecture Decision Records` subsection (append to it if present, do
not duplicate the header):

```markdown
### Architecture Decision Records
- `docs/adr/{NUM}-{slug}.md` — {one-line decision summary}
```

Report:

```
✓ ADRs written ({N}/{M} decisions were ADR-worthy):
  docs/adr/{NUM}-{slug}.md — {title}
  ...
[If M > N:] {M-N} decision(s) were implementation details — skipped.
[If a standing rule was added:] indexed in ARCHITECTURE.md + index.yaml; lint PASS.
```
