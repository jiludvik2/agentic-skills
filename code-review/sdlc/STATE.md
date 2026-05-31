# State — last updated 2026-05-31

**Active focus:** **EPIC `epic-analyzer-thin-runner`** (ADR-0020, stories s0–s5). **s0–s3 DONE.** s0–s2 pushed to origin/main at 92c8b40; **s3 is local-only (4 commits ahead, unpushed).**
**Last completed:** **Story s3** (`s3-js-semgrep-rules`, G6) — vendored `security-js.yaml` (js-eval CWE-95 ERROR, js-innerhtml-xss CWE-79 WARNING) for `[javascript, typescript]`; `vuln.js` + `vuln.ts` fixture; integration test asserting both rules fire on both languages; SKILL.md + ADR-0016 updated. Zero `code_review/` change — architecture-validation criterion ("near-trivial") proven. 385 tests green.
**Next:** **Operator approval of the s4 plan** (compiled, not yet committed) — then execute s4-t0 (ADR-0022 tool selection) → s4-t1 (adapter + wiring + docs + tests). s3 is pushed (origin/main @ 3be3eeb).

## Story s4 plan summary (awaiting approval)
Story `s4-js-complexity-analyzer` — G8: JS/TS complexity analyzer, radon-`cc` parity. Two tasks:
- **s4-t0** — ADR-0022: JS complexity tool selection + cc-parity scope + JS cohesion limitation (no code; resolves the stack hard-stop).
- **s4-t1** — adapter + REGISTRY/_JS_ADAPTERS/capabilities wiring + SKILL.md docs + tests (test-first). Docs in-task: `test_every_analyzer_documented` couples REGISTRY membership to the SKILL.md table.

**Key decision (hard-stop, in ADR-0022):** which JS complexity tool. Plan recommends **reusing the vendored ESLint `complexity` core rule** via an adapter-supplied config (zero new dependency; radon runs only `cc`, so eslint-complexity is exact parity). Alternatives: `eslintcc` / `ts-complex` (richer, but new npm dependency). Operator can change the choice by editing s4 before approval.

- **s5 (G5: maintainability oracle QA harness)** — extend analyzer-coverage QA harness with labelled coupling fixtures asserted against the **new raw bundle**. UNPLANNED.

## Open questions / follow-ups
- **s5 carry-over:** `sdlc/docs/qa/analyzer-coverage/results/raw/*.json` are pre-ADR-0020 captures (old sarif/metrics shape) — regenerate against the raw bundle before s5 uses them.
- **Stale doc (not s3 scope):** stack-pins.md §License floor cites `scripts/license_audit.py` as the CI license gate, but that script does not exist — no dependency-audit gate is wired (rule #26 currently n/a for this project).
