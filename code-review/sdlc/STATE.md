# State — last updated 2026-05-29

**Active focus:** `epic-analyzer-ga-hardening` (**now 6 stories**, s0–s5) → **s0-semgrep-rule-source in progress** (s0-t0 done; s0-t1 next). On branch `ccglass-traffic-analysis`. A follow-up QA pass added F8 (eslint only works under harness scaffolding), F9 (CI green masks the *skipped* Node-analyzer integration tests — why F1/F2 hid), F10 (3 untested CLI error branches) → new stories s4 (eslint), s5 (CLI error tests) + an F9 AC on s1.
**Last completed:** **s0-t1** (`9a5bab1`) — vendored `semgrep-rules/security.yaml` (subprocess-shell-true, dangerous-eval) + `provision_semgrep_rules()` in `prefetch_caches.py` copies it into `cache_root()/cache/semgrep/rules`; setup.sh now provisions rules. Verify PASS (17/17), Review MINOR-ONLY (applied). s0-t0 (`09c6154`) = ADR-0016. Pushed through `d477d17`; `825cb43`+later local until this wrap pushes.
**Next:** **s0-t2** — adapter (`code_review/adapters/semgrep.py`): anchor `_semgrep_rules_dir()` on `cache_root()` (honor `$POLYREVIEW_CACHE_DIR`), remove the `--config auto` + `--metrics off` combo (fail loud, message names setup.sh), drop/guard `--x-ignore-semgrepignore-files`, and wire `semgrep_rules` through `load_config`/`code-review.toml`. TDD; extend `tests/test_adapters/test_semgrep.py`. Then t3 (e2e + de-hack smoke harness + mark F3 resolved), then s1→s5. **Paused at clean task boundary for context — resume with `/clear`.**

## Open questions / follow-ups

- **GA release blocked on `epic-analyzer-ga-hardening`.** Shipping `0.1.0` would advertise TypeScript coverage + security scanning that don't work on a fresh install (F1 depcruiser/Node, F2 jscpd, F3 semgrep, F5 JS toolchain). Fix the epic first, then: bump `pyproject.toml` → `0.1.0`, commit, cut + push GA tag `code-review-v0.1.0`. Runbook: `sdlc/docs/runbooks/release.md`. (Was: ready to ship — now gated.)
- **`claude-code-review` redirect meta-package** (ADR-0014): publish after the first GA publish.
- **Uncommitted on this branch:** QA harness + the 5 epic/story artefacts + a drafted README install-prereqs fix (F7, needs operator sign-off) + a `pyproject.toml` ruff `extend-exclude` for the QA fixtures. Nothing committed yet.
- **`analyze_ccglass.py`** carries 22 ruff errors on this branch (pre-existing, prior session) — would redden CI if this branch merges. Out of epic scope.

## Recent shipped (2026-05-29)

- **Analyzer-coverage QA** (uncommitted): regenerable smoke test (`scaffold_fixtures.sh` + `run_smoke.py`) covering all 13 adapters; `README.md` + `FINDINGS.md`. Reached 13/13 only with manual provisioning — the epic's job is to make a clean `setup.sh` sufficient.
- **(on `main`, e575b37) CI green**, test suite strict-typed; `polyreview 0.1.0rc1` on TestPyPI via `release.yml`. The old "CI failing on main" + mypy `conftest.py` follow-ups are resolved.
