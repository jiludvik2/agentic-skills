# State — last updated 2026-05-31

**Active focus:** **EPIC `epic-analyzer-thin-runner`** (ADR-0020, stories s0–s5). **s0–s4 DONE.** s0–s3 pushed to origin/main @ 3be3eeb; **s4 is local (commits 20a9a2d, 07d38aa, 85bba09, 8073866 + this close — unpushed).**
**Last completed:** **Story s4** (`s4-js-complexity-analyzer`, G8) — shipped `jscomplexity`, a JS cyclomatic-complexity analyzer reusing the vendored ESLint `complexity` rule (zero new dependency; radon-`cc` parity). JS-only (ADR-0022 + gate-escalation amendment: ESLint can't parse TS without the unvendored `@typescript-eslint/parser`); TS complexity + JS cohesion documented as limitations. New analyzer with no existing-adapter change — G8 architecture-validation confirmed. 393 tests green.
**Next:** **Push s4** (operator-driven, no push policy in AGENTS.md), then **plan story s5** (unplanned) — story-boundary pause.

## Story-boundary pause (s4 → s5)
s5 has no operator-approved plan, so auto-cross does not apply — paused for s5 planning per the Execute verb.

- **s5 (G5: maintainability oracle QA harness)** — extend the analyzer-coverage QA harness with labelled coupling fixtures (pydeps `test_cycles`, depcruiser `__mocks__`) asserted against the **new raw bundle**. UNPLANNED. **Last story of the epic** — closing it cleanly hits the epic boundary (Document + File verbs: README reconcile, epic move to done/, ADR-0022 → docs/decisions/).

## Open questions / follow-ups
- **s5 carry-over:** `sdlc/docs/qa/analyzer-coverage/results/raw/*.json` are pre-ADR-0020 captures (old sarif/metrics shape) — regenerate against the raw bundle before s5 uses them.
- **TS complexity follow-up** (post-epic, if demanded): vendor `typescript-eslint` (v8, MIT) + widen `jscomplexity` capabilities `languages` — no adapter rewrite (ADR-0022).
- **Stale doc (not s4 scope):** stack-pins.md §License floor cites `scripts/license_audit.py` (does not exist); no dependency-audit gate is wired (rule #26 n/a).
