# State — last updated 2026-05-30

**Active focus:** **EPIC `epic-analyzer-thin-runner`** (ADR-0020) — facade → thin invocation runner. **Story s0 DONE and committed** (`f5e60c1`): the new raw-capture rail (`capture.py` + `review_bundle.py` + `review-bundle.v1.json`) is fully in place and **purely additive** — the live SARIF path is untouched. Tree clean on `main` (not pushed).
**Last completed:** **s0 — contract inversion + bundle** (s0-t0 `12eefd6` CaptureOutput + run_and_capture; s0-t1 `1bfa5ed` ReviewBundle + schema). Per-task Verify PASS + Review MINOR-ONLY; story-level Review MINOR-ONLY. Full suite 441 passed; ruff + `mypy code_review` clean.
**Next:** **Execute s1 once the plan is approved.** **s1 is PLANNED and committed** — story `s1-migrate-adapters-and-emit-bundle` + 4 tasks (s1-t0 type/status SoT; s1-t1 9 Python adapters; s1-t2 4 JS adapters + G1; s1-t3 CLI emits bundle + delete aggregator/severity/hotspots/MetricSet/SARIF-builders). CLI bundle-emission pulled s2→s1-t3 (operator-approved). Plan approval is human — **awaiting operator review before execution.**

## Open questions / follow-ups
- **s1 plan awaits operator review** (plan approval stays human). It absorbs the 3 s0 story-level Minors: (1) shared ADR-0019 status SoT (s1-t0); (2) bundle `timeout`-capture coverage (s1-t3); (3) timeout-test loop-teardown cleanup (s1-t3). Epic re-scoped: s2 is now SKILL.md interpretation + golden-bundle hardening.
- **CI mypy gate is package-scoped** (`uv run mypy code_review`). Bare `uv run mypy` also checks `tests/` and surfaces **6 PRE-EXISTING strict errors** in `test_bandit.py`/`test_schemathesis.py` (on HEAD, outside the gate) — not regressions. Consider tightening the gate or fixing the stubs (own task).
- **Diff-path resolution** (open since s4): `resolve_diff_paths` repo-relative vs `cli.py` cwd-abspath — fix during s1/s2 (invocation layer survives the redesign).
- **SDLC #26 supply-chain gate:** none wired; `stack-pins.md` cites non-existent `scripts/license_audit.py`; `npm audit` 5 pre-existing transitive vulns (offline). Decide whether to wire a gate (ADR).
- **`claude-code-review` redirect meta-package** (ADR-0014): due now (first GA published). Own task.
- **Merged branch `ccglass-traffic-analysis`** still on local + origin; delete (operator authorises) now PR #1 merged.
- **Stack-pins drift (Minor):** `types-jsonschema` / `types-PyYAML` dev stubs not listed in the stack-pins dev table.
