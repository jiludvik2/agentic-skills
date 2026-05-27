# State — last updated 2026-05-27

**Active focus:** s3 Milestones A and B complete. Milestone C (JS adapters, t8–t11) not yet started.

**Last completed:** s3 t0–t7 via subagent-driven development (implementer + spec + quality review per task).
- **t0:** sarif_utils.py + ADR-0007 contract consolidation (schemas/capabilities.json into package, Path(__file__) readers, wheel package-data)
- **t1:** BanditAdapter (JSON shim → SARIF)
- **t2:** VultureAdapter (Python API → SARIF) + dead.py fixture
- **t3:** PydepsAdapter (module coupling metrics + SARIF)
- **t4:** CohesionAdapter (LCOM4 metrics + SARIF) + cohesive.py fixture
- **t5:** GitleaksAdapter (SARIF native, binary)
- **t6:** TrivyAdapter (offline SARIF, binary + pre-fetched DB guard)
- **t7:** Semgrep offline fix — local rules fixture, `--metrics off`, `SEMGREP_LOG_FILE`/`SEMGREP_SETTINGS_FILE` env vars (pysemgrep 1.161.0 does not support `SEMGREP_USER_DATA_FOLDER`), `--x-ignore-semgrepignore-files` (experimental, prevents tests/ from being silently excluded)

**Green bar:** 156 passed, 2 skipped (gitleaks + trivy integration tests; binaries not installed), 0 failures.

**Next:** Execute Milestone C via subagent-driven development:
- **t8:** JS adapter infrastructure (`js_base.py`, `_probe_analyzer` extension, JS fixtures)
- **t9:** eslint adapter
- **t10:** jscpd adapter
- **t11:** knip + dependency-cruiser adapters + per-language selection (`lang_select.py`)

## Open questions / known debt
- `code-review.toml` location — operator config still read from the skill dir (`_SKILL_DIR` kept in cli.py for this); ADR-0007 defers the decision of whether it should be CWD-relative instead.
- `Config.severity_overrides` parsed from TOML but not wired into `map_severity()` — reserved for s3-t11.
- `--capabilities` output lacks a schema; `analyzers` key shape differs from review-response — deferred from s0/s1.
- `--x-ignore-semgrepignore-files` in semgrep.py is experimental (undocumented, may be removed). Alternative: `--no-git-ignore`. Worth revisiting if semgrep is upgraded.
- Ruff is part of per-task green-bar; verifier/reviewer sub-agents still don't run it — run locally every task.
