# write_adrs step — lazy-loaded by discuss-phase.md

> **Lazy-loaded.** Read this file only inside the `write_adrs` step of
> `workflows/discuss-phase.md`. Do not put it in `<required_reading>`.
>
> **Overlay-maintained file.** This is a local customization (see
> `tools/gsd-overlay/` in the market-data repo). It is NOT part of upstream
> @opengsd/gsd-core and must be re-applied after every GSD upgrade.

## Purpose

Generate Architecture Decision Records (ADRs) in `docs/adr/` for significant
architectural choices captured during this discuss-phase session. ADRs record
the *why* — what alternatives were considered, what was chosen, and what the
consequences are — in a form that outlasts the CONTEXT.md planning artifact.

---

## Guard conditions (exit step silently if any are true)

```bash
# 1. No docs/adr/ directory in project root
[ -d "docs/adr" ] || { echo "(write_adrs: docs/adr/ not found — skipping ADR generation)"; return 0; }

# 2. Generation explicitly disabled
ADR_CFG=$(gsd_run query config-get workflow.adr_generation 2>/dev/null || echo "true")
[ "$ADR_CFG" = "false" ] && { echo "(write_adrs: workflow.adr_generation=false — skipping)"; return 0; }
```

---

## ADR-worthiness criteria

Evaluate each locked decision in CONTEXT.md `<decisions>` against these criteria. An ADR is warranted when a decision:

1. **Involves a real tradeoff** — multiple viable approaches existed; one was chosen for reasons not obvious from the code alone
2. **Constrains future phases** — future work needs to know WHY to avoid accidentally reversing it
3. **Crosses a module or layer boundary** — affects more than one component
4. **Rejects a common default** — goes against what most developers would naturally do

Explicitly **NOT** ADR-worthy (skip these without comment):
- Everything under `### Claude's Discretion` — those are implementation details
- Naming/formatting choices
- Decisions that are self-documenting from the code
- Minor preferences (exact regex pattern, variable name, message wording)

**Cap: max 3 ADRs per session.** If more than 3 decisions qualify, choose the 3 most consequential. ADR inflation reduces their signal value.

---

## Step execution

### 1. Identify candidates

Read the `<decisions>` block of the CONTEXT.md just written. For each non-Discretion category, assess each decision against the criteria above. Produce a shortlist (≤ 3).

**If no decisions qualify:** Skip the rest of this step silently. Do NOT generate ADRs for minor decisions.

### 2. Determine next ADR number

This project numbers ADRs with a 4-digit, zero-padded prefix and NO `ADR-`
prefix in the filename (house convention: `0001-slug.md`, `0002-slug.md`, …).
Match it exactly — do not invent an `ADR-NNN-` scheme.

```bash
LAST_ADR_NUM=$(ls docs/adr/[0-9]*.md 2>/dev/null | xargs -n1 basename 2>/dev/null | grep -oE '^[0-9]{4}' | sort -n | tail -1 || echo "0000")
NEXT_ADR_NUM=$((10#$LAST_ADR_NUM + 1))
```

### 3. Write each ADR

For each candidate, create `docs/adr/{NNNN}-{slug}.md` where:
- `{NNNN}` is zero-padded to 4 digits (0001, 0012, …)
- `{slug}` is a 3–6-word kebab-case summary

Use the project's house **Nygard format** (matches existing `docs/adr/0001`–`0003`):

```markdown
# ADR-{NNNN}: {Title — the decision as a noun phrase}

- **Status:** Accepted
- **Date:** {ISO date}
- **Deciders:** Operator (Jiri Ludvik)
- **Related:** {related ADRs (e.g. ADR-0001), the phase dir, and any docs/STANDARDS.md or docs/ARCHITECTURE.md sections}

## Context

{Why this decision was needed. What problem it solves. What alternatives were
available and why they were rejected. 2–4 sentences.}

## Decision

{What was decided, stated concretely. Include what was chosen AND what was
rejected. Reference exact identifiers — function names, file paths, flag names
— from the implementation. 3–6 sentences.}

## Consequences

**Positive:**
- {Concrete benefit}

**Negative / watch-out:**
- {Tradeoff or risk introduced by this decision}

**For future phases:** {What Phase N+1 or later phases need to know — e.g.
which constraint this decision creates for downstream work.}
```

Ground each ADR in the concrete implementation: use real function names, file
paths, and identifiers from CONTEXT.md and the codebase — not abstractions.

### 4. Update CONTEXT.md canonical_refs

After writing all ADR files, append each to the `<canonical_refs>` section:

```markdown
### Architecture Decision Records
- `docs/adr/{NNNN}-{slug}.md` — {one-line decision summary}
```

If a `### Architecture Decision Records` subsection already exists, append entries to it rather than creating a duplicate header.

### 5. Expose files for git_commit

Store generated paths in `ADR_FILES` (space-separated), used by the caller's
`git_commit` step:

```bash
ADR_FILES="docs/adr/0004-foo.md docs/adr/0005-bar.md"
```

If no ADRs were generated, `ADR_FILES` stays empty or unset.

### 6. Report

```
✓ ADRs written ({N}/{M} decisions were ADR-worthy):
  docs/adr/{NNNN}-{slug}.md — {title}
  ...
[If M > N:] {M-N} decision(s) were implementation details — skipped.
```
