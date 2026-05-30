# State — last updated 2026-05-30

**Active focus:** **EPIC `epic-analyzer-thin-runner`** (ADR-0020) — facade → **thin invocation runner** (couple to invocation contract, not output schema; emit raw bundles; agent interprets). **s0 is planned and committed — awaiting operator approval to execute.** Tree clean on `main` (not pushed).
**Last completed:** **Plan s0** (`0c0b11b`) — story `s0-contract-inversion-and-bundle` + 2 tasks (s0-t0 `CaptureOutput`+`run_and_capture`; s0-t1 `ReviewBundle`+`review-bundle.v1.json`). Tests-first; **additive strangle** (s0 adds the new rail, deletes nothing; s1 switches + tears out the SARIF layer).
**Next:** **Execute s0-t0** once the plan is approved — tests-first RED→GREEN, then Verify + Review. Then s0-t1, then s1 (adapter migration + delete `_to_sarif`/`aggregator`/`severity`/`hotspots`/`MetricSet`).

## Open questions / follow-ups

- **s0 plan awaits operator review** (plan approval stays human). Two design calls flagged: new `code_review/capture.py` + distinct `CaptureOutput` type (keeps s0 additive/green; optional rename → `AnalyzerOutput` in s1); bundle as the agent's versioned contract (`review-bundle/v1`, opaque `stdout`).
- **Gap dispositions** live in `epic-analyzer-thin-runner.md`: G3 retired; G1→s1; G2/G7→s2; G6→s3; G8→s4; G5→s5. Validation criterion: s3–s5 must each be near-trivial.
- **`claude-code-review` redirect meta-package** (ADR-0014): due now (first GA published). Own task.
- **Diff-path resolution** (open since s4): `resolve_diff_paths` repo-relative vs `cli.py` cwd-abspath — `--diff` from a subdir mis-resolves; affects all adapters. Survives the redesign (invocation layer); fix during s1/s2.
- **GA supply-chain gate** (open since s3): no audit gate (SDLC #26 skipped); `npm audit` 5 pre-existing transitive vulns (offline/local-only). Decide whether to wire a gate (ADR).
- **Stale doc:** `stack-pins.md` references non-existent `scripts/license_audit.py` — correct or add the gate (ADR).
- **Merged branch `ccglass-traffic-analysis`** still on local + origin; delete (operator authorises) now PR #1 merged.
- **Deferred Minors** (s0/s6/s7 close notes): most touch code the redesign rewrites — re-triage against the new architecture rather than fixing on the facade.
