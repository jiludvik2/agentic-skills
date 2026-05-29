# State — last updated 2026-05-29

**Active focus:** `epic-analyzer-ga-hardening` → **s0-semgrep-rule-source in progress** (s0-t0 done; s0-t1 next). On branch `ccglass-traffic-analysis`, committed through `09c6154`.
**Last completed:** **s0-t0** (`09c6154`) — ADR-0016 semgrep rule provenance: vendored-in-bundle, `cache_root()` resolution, fail-loud on missing cache, CLI exposure of `semgrep_rules`. Verify PASS, Review MINOR-ONLY (findings applied). Baseline commit `2297081` carries the QA harness + epic + full s0 plan.
**Next:** **s0-t1** — vendor the curated ruleset under `.claude/skills/code-review/semgrep-rules/` and have `prefetch_caches.py`/`setup.sh` copy it into `cache_root()/cache/semgrep/rules` (idempotent), TDD. Then t2 (adapter: cache_root resolution, drop `auto`+`--metrics off` and the `--x-` flag, wire `semgrep_rules` config) → t3 (e2e green + de-hack smoke harness + mark F3 resolved). Then s1→s3. **Paused at this clean task boundary for context** — resume with `/clear`.

## Open questions / follow-ups

- **GA release blocked on `epic-analyzer-ga-hardening`.** Shipping `0.1.0` would advertise TypeScript coverage + security scanning that don't work on a fresh install (F1 depcruiser/Node, F2 jscpd, F3 semgrep, F5 JS toolchain). Fix the epic first, then: bump `pyproject.toml` → `0.1.0`, commit, cut + push GA tag `code-review-v0.1.0`. Runbook: `sdlc/docs/runbooks/release.md`. (Was: ready to ship — now gated.)
- **`claude-code-review` redirect meta-package** (ADR-0014): publish after the first GA publish.
- **Uncommitted on this branch:** QA harness + the 5 epic/story artefacts + a drafted README install-prereqs fix (F7, needs operator sign-off) + a `pyproject.toml` ruff `extend-exclude` for the QA fixtures. Nothing committed yet.
- **`analyze_ccglass.py`** carries 22 ruff errors on this branch (pre-existing, prior session) — would redden CI if this branch merges. Out of epic scope.

## Recent shipped (2026-05-29)

- **Analyzer-coverage QA** (uncommitted): regenerable smoke test (`scaffold_fixtures.sh` + `run_smoke.py`) covering all 13 adapters; `README.md` + `FINDINGS.md`. Reached 13/13 only with manual provisioning — the epic's job is to make a clean `setup.sh` sufficient.
- **(on `main`, e575b37) CI green**, test suite strict-typed; `polyreview 0.1.0rc1` on TestPyPI via `release.yml`. The old "CI failing on main" + mypy `conftest.py` follow-ups are resolved.
