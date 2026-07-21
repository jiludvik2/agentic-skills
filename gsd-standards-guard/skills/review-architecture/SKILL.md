---
name: review-architecture
description: "Retrospectively audit and refine docs/ARCHITECTURE.md against its own §5.3 authoring contract: flag [TARGET]/[CURRENT] scaffolding, decision-restating prose, standing-table references to a superseded ADR, and drift between the MD ledger and docs/adr/index.yaml (row-for-row) — the AC6 'ledger lint' the spec defines but engine.js --lint does not check (--lint only validates index.yaml's own bucket integrity). Also spot-checks the descriptive sections (context/pipeline, repo layout, serving-layer boundaries, invariants) against the current tree for staleness and refines what has drifted. Run periodically, after a manual ARCHITECTURE.md edit, or when ADRs predating this skill were never fully indexed. Independent of /write-adr's per-ADR incremental sync and /standards-audit's code-vs-rules sweep."
argument-hint: ""
allowed-tools:
  - Read
  - Edit
  - Write
  - Bash
  - Glob
  - Grep
---

# review-architecture — retrospective ledger + prose audit

`docs/ARCHITECTURE.md` drifts two ways nothing else in this package catches:

1. **Ledger rot** — `[TARGET]`/`[CURRENT]` scaffolding left in, prose that restates a decision
   an ADR owns, a standing-table row that still cites a since-superseded ADR, or the MD ledger
   and `docs/adr/index.yaml` disagreeing on a rule's text/globs/bucket. `engine.js --lint`
   catches index.yaml's *own* integrity (bucket membership, disk coverage, glob resolution) —
   it never opens `ARCHITECTURE.md`, so none of the above trips it.
2. **Prose rot** — the Context/pipeline sketch, Repo layout, Serving-layer boundaries, and
   Invariants sections describe the codebase as it was when last hand-written, not as it is now.

Neither of the other two skills covers this: `/write-adr` only touches the ledger as a side
effect of writing *one new* ADR (§4 of that skill); `/standards-audit` checks code against rules,
never the rules document's own accuracy. This skill is the whole-file, periodic counterpart —
same relationship `/standards-audit` has to the per-diff hook, but for the doc instead of the code.

## Guard conditions (exit silently if true)

```bash
[ -f docs/ARCHITECTURE.md ]  || { echo "(review-architecture: docs/ARCHITECTURE.md not found — skipping)"; exit 0; }
[ -f docs/adr/index.yaml ]   || { echo "(review-architecture: docs/adr/index.yaml not found — skipping)"; exit 0; }
```

## 1. Mechanical pass — index integrity (reuse, don't reimplement)

```bash
node .claude/skills/gsd-standards-guard/engine.js --lint --pretty
```

This is index.yaml's own integrity check (bucket membership, ADR coverage vs `docs/adr/`,
glob resolution) — a prerequisite, not the audit itself. Fix any FAIL here first; a broken
index makes the row-for-row diff in step 2 meaningless.

## 2. Ledger lint (AC6) — read both, diff by hand

Read `docs/ARCHITECTURE.md`'s **Decision index** section and `docs/adr/index.yaml` in full, then:

**a. Scaffolding markers.**
```bash
grep -n '\[TARGET\]\|\[CURRENT\]' docs/ARCHITECTURE.md
```
Any hit is a finding — the §5.3 contract prohibits both once a component is built.

**b. Decision-restating prose.** Read the Governance banner, Context/pipeline, Repo layout,
Serving-layer boundaries, and Invariants sections. Flag any paragraph that argues *why* a
choice was made (alternatives considered, tradeoffs) rather than stating the current fact —
that content belongs in an ADR (`docs/adr/*`), which this file should point to, not restate.

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

## 3. Prose freshness — sections vs. current tree

For each of the four descriptive sections, spot-check against the repo as it stands today
(not as the doc claims):

- **Repo layout** — compare the listed top-level directories against `git ls-files` /
  top-level `ls`. Flag entries for directories that no longer exist, and directories that
  exist but aren't mentioned if they're clearly load-bearing (not scratch/build output).
- **Serving-layer boundaries** — for each `May depend on` / `Must not` row, spot-check with a
  `grep`/`Glob` for the forbidden import shape. A boundary the codebase now visibly and
  pervasively violates is a signal the doc is stale (the rule was reversed and never updated)
  — not that you should silently loosen it. Flag it for a human call: reconcile via ADR or fix
  the code.
- **Invariants** — same treatment: spot-check each "we never do X" against the current tree.
- **Context/pipeline** — sanity-read only; flag if it names a component, flow, or file that no
  longer exists.

Keep this pass proportional — a handful of targeted `Glob`/`grep` checks per section, not a
full re-architecture review. If a section needs deep verification beyond a spot-check, say so
in the report rather than guessing.

## 4. Refine

Apply fixes directly with `Edit`:

- **Auto-fix, no judgment needed:** remove stale `[TARGET]`/`[CURRENT]` markers; move a
  superseded-but-still-standing row to the Superseded line; reconcile an MD↔YAML text/glob
  mismatch against the ADR ground truth (both files, kept in sync).
- **Rewrite, flagged in the report:** decision-restating prose → trim to a pointer at the
  owning ADR; stale Repo layout / Context sketch entries → update to match the current tree.
- **Do not silently resolve:** a Serving-layer boundary or Invariant the code now visibly
  violates. Report it as a finding with examples (file:line) and let a human decide whether to
  fix the code or supersede the rule via a new ADR — this skill edits the *document*, it does
  not adjudicate architecture.

## 5. Re-lint and report

```bash
node .claude/skills/gsd-standards-guard/engine.js --lint --pretty
```

Report:

```
✓ review-architecture ({N} edits applied, {M} findings need a human call)

Fixed:
  - {one line per auto-fixed or rewritten item}

Needs a decision:
  - {one line per boundary/invariant violation or unresolved MD↔YAML/ADR conflict, with file:line}

index.yaml lint: {PASS | FAIL — see above}
```
