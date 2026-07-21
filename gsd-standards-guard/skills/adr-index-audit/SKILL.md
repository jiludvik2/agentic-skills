---
name: adr-index-audit
description: "Retrospectively audit and refine docs/ARCHITECTURE.md's decision-index ledger against its own §5.3 authoring contract and docs/adr/index.yaml: flag [TARGET]/[CURRENT] scaffolding, decision-restating prose, standing-table references to a superseded ADR, and drift between the MD ledger and index.yaml (row-for-row) — the AC6 'ledger lint' the spec defines but engine.js --lint does not check (--lint only validates index.yaml's own bucket integrity: coverage, no double-bucketing, glob resolution — never opens ARCHITECTURE.md). Run periodically, after a manual ARCHITECTURE.md edit, or when ADRs predating this skill were never fully indexed. Independent of /write-adr's per-ADR incremental sync and /standards-audit's code-vs-rules sweep. Ledger/index bookkeeping only — does not review whether the architecture itself, or the doc's descriptive prose, still matches the codebase."
argument-hint: ""
allowed-tools:
  - Read
  - Edit
  - Write
  - Bash
  - Glob
  - Grep
---

# adr-index-audit — retrospective ADR-ledger consistency audit

`docs/ARCHITECTURE.md`'s **decision index** (the three-tier ledger: Standing rules / Superseded /
Historical) drifts in ways nothing else in this package catches: `[TARGET]`/`[CURRENT]`
scaffolding left in, prose that restates a decision an ADR owns, a standing-table row that still
cites a since-superseded ADR, or the MD ledger and `docs/adr/index.yaml` disagreeing on a rule's
text/globs/bucket. `engine.js --lint` catches `index.yaml`'s *own* integrity (bucket membership,
disk coverage, glob resolution) — it never opens `ARCHITECTURE.md`, so none of the above trips it.

Neither of the other two skills covers this either: `/write-adr` only touches the ledger as a side
effect of writing *one new* ADR (§4 of that skill); `/standards-audit` checks code against rules,
never the rules document's own bookkeeping. This skill is the whole-ledger, periodic counterpart —
same relationship `/standards-audit` has to the per-diff hook, but for the ledger instead of the code.

**Out of scope:** whether the codebase still matches what `ARCHITECTURE.md`'s prose sections
(Context/pipeline, Repo layout, Serving-layer boundaries, Invariants) *describe*. That's a
separate, harder, code-vs-doc review this skill does not attempt — it only audits the ledger's
internal and cross-file consistency.

## Guard conditions (exit silently if true)

```bash
[ -f docs/ARCHITECTURE.md ]  || { echo "(adr-index-audit: docs/ARCHITECTURE.md not found — skipping)"; exit 0; }
[ -f docs/adr/index.yaml ]   || { echo "(adr-index-audit: docs/adr/index.yaml not found — skipping)"; exit 0; }
```

## 1. Mechanical pass — index integrity (reuse, don't reimplement)

```bash
node .claude/skills/gsd-standards-guard/engine.js --lint --pretty
```

This is `index.yaml`'s own integrity check (bucket membership, ADR coverage vs `docs/adr/`,
glob resolution) — a prerequisite, not the audit itself. Fix any FAIL here first; a broken
index makes the row-for-row diff in step 2 meaningless.

## 2. Ledger lint (AC6) — read both, diff by hand

Read `docs/ARCHITECTURE.md`'s **Decision index** section and `docs/adr/index.yaml` in full, then:

**a. Scaffolding markers.**
```bash
grep -n '\[TARGET\]\|\[CURRENT\]' docs/ARCHITECTURE.md
```
Any hit is a finding — the §5.3 contract prohibits both once a component is built.

**b. Decision-restating prose.** Read the Governance banner and the Decision-index section (and,
opportunistically, the other sections). Flag any paragraph that argues *why* a choice was made
(alternatives considered, tradeoffs) rather than stating the current fact — that content belongs
in an ADR (`docs/adr/*`), which this file should point to, not restate.

**c. Superseded references.** For every ADR id in `index.yaml`'s `superseded{}` bucket, grep
the **Standing rules** table for that id — a live-looking row citing a superseded ADR is a
finding (it should have moved to the Superseded line already).
```bash
grep -n '| *{adr-id} *|' docs/ARCHITECTURE.md   # against the Standing rules table only
```

**d. MD ↔ YAML row-for-row agreement.** For every ADR in `index.yaml`, confirm:
- it appears in **exactly one** of the MD file's three ledger sections (Standing rules /
  Superseded / Historical) — matching the bucket it's in in `index.yaml`;
- for `rules[]` entries: the MD table's rule text and globs match the YAML `rule`/`globs`
  content (not necessarily character-for-character, but no material difference in meaning
  or scope);
- for `superseded{}`/`historical{}` entries: the MD line's successor/reason matches the YAML value.

When MD and YAML disagree and neither is obviously stale, **open the ADR file itself**
(`docs/adr/<NNN>-*.md`) as ground truth and reconcile both renderings to match it — don't pick
one arbitrarily.

## 3. Refine

Apply fixes directly with `Edit`:

- **Auto-fix, no judgment needed:** remove stale `[TARGET]`/`[CURRENT]` markers; move a
  superseded-but-still-standing row to the Superseded line; reconcile an MD↔YAML text/glob
  mismatch against the ADR ground truth (both files, kept in sync).
- **Rewrite, flagged in the report:** decision-restating prose → trim to a pointer at the
  owning ADR.
- **Do not silently resolve:** an MD↔YAML conflict where the ADR file itself is ambiguous or
  the two renderings reflect a real, unresolved disagreement about current status. Report it
  and let a human decide.

## 4. Re-lint and report

```bash
node .claude/skills/gsd-standards-guard/engine.js --lint --pretty
```

Report:

```
✓ adr-index-audit ({N} edits applied, {M} findings need a human call)

Fixed:
  - {one line per auto-fixed or rewritten item}

Needs a decision:
  - {one line per unresolved MD↔YAML/ADR conflict, with file:line}

index.yaml lint: {PASS | FAIL — see above}
```
