# State — last updated 2026-05-31

**Active focus:** **EPIC `epic-analyzer-thin-runner`** (ADR-0020). **Story s1 in flight.** s1-t0, s1-t1, s1-t1b, **s1-t1c DONE and committed**. Paused at a clean task boundary. Tree clean on `main` (not pushed; ahead of origin).
**Last completed:** **s1-t1c** (`b8abdfc`) — **removed Schemathesis + the entire `contracts` domain** from code-review (operator-directed, ADR-0021; the migration hit an auth-token-leak fork). Excised the adapter/registry/capabilities/config/CLI/deps (uv.lock −783) + tests/fixture; docs updated (ADR-0021 filed, 0009 superseded, 0011 amended). Verify PASS, Review HAS-IMPORTANT (ADR-0011 amend banner) remediated inline. Full suite **431 passed**, ruff + `mypy code_review` clean. (s1-t1b `d8580aa`.)
**Next:** **s1-t2** — migrate the JS adapters (eslint/knip/jscpd/depcruiser) to invoke-and-capture + the G1 gate. Then **s1-t3** (CLI emits the bundle + delete the SARIF layer/shim, the transitional `cli.py` `_capture_to_legacy`/`_safe_run`, aggregator/severity/hotspots/MetricSet/sarif_utils/legacy AnalyzerOutput). Both have operator-approved task specs in `work/active/`. **Resume with `/clear` then "continue s1".**

## Open questions / follow-ups
- **Contract testing spun out (ADR-0021):** a standalone contract-testing skill is captured in `sdlc/raw/contract-testing-skill.md` (seeds: the deleted in-process schemathesis adapter + fixture from git history; deps schemathesis/hypothesis/fastapi/uvicorn; the `pytest>=8,<9` coupling). Not built under this epic.
- **pytest 9.x bump now unblocked** — schemathesis was the only thing pinning `pytest<9` (CVE-2025-71176 allow-list). Deferred to a dev-dep-bump story; expiry 2026-08-31 (`stack-pins.md`).
- **s1-t1 re-split (operator-approved 2026-05-30):** 4 of the 9 "Python adapters" were in-process library calls, not subprocesses → s1-t1 (5 subprocess), s1-t1b (radon/vulture/cohesion library→CLI), s1-t1c (schemathesis). `s1-t2`/`s1-t3` ids unchanged.
- **Transitional shim DELETE in s1-t3:** `cli.py` `_capture_to_legacy`/`_safe_run`; plus `aggregator`/`severity`/`hotspots`/`MetricSet`/`sarif_utils`/legacy `AnalyzerOutput`/`review-response.json`.
- **`/dev/stdout` not writable under the OS sandbox / containers** — file-output tools must use native stdout or capture native output, never a `/dev/stdout` redirect. (Cost us a fallout cycle on trivy/gitleaks.)
- **Minor carried to s1-t3:** `test_sandbox_compatibility` gitleaks/trivy no-temp-file tests are now near-trivial (mocked) — convert to assert no `--report-path`/`--output` arg, or drop.
- **s0 carry-overs still open (s1-t3):** bundle `timeout`-capture coverage (Minor #2); `test_capture` timeout event-loop-teardown warning (Minor #3, still the one suite warning).
- **CI mypy gate is package-scoped** (`uv run mypy code_review`); bare `mypy` (incl. `tests/`) shows pre-existing strict errors in test files outside the gate (e.g. `test_bandit`; the `test_schemathesis` ones are gone with that file) — not regressions.
- **Diff-path resolution** (open since s4): fix opportunistically in s1-t3 if it falls out of the CLI rewrite.
