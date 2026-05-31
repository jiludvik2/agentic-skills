# State — last updated 2026-05-31

**Active focus:** **EPIC `epic-analyzer-thin-runner`** (ADR-0020, stories s0–s5). **s0 + s1 + s2 DONE** (local, not yet pushed). s3 is the next story but has no compiled artefact — plan needed before execution.
**Last completed:** **Story s2** (SKILL.md "Interpreting the bundle" section for all 12 registry analyzers; golden-bundle fixture + byte-equal regression guard; diff-path resolution anchored on git repo root; dead `sarif-2.1.0.json` + 3 packaging pins removed). 384 tests green.
**Next:** **Plan and approve story s3 — G6: vendor JS semgrep rules.** Epic description: "orthogonal coverage win, now cheap; closes the no-JS-SAST gap. Already decided: vendor JS/TS rules into the ruleset, not a new tool." Source raw material: `vendor-js-semgrep-rules.md` (referenced in epic but not found in `sdlc/raw/` or `sdlc/docs/` — may have been absorbed). Propose plan; operator approves before execution.

## Open questions / follow-ups
- **s3 plan needed** — compile the story + tasks for G6 (vendor JS semgrep rules). Check `semgrep-rules/` bundle directory and the semgrep adapter for the current rule-selection logic before designing the task sequence.
- **s4 (G8: JS complexity analyzer)** and **s5 (G5: maintainability oracle QA harness)** follow s3; both unplanned.
- **s5 carry-over:** `sdlc/docs/qa/analyzer-coverage/results/raw/*.json` are pre-ADR-0020 captures (old sarif/metrics shape) — regenerate against the raw bundle before s5 uses them.
- **Push cadence:** s2 commits are local only (`main` @ `ded646c` on origin). Push when the operator is ready.
