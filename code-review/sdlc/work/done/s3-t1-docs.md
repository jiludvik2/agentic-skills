---
id: s3-t1-docs
kind: task
project: code-review
status: done
parent: s3-js-semgrep-rules
sources: [adr-0016-semgrep-rule-provenance.md, s3-t0-js-rules-fixture-test.md]
created: 2026-05-31
updated: 2026-05-31
tags: [docs, skill-md, adr, semgrep]
---

# Task s3-t1 — documentation: SKILL.md + ADR-0016 amendment

## Outcome

SKILL.md accurately reflects that the vendored semgrep ruleset now covers Python **and** JS/TS.
ADR-0016 records that the JS/TS follow-up tracked since its 2026-05-30 amendment is delivered
in s3.

## Changes

### SKILL.md (`.claude/skills/code-review/SKILL.md`)

1. **Setup section** (the "It installs..." paragraph, around line 131): change
   "vendored Semgrep security ruleset" prose to note it covers Python and JS/TS.
   Specifically: `the **vendored Semgrep security ruleset** (Python and JS/TS; committed in the
   bundle at ...)`.

2. **Per-tool reading guide table** (semgrep row, around line 179): update the "What to read"
   or "Severity cues" column to note the ruleset is multi-language:
   `runs[].results[]; each entry has level (error/warning/note) and ruleId; vendored ruleset
   covers Python and JS/TS security patterns`.

### ADR-0016 (`sdlc/docs/decisions/adr-0016-semgrep-rule-provenance.md`)

Add an amendment block below the 2026-05-30 one:

```
> **Amendment (2026-05-31, s3).** The JS/TS follow-up tracked since the 2026-05-30 amendment
> is delivered: `security-js.yaml` (MIT, hand-authored) adds `js-eval` (CWE-95, ERROR) and
> `js-innerhtml-xss` (CWE-79, WARNING) for `[javascript, typescript]`. Provisioning unchanged
> — `provision_semgrep_rules()` globs `*.y*ml` and copies all files idempotently. Validated
> end-to-end via `test_semgrep_js_rules_fire_on_js_fixture` (integration).
```

Also update the "Ruleset scope" decision text (§2) from "JS/TS is a tracked follow-up" to
"JS/TS covered as of s3 (2026-05-31)."

## Acceptance criteria

- SKILL.md setup section and semgrep table row both mention Python + JS/TS coverage.
- ADR-0016 amendment block records s3 delivery; §2 scope text updated.
- `test_skill_md_interpretation.py` still passes without modification (semgrep is already in
  the table; this task only extends the prose, not the structure).
- `uv run pytest`, `uv run ruff check .`, `uv run mypy code_review` clean.

## Test specification

No new tests. The existing `test_every_analyzer_documented` test guards that `semgrep` stays in
the SKILL.md interpretation table — it will pass as long as the word "semgrep" remains. The
prose additions are documentation, not behaviour. Confirm the existing SKILL.md tests still
pass after edits.
