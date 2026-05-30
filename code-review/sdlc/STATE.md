# State — last updated 2026-05-30

**Active focus:** **EPIC `epic-analyzer-thin-runner`** (ADR-0020) — facade → thin invocation runner. **Story s0 DONE and committed** (`f5e60c1`): the new raw-capture rail (`capture.py` + `review_bundle.py` + `review-bundle.v1.json`) is fully in place and **purely additive** — the live SARIF path is untouched. Tree clean on `main` (not pushed).
**Last completed:** **s0 — contract inversion + bundle** (s0-t0 `12eefd6` CaptureOutput + run_and_capture; s0-t1 `1bfa5ed` ReviewBundle + schema). Per-task Verify PASS + Review MINOR-ONLY; story-level Review MINOR-ONLY. Full suite 441 passed; ruff + `mypy code_review` clean.
**Next:** **Plan s1 — migrate adapters to invoke-and-capture** (UNPLANNED — auto-progress halted here, plan approval is human). s1 deletes every `_to_sarif`, `aggregator`/`severity`/`hotspots`/`MetricSet`/SARIF builders; each adapter → invoke + capture + exit-code/availability mapping; folds in G1 (jscpd scope). An s1 plan proposal is on the table awaiting operator approval.

## Open questions / follow-ups
- **s1 plan proposed, awaiting approval.** It absorbs the 3 s0 story-level Minors: (1) promote a shared ADR-0019 status `Literal/StrEnum` (single source of truth across capture.py + bundle + schema enum); (2) add a `timeout`-status capture to the bundle test suite; (3) clean up the timeout-test event-loop-teardown warning when base.run_subprocess is touched.
- **CI mypy gate is package-scoped** (`uv run mypy code_review`). Bare `uv run mypy` also checks `tests/` and surfaces **6 PRE-EXISTING strict errors** in `test_bandit.py`/`test_schemathesis.py` (on HEAD, outside the gate) — not regressions. Consider tightening the gate or fixing the stubs (own task).
- **Diff-path resolution** (open since s4): `resolve_diff_paths` repo-relative vs `cli.py` cwd-abspath — fix during s1/s2 (invocation layer survives the redesign).
- **SDLC #26 supply-chain gate:** none wired; `stack-pins.md` cites non-existent `scripts/license_audit.py`; `npm audit` 5 pre-existing transitive vulns (offline). Decide whether to wire a gate (ADR).
- **`claude-code-review` redirect meta-package** (ADR-0014): due now (first GA published). Own task.
- **Merged branch `ccglass-traffic-analysis`** still on local + origin; delete (operator authorises) now PR #1 merged.
- **Stack-pins drift (Minor):** `types-jsonschema` / `types-PyYAML` dev stubs not listed in the stack-pins dev table.
