# State — last updated 2026-05-27

**Active focus:** s1 and s2 closed. s3 fully planned — `sdlc/work/active/s3-plan.md` (12 tasks, 3 milestones) + ADR-0007 accepted. Execution not yet started.

**Last completed:** s3 planning. Wrote the implementation plan (10 adapters: bandit, vulture, pydeps, cohesion, gitleaks, trivy, eslint, jscpd, knip, depcruiser + shared infra + per-language selection). Reviewed contract/schema management and recorded **ADR-0007** (package-bundled contracts): the `code_review` package becomes the single source of truth for `capabilities.json` + the four JSON schemas, resolved via `Path(__file__)`. Plan task t0 was rewritten to do that full consolidation (moves all schemas into the package, deletes repo-root `/schemas/` and the skill-dir `capabilities.json`, collapses the `_SKILL_DIR` constants). Earlier housekeeping: filed stray s1-t0/s1-t3 to done/, dropped stale `type: ignore` in semgrep.py.

**Next:** Execute s3 via subagent-driven development, starting with **t0** (ADR-0007 consolidation + `sarif_utils.py` + `env` param). Fresh implementer subagent per task; two-stage review (spec then quality) after each.

## Open questions / known debt
- **Resolved by s3-t0 when executed (per ADR-0007):** three duplicate `_SKILL_DIR` constants; `_SKILL_DIR` wheel-install break (`semgrep.py` reading repo root); sandbox-write friction for contracts.
- `code-review.toml` location — operator config still read from the skill dir; ADR-0007 defers the decision of whether it should be CWD-relative instead.
- `Config.severity_overrides` is parsed from TOML but not yet wired into `map_severity()` — reserved for s3 (Config.disabled_analyzers wired in s3-t11).
- `_get_uri` / `_get_file_uri` duplicated in `aggregator.py` and `hotspots.py` — extract to shared helper (folded into s3-t0 `sarif_utils.py`).
- `--capabilities` output lacks a schema; `analyzers` key shape differs from review-response — deferred debt from s0/s1.
- Semgrep integration test (`test_semgrep_produces_valid_sarif`) fails: binary is on PATH but `--config auto` fetches from registry and returns no findings — fixed in s3-t7 (local rule fixture + `SEMGREP_USER_DATA_FOLDER`).
- Ruff is part of per-task green-bar; verifier/reviewer sub-agents still don't run it — run locally every task.
