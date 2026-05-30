# State — last updated 2026-05-29

**Active focus:** `epic-analyzer-ga-hardening` (6 stories, s0–s5) → **s0 CLOSED**; **s1-js-toolchain-manifest in progress** (planned 4 tasks; s1-t0 + s1-t1 done, **s1-t2 next**). On branch `ccglass-traffic-analysis`. Remaining findings: F8 eslint (s4), F9 CI masks skipped Node integration tests (s1-t3 + s2/s3/s4), F10 CLI error branches (s5).
**Last completed:** **s1-t1** (`f397057`) — committed `package.json` + `package-lock.json` at the skill root pinning eslint^9/knip^5/jscpd^4/dependency-cruiser^16(candidate)/eslint-formatter-sarif^3 (ADR-0017); setup.sh's npm-ci branch now vendors them; 4 Node analyzers probe available. s1-t0 (`dbe3a4e`) = ADR-0017 (Node 20+22 matrix) + stack-pins. Verify PASS / Review MINOR-ONLY both. (Earlier: whole s0 story closed `c19b786`.)
**Next:** **s1-t2** — version-drift guard (capabilities.json has NO Node-tool version fields today → add a version source that matches the lockfile) + make the eslint SARIF formatter (`@microsoft/eslint-formatter-sarif`) resolve regardless of adapter cwd (replace the smoke harness's NODE_PATH stopgap). Spec: `sdlc/work/active/s1-t2-version-drift-and-eslint-formatter.md`. Then s1-t3 (CI Node 20+22 matrix runs integration tests, xfail-gating jscpd/depcruiser/eslint → flipped in s2/s3/s4). **Paused at clean task boundary for context — resume with `/clear` → "resume s1-t2".**

## Open questions / follow-ups

- **RESOLVED — ADR-0016 JS/TS rule scope** (2026-05-30): operator chose to **amend** ADR-0016 #2 to "Python-first; JS/TS a tracked follow-up" (not author JS/TS rules now). s0 stays closed on the proven Python coverage. Amendment note in `adr-0016-semgrep-rule-provenance.md` #2.
- **GA release blocked on `epic-analyzer-ga-hardening`.** ~~F3 semgrep~~ ✅ resolved (s0). Remaining blockers: F1 depcruiser/Node, F2 jscpd, F5 JS toolchain (+ F8 eslint, F10 CLI errors). Fix the rest, then bump `pyproject.toml` → `0.1.0`, commit, cut + push GA tag `code-review-v0.1.0`. Runbook: `sdlc/docs/runbooks/release.md`.
- **`claude-code-review` redirect meta-package** (ADR-0014): publish after the first GA publish.
- **`analyze_ccglass.py`** carries 22 ruff errors on this branch (pre-existing, prior session) — would redden CI if this branch merges. Out of epic scope.

## Recent shipped (2026-05-29)

- **s1 in progress** — s1-t0 ADR-0017 (Node 20+22 matrix, JS pins) + s1-t1 vendored `package.json`/lockfile (4 Node analyzers now `available`). `dbe3a4e`/`f397057`, pushed.
- **s0-semgrep-rule-source CLOSED** — semgrep green from a clean `setup.sh` (vendored ruleset + cache_root + fail-loud + e2e). FINDINGS F3 resolved. Through `c19b786`, pushed.
- **Analyzer-coverage QA** (committed earlier this branch): regenerable smoke test (`scaffold_fixtures.sh` + `run_smoke.py`) covering all 13 adapters; the smoke harness now asserts semgrep rules are provisioned (no longer self-provisions).
- **(on `main`, e575b37) CI green**, test suite strict-typed; `polyreview 0.1.0rc1` on TestPyPI via `release.yml`.
