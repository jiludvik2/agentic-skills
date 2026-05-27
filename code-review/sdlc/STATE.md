# State — last updated 2026-05-27

**Active focus:** s3 complete (all three milestones). Next: s4 (contract testing) or s5 (subagent integration).

**Last completed:** s3 t0–t11 via subagent-driven development (implementer + spec + quality review per task).
- **t0:** sarif_utils.py + ADR-0007 contract consolidation
- **t1:** BanditAdapter (JSON shim → SARIF)
- **t2:** VultureAdapter (Python API → SARIF) + dead.py fixture
- **t3:** PydepsAdapter (module coupling metrics + SARIF)
- **t4:** CohesionAdapter (LCOM4 metrics + SARIF) + cohesive.py fixture
- **t5:** GitleaksAdapter (SARIF native, binary) — uses `tempfile.TemporaryDirectory`
- **t6:** TrivyAdapter (offline SARIF, binary + pre-fetched DB guard) — uses `tempfile.TemporaryDirectory`
- **t7:** Semgrep offline fix — local rules, `SEMGREP_LOG_FILE`/`SEMGREP_SETTINGS_FILE`, `tempfile.TemporaryDirectory`
- **t8:** JS adapter infrastructure (`js_base.py`, `_probe_analyzer` extension, JS fixtures, 5 tests)
- **t9:** EslintAdapter (vendored binary, SARIF formatter, integration skipif guard)
- **t10:** JscpdAdapter, KnipAdapter, DependencyCruiserAdapter (JSON→SARIF, integration skipif guards)
- **t11:** REGISTRY (12 adapters), `lang_select.py` + `--language` CLI flag, `disabled_analyzers` (Config + CLI), capabilities.json updated, `test_sandbox_compatibility.py`, `test_lang_select.py`

**Green bar:** 191 passed, 6 skipped (gitleaks + trivy + 4 JS integration tests; binaries/node_modules not installed), 0 failures.

## Open questions / known debt
- `code-review.toml` location — operator config still read from the skill dir (`_SKILL_DIR` kept in cli.py for this); ADR-0007 defers the decision of whether it should be CWD-relative instead.
- `Config.severity_overrides` parsed from TOML but not wired into `map_severity()` — reserved for s4+.
- `--capabilities` output lacks a schema; `analyzers` key shape differs from review-response — deferred from s0/s1.
- `--x-ignore-semgrepignore-files` in semgrep.py is experimental (undocumented, may be removed). Alternative: `--no-git-ignore`. Worth revisiting if semgrep is upgraded.
- JS adapters error message says "not found. Run scripts/setup.sh first." even when node itself is absent from PATH — would benefit from `probe_js_adapter` for a richer message (tracked, low priority).
- `package.json` / `package-lock.json` not yet created; JS integration tests always skip until `npm ci` is run via `scripts/setup.sh`.
- Ruff is part of per-task green-bar; verifier/reviewer sub-agents still don't run it — run locally every task.
