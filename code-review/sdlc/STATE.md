# State — last updated 2026-05-31

**Active focus:** **EPIC `epic-analyzer-thin-runner`** (ADR-0020, stories s0–s5). **s0–s3 DONE.** s0–s2 pushed to origin/main at 92c8b40; **s3 is local-only (4 commits ahead, unpushed).**
**Last completed:** **Story s3** (`s3-js-semgrep-rules`, G6) — vendored `security-js.yaml` (js-eval CWE-95 ERROR, js-innerhtml-xss CWE-79 WARNING) for `[javascript, typescript]`; `vuln.js` + `vuln.ts` fixture; integration test asserting both rules fire on both languages; SKILL.md + ADR-0016 updated. Zero `code_review/` change — architecture-validation criterion ("near-trivial") proven. 385 tests green.
**Next:** **Push s3** (4 commits: 4db34ee plan, 9aeefdc s3-t0, 36720a8 s3-t1, cc75748 story cleanup) — operator-driven, no push policy in AGENTS.md. Then **plan story s4** (unplanned).

## Story-boundary pause (s3 → s4)
s4 has no operator-approved plan, so auto-cross does not apply — paused for s4 planning per the Execute verb.

- **s4 (G8: JS complexity analyzer)** — add a JS complexity analyzer (parity with radon); document JS cohesion as a thin-tooling limitation. UNPLANNED.
- **s5 (G5: maintainability oracle QA harness)** — extend analyzer-coverage QA harness with labelled coupling fixtures asserted against the **new raw bundle**. UNPLANNED.

## Open questions / follow-ups
- **s5 carry-over:** `sdlc/docs/qa/analyzer-coverage/results/raw/*.json` are pre-ADR-0020 captures (old sarif/metrics shape) — regenerate against the raw bundle before s5 uses them.
- **Stale doc (not s3 scope):** stack-pins.md §License floor cites `scripts/license_audit.py` as the CI license gate, but that script does not exist — no dependency-audit gate is wired (rule #26 currently n/a for this project).
