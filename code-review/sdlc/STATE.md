# State — last updated 2026-05-27

**Active focus:** s1 fully closed (s1-t0 and s1-t3 filed to done/). s2 closed. Ready to plan s3.

**Last completed:** Housekeeping — removed duplicate schema from sandbox-blocked `.claude/skills/` path; filed stray s1 tasks (s1-t0 skill scaffold, s1-t3 setup.sh) that were implemented but never moved to done/; dropped stale `type: ignore` in semgrep.py (jsonschema now ships stubs). Green bar: 125/126 pass (1 pre-existing semgrep integration failure, sandbox-gated, documented below).

**Next:** `s3-remaining-deterministic-adapters` — plan needed before execution (SDLC rule #22). See `sdlc/work/active/s3-remaining-deterministic-adapters.md`.

## Open questions / known debt
- `Config.severity_overrides` is parsed from TOML but not yet wired into `map_severity()` — reserved for s3.
- Three duplicate `_SKILL_DIR` constants across `cli.py`, `config.py`, `hotspots.py` — refactor deferred.
- `_get_uri` / `_get_file_uri` duplicated in `aggregator.py` and `hotspots.py` — extract to shared helper in s3.
- `--capabilities` output lacks a schema; `analyzers` key shape differs from review-response — deferred debt from s0/s1.
- `_SKILL_DIR` sibling-path assumption breaks for a wheel install — deferred.
- Semgrep integration test (`test_semgrep_produces_valid_sarif`) fails: binary is on PATH but returns no findings for the fixture — investigate before/during s3 Semgrep cache-dir work.
- Ruff is part of per-task green-bar; verifier/reviewer sub-agents still don't run it — run locally every task.
