# State — last updated 2026-05-31

**Active focus:** **EPIC `epic-analyzer-thin-runner`** (ADR-0020) — facade → thin invocation runner. **Story s1 in flight.** s1-t0 (status SoT + return-type consolidation) and s1-t1 (5 subprocess Python adapters → invoke-and-capture) both **DONE and committed**. Tree clean on `main` (not pushed; ahead of origin).
**Last completed:** **s1-t1** (`6d77030`) — bandit/semgrep/gitleaks/trivy/pydeps now return `CaptureOutput` via `run_and_capture` (+`env=`); pre-flights → `unavailable` (ADR-0019); trivy/gitleaks avoid `/dev/stdout`; transitional `cli.py` shim holds the legacy aggregate green. Verify PASS, Review MINOR-ONLY. Full suite **447 passed** (5 real-tool integrations), ruff + `mypy code_review` clean. (s1-t0 `6dcc3ed`; re-split plan `554497e`.)
**Next:** **s1-t1b** — migrate radon/vulture/cohesion (in-process library → CLI subprocess). Then **s1-t1c** schemathesis (library → `schemathesis run` subprocess; auth/sandbox design fork — read the current adapter first, escalate if auth can't map). Then **s1-t2** (JS adapters + G1) and **s1-t3** (CLI emits bundle + delete the SARIF layer/shim). All have operator-approved task specs in `work/active/`.

## Open questions / follow-ups
- **s1-t1 re-split (operator-approved 2026-05-30):** 4 of the 9 "Python adapters" were in-process library calls, not subprocesses → s1-t1 (5 subprocess), s1-t1b (radon/vulture/cohesion library→CLI), s1-t1c (schemathesis). `s1-t2`/`s1-t3` ids unchanged.
- **Transitional shim DELETE in s1-t3:** `cli.py` `_capture_to_legacy`/`_safe_run`; plus `aggregator`/`severity`/`hotspots`/`MetricSet`/`sarif_utils`/legacy `AnalyzerOutput`/`review-response.json`.
- **`/dev/stdout` not writable under the OS sandbox / containers** — file-output tools must use native stdout or capture native output, never a `/dev/stdout` redirect. (Cost us a fallout cycle on trivy/gitleaks.)
- **Minor carried to s1-t3:** `test_sandbox_compatibility` gitleaks/trivy no-temp-file tests are now near-trivial (mocked) — convert to assert no `--report-path`/`--output` arg, or drop.
- **s0 carry-overs still open (s1-t3):** bundle `timeout`-capture coverage (Minor #2); `test_capture` timeout event-loop-teardown warning (Minor #3, still the one suite warning).
- **CI mypy gate is package-scoped** (`uv run mypy code_review`); bare `mypy` shows 6 pre-existing strict errors in test_bandit/test_schemathesis (outside the gate) — not regressions.
- **Diff-path resolution** (open since s4): fix opportunistically in s1-t3 if it falls out of the CLI rewrite.
