# State — last updated 2026-05-26

**Active focus:** s2 (aggregator and severity mapping) complete and closed — all tasks (t0, t0-fix1, t1, t1-fix1, t2, t2-fix1, t3, t4, t4-fix1) in done/. Story-level review: MINOR-ONLY. 116/116 non-integration GREEN; ruff + mypy strict clean.

**Last completed:** `s2-aggregator-and-severity-mapping` — SARIF-to-SDLC severity mapping, multi-analyzer SARIF consolidation with CWE-keyed dedup (line tolerance), per-file hotspot composite score ranking, TOML config loader with weight overrides, CLI wiring (aggregate → hotspots → schema validation), `review-response.json` schema.

**Next:** `s3-remaining-deterministic-adapters` — plan needed before execution (SDLC rule #22). See `sdlc/work/active/s3-remaining-deterministic-adapters.md`.

## Open questions / known debt
- `Config.severity_overrides` is parsed from TOML but not yet wired into `map_severity()` — reserved for s3.
- Three duplicate `_SKILL_DIR` constants across `cli.py`, `config.py`, `hotspots.py` — refactor deferred.
- `_get_uri` / `_get_file_uri` duplicated in `aggregator.py` and `hotspots.py` — extract to shared helper in s3.
- `--capabilities` output lacks a schema; `analyzers` key shape differs from review-response — deferred debt from s0/s1.
- `_SKILL_DIR` sibling-path assumption breaks for a wheel install — deferred.
- Semgrep integration test needs binary on PATH (sandbox-gated) — deferred.
- Ruff is part of per-task green-bar; verifier/reviewer sub-agents still don't run it — run locally every task.
