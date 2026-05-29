# State — last updated 2026-05-29

**Active focus:** `epic-analyzer-ga-hardening` (active, **4 stories unplanned**) — pre-GA fixes for the 4 ship-blockers the analyzer-coverage QA test found. Filed on branch `ccglass-traffic-analysis` (uncommitted).
**Last completed:** Analyzer-coverage smoke test (`sdlc/docs/qa/analyzer-coverage/`): all 13 analyzers exercised against synthetic code — **11/13 pass**, 2 broken + semgrep broken OOB. Findings in `FINDINGS.md`; compiled into the new epic.
**Next:** execute the **s0 plan** (4 tasks: t0 ADR → t1 vendor/provision → t2 adapter fix → t3 e2e). Rule-provenance **decided: vendored-in-bundle** (operator, 2026-05-29). Ready to start s0-t0 on operator go. Then s1→s3. GA gated on this epic.

## Open questions / follow-ups

- **GA release blocked on `epic-analyzer-ga-hardening`.** Shipping `0.1.0` would advertise TypeScript coverage + security scanning that don't work on a fresh install (F1 depcruiser/Node, F2 jscpd, F3 semgrep, F5 JS toolchain). Fix the epic first, then: bump `pyproject.toml` → `0.1.0`, commit, cut + push GA tag `code-review-v0.1.0`. Runbook: `sdlc/docs/runbooks/release.md`. (Was: ready to ship — now gated.)
- **`claude-code-review` redirect meta-package** (ADR-0014): publish after the first GA publish.
- **Uncommitted on this branch:** QA harness + the 5 epic/story artefacts + a drafted README install-prereqs fix (F7, needs operator sign-off) + a `pyproject.toml` ruff `extend-exclude` for the QA fixtures. Nothing committed yet.
- **`analyze_ccglass.py`** carries 22 ruff errors on this branch (pre-existing, prior session) — would redden CI if this branch merges. Out of epic scope.

## Recent shipped (2026-05-29)

- **Analyzer-coverage QA** (uncommitted): regenerable smoke test (`scaffold_fixtures.sh` + `run_smoke.py`) covering all 13 adapters; `README.md` + `FINDINGS.md`. Reached 13/13 only with manual provisioning — the epic's job is to make a clean `setup.sh` sufficient.
- **(on `main`, e575b37) CI green**, test suite strict-typed; `polyreview 0.1.0rc1` on TestPyPI via `release.yml`. The old "CI failing on main" + mypy `conftest.py` follow-ups are resolved.
