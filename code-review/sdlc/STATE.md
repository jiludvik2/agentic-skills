# State — last updated 2026-05-31

**Active focus:** **EPIC `epic-analyzer-thin-runner`** (ADR-0020, stories s0–s5). **s0 + s1 + s2 DONE** (pushed to origin/main at 92c8b40). **s3 plan compiled and awaiting operator approval.**
**Last completed:** **Story s2** (SKILL.md "Interpreting the bundle" section for all 12 registry analyzers; golden-bundle fixture + byte-equal regression guard; diff-path resolution anchored on git repo root; dead `sarif-2.1.0.json` + 3 packaging pins removed). 384 tests green.
**Next:** **Operator approval for story s3 plan** — then execute s3-t0 (JS/TS semgrep rules + fixture + integration test) followed by s3-t1 (documentation).

## Story s3 plan summary

Story: `s3-js-semgrep-rules` — G6: vendor JS/TS semgrep rules.

Two tasks:
- **s3-t0** — Add `security-js.yaml` to the skill bundle (2 rules: `js-eval` CWE-95, `js-innerhtml-xss` CWE-79); create `tests/fixtures/js-with-security-issues/vuln.js`; add integration test asserting both rules fire end-to-end. No adapter code modified (architecture validation).
- **s3-t1** — Update SKILL.md semgrep entry to note Python + JS/TS; amend ADR-0016 to close the JS/TS follow-up.

Architecture validation: provisioning already globs `*.y*ml` — adding the new rule file is the only plumbing needed. No adapter changes.

## Open questions / follow-ups
- **s4 (G8: JS complexity analyzer)** and **s5 (G5: maintainability oracle QA harness)** follow s3; both unplanned.
- **s5 carry-over:** `sdlc/docs/qa/analyzer-coverage/results/raw/*.json` are pre-ADR-0020 captures (old sarif/metrics shape) — regenerate against the raw bundle before s5 uses them.
