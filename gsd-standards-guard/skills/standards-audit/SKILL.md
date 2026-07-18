---
name: standards-audit
description: "Run a whole-codebase standards-compliance sweep — the manual counterpart to the per-change code-review hook. Calls the gsd-standards-guard engine with --scope=all: a deterministic tier that mechanically runs every check: rule over the tracked tree (CI-gateable, exits non-zero on any violation) and a semantic tier that spawns the gsd-code-reviewer per rule-area with only that area's rules injected. Use pre-release, on a schedule, or in CI. Re-homes the old installer's --audit flag as a project-owned command with zero GSD vendor surface."
argument-hint: ""
allowed-tools:
  - Read
  - Bash
  - Task
  - Write
---

# standards-audit — whole-codebase compliance sweep

The second caller of the `gsd-standards-guard` engine (the first is the
per-change PreToolUse hook). Same engine, same `docs/adr/index.yaml`, same rules
— only `--scope` differs (`all` vs `diff`). The hook and this audit **cannot
drift** in what they enforce, and neither depends on the other.

Manual only. Not wired into the hook or any phase workflow — it owns its whole
invocation. Audits are periodic, not per-change.

## 1. Preflight

```bash
[ -f docs/adr/index.yaml ] || { echo "standards-audit: docs/adr/index.yaml missing — nothing to enforce"; exit 1; }
node .claude/skills/gsd-standards-guard/engine.js --lint --pretty || echo "WARN: index lint failed — results may be incomplete"
```

## 2. Deterministic tier (CI-gateable core)

Run every `check:` rule whose globs match a tracked file over the whole tree.
This tier needs no model and is the hard gate — it **exits non-zero** on any
violation.

```bash
node .claude/skills/gsd-standards-guard/engine.js --scope=all --exit-code --format=pretty
DET_STATUS=$?   # 0 = clean, 1 = at least one deterministic violation
```

Capture the JSON form too, for the rollup and for splitting semantic from
deterministic rules:

```bash
node .claude/skills/gsd-standards-guard/engine.js --scope=all --format=json > /tmp/standards-audit.json
```

Every `violations[]` entry names the ADR, file, line, and forbidden/required
pattern — report each verbatim.

## 3. Semantic tier (per-area reviewer passes)

Semantic rules (no `check:`) need model judgment. From
`/tmp/standards-audit.json`, take the matched rules **without** a `check`, group
them by `area`, and for each area spawn one `gsd-code-reviewer` subagent (a
native GSD agent — invoking it is not a patch) with **only that area's rules**
injected. Chunking by area keeps each pass selective and token-minimal, exactly
like the hook.

For each area:

- Give the subagent the area's rule lines (`ADR-<n> (<area>): <rule>`), the
  enforcement directive, and the list of files that matched that area's globs
  (`matchedRules[].matchedFiles` from the JSON).
- Ask it to report findings citing the ADR, in the same shape the hook produces:
  `violates ADR-<n> — <rule>` with file:line.

If an area's file set is too large for one subagent's useful context, chunk finer
by glob within the area (the deterministic tier has no such limit — it is
script-evaluated).

## 4. Rollup report

Collect the deterministic violations and every area's semantic findings into one
report at `docs/reviews/audit-<ISO-date>.md` (create `docs/reviews/` if absent):

```markdown
# Standards audit — {date}

- Tree: {N} tracked files · rules matched: {R} ({D} deterministic, {S} semantic)
- Deterministic result: {PASS | FAIL — K violations}

## Deterministic violations
- ADR-{n} — {file}:{line} — forbidden "{pattern}"  ({rule})

## Semantic findings (by area)
### {area}
- ADR-{n} — {file}:{line} — {finding}  ({rule})

## Clean areas
- {area}: no findings
```

## 5. Exit status

Exit non-zero if the deterministic tier found any violation (`DET_STATUS` = 1) —
this is what makes the audit CI-gateable. Semantic findings are advisory (model
judgment) and do not by themselves fail the build; surface them in the report and
let a human triage.

```bash
exit $DET_STATUS
```
