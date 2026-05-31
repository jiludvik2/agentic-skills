---
id: s2-t3-skill-md-interpretation-guidance
kind: task
project: code-review
status: active
parent: s2-skill-interpretation-and-golden-bundle
sources: [adr-0020-thin-invocation-runner.md, epic-analyzer-thin-runner.md, intent-review-requirements.md]
created: 2026-05-31
updated: 2026-05-31
tags: [skill, interpretation, documentation, g2, g7, capstone]
---

# Task s2-t3 — SKILL.md per-tool interpretation guidance (capstone)

## Outcome

SKILL.md teaches the consuming agent **how to read the raw bundle**: for each of the 12
registered analyzers, the output format it produces, how to interpret it, and severity cues;
plus cross-tool dedup-by-judgment guidance and false-positive notes for vulture and knip
(G2/G7). This is the story capstone — it closes the gap ADR-0020 opened by moving
interpretation onto the agent without ever telling the agent how.

## Design

Add an **"Interpreting the bundle"** section to
`.claude/skills/code-review/SKILL.md` (after the taxonomy, before sandbox config). Structure:

- **Bundle anatomy recap** — one short paragraph: `outputs[]` is one raw capture per tool;
  read `status` first (ADR-0019: `ok`/`error`/`timeout`/`unavailable`), then `stdout`/`stderr`.
  `unavailable` = the tool had nothing to scan or isn't installed (**not** a finding-free pass
  to report as clean); `error`/`timeout` = the tool did not complete — surface it, don't treat
  silence as all-clear (the F3 failure mode).
- **Per-tool table** — one row per registry analyzer, columns: *tool · output format · what
  to read · severity cues*. Group by output family:
  - **JSON**: bandit (`-f json`: `results[]` with `issue_severity`/`issue_confidence`), radon
    (`cc --json`: per-function complexity ranks A–F), pydeps (`--show-deps` JSON dep map),
    jscpd (JSON `duplicates[]`), knip (`--reporter json`: unused files/exports), depcruiser
    (`--output-type json`: `violations[]` incl. circular deps).
  - **SARIF**: semgrep (`--sarif`: `runs[].results[]` with `level` + `ruleId`), trivy
    (`--format sarif`: dependency CVEs), eslint (SARIF via the vendored formatter).
  - **Plain text**: vulture (`path:line: unused … (NN% confidence)`), cohesion (per-class
    cohesion %), gitleaks (native finding output; **exit 1 = leaks present**, which the
    capture maps to `ok`/non-error per the adapter — read stdout for the leaks).
- **Severity judgment** — the agent maps tool output to the SDLC taxonomy
  (critical/important/minor/nit) **by judgment**; there is no severity-mapping code anymore
  (ADR-0020). Give a couple of worked cues (a semgrep `error`-level SQLi → likely
  critical/important; a radon `C`-rank function → minor).
- **Cross-tool dedup** — when two tools flag the same location/issue, the agent dedups by
  judgment (ADR-0010 / ADR-0020: no mechanical aggregator). One sentence + an example.
- **G2/G7 false-positive notes** (inline, concise — operator-approved plan-time disposition):
  - **vulture** — high false-positive rate; weight by the reported confidence %, and treat
    dynamically-referenced names (framework hooks, `__all__`, plugin entry points) as suspect
    rather than definitively dead.
  - **knip** — whole-project tool; reports unused exports that may be public API or consumed
    across package boundaries it can't see. Corroborate before reporting as dead.

## Acceptance criteria

- SKILL.md contains an "Interpreting the bundle" section covering **every** key in
  `code_review.adapters.REGISTRY` (12 tools), each with an output format and severity cue.
- The section documents: status-first reading (incl. `unavailable` ≠ clean,
  `error`/`timeout` ≠ silence), severity-by-judgment (no code), cross-tool dedup-by-judgment,
  and the vulture + knip FP notes (G2/G7).
- A doc-structure test fails if any registry analyzer is absent from the section (guidance
  cannot drift from the adapter set).
- Prose is consistent with ADR-0020's guard-rail — it describes the **agent's** interpretation
  job, never re-introduces normalisation/ranking as a runner responsibility.
- `uv run pytest`, `uv run ruff check .` clean. (Doc-only task; mypy unaffected but kept green.)

## Test specification (write first, confirm RED)

1. `tests/test_skill_md_interpretation.py::test_every_analyzer_documented` — read
   `code_review.adapters.REGISTRY` keys; assert the "Interpreting the bundle" section of
   SKILL.md mentions each tool name. RED until the section is written.
2. `test_interpretation_section_present` — the `## Interpreting the bundle` heading exists.
3. `test_status_semantics_documented` — the section explains `unavailable`, `error`, and
   `timeout` (string-presence assertions for the three statuses + an "not clean"/"not silence"
   caution near `unavailable`).
4. `test_fp_notes_present` — vulture **and** knip appear with a false-positive / confidence
   caveat (G2/G7 coverage guard).

## Notes

- Doc-only change to the **source** SKILL.md (`.claude/skills/code-review/SKILL.md`). Per the
  memory note, `.claude/skills/` is Bash-write-blocked but the Edit/Write tools work — edit it
  directly.
- If the wheel/production layouts ship a copy of SKILL.md, confirm the packaged copy is sourced
  from this one (no second hand-maintained copy drifts) — grep for a bundled `SKILL.md` under
  the package and reconcile if present.
- Keep it tight: this is interpretation guidance, not a tool manual. One row per tool, a few
  worked cues — the agent is competent at reading tool output natively (ADR-0020 risk note).
