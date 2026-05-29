# State — last updated 2026-05-29

**Active focus:** `epic-analyzer-ga-hardening` (6 stories, s0–s5) → **s0-semgrep-rule-source CLOSED** (`c19b786`); next epic story **s1-js-toolchain-manifest is UNPLANNED**. On branch `ccglass-traffic-analysis`. F8 (eslint only works under harness scaffolding), F9 (CI green masks the *skipped* Node-analyzer integration tests), F10 (3 untested CLI error branches) → stories s4 (eslint), s5 (CLI error tests) + an F9 AC on s1.
**Last completed:** **s0 story** — semgrep works out-of-the-box (resolves F3). s0-t0 ADR-0016 (`09c6154`), s0-t1 vendor+provision (`9a5bab1`), s0-t2 adapter cache_root/fail-loud/config-wiring (`37c83ac`), s0-t3 clean-setup e2e + de-hacked smoke harness + F3 resolved (`7f207e0`). Story-level Review MINOR-ONLY. All pushed.
**Next:** **Plan s1-js-toolchain-manifest** (operator approval needed — auto-cross paused on the unplanned next story). s1 fixes F5 (no committed `package.json`/lockfile pinning the 4 Node analyzers) + carries the F9 AC (make the skipped Node integration tests visible/run). Then s2 (jscpd output, F2), s3 (depcruiser/Node24, F1), s4 (eslint, F8), s5 (CLI error branches, F10) — each closes a GA blocker.

## Open questions / follow-ups

- **OPERATOR DECISION — ADR-0016 JS/TS rule scope.** ADR-0016 #2 says "Security rules for Python AND JS/TS", but the vendored `security.yaml` ships Python-only (header frames JS/TS as future work). Story-level review flagged the discrepancy. Decide: add JS/TS security rules (new s0 follow-up task) **or** amend ADR-0016 #2 to "Python-first, JS/TS tracked follow-up". Not amended unilaterally (ADR content stays human). Full deferred-Minor list in `s0-semgrep-rule-source.md` notes.
- **GA release blocked on `epic-analyzer-ga-hardening`.** ~~F3 semgrep~~ ✅ resolved (s0). Remaining blockers: F1 depcruiser/Node, F2 jscpd, F5 JS toolchain (+ F8 eslint, F10 CLI errors). Fix the rest, then bump `pyproject.toml` → `0.1.0`, commit, cut + push GA tag `code-review-v0.1.0`. Runbook: `sdlc/docs/runbooks/release.md`.
- **`claude-code-review` redirect meta-package** (ADR-0014): publish after the first GA publish.
- **`analyze_ccglass.py`** carries 22 ruff errors on this branch (pre-existing, prior session) — would redden CI if this branch merges. Out of epic scope.

## Recent shipped (2026-05-29)

- **s0-semgrep-rule-source CLOSED** — semgrep is now green from a clean `setup.sh` (vendored ruleset + cache_root resolution + fail-loud + config wiring + e2e proof). FINDINGS F3 resolved. Commits `09c6154`/`9a5bab1`/`37c83ac`/`7f207e0`/`c19b786`, all pushed.
- **Analyzer-coverage QA** (committed earlier this branch): regenerable smoke test (`scaffold_fixtures.sh` + `run_smoke.py`) covering all 13 adapters; the smoke harness now asserts semgrep rules are provisioned (no longer self-provisions).
- **(on `main`, e575b37) CI green**, test suite strict-typed; `polyreview 0.1.0rc1` on TestPyPI via `release.yml`.
