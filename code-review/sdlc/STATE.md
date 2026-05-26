# State — last updated 2026-05-26

**Active focus:** Executing s0 — `s0-t0` complete, auto-progressing to `s0-t1` (contracts module).

**Last completed:** `s0-t0` — package scaffolded and all 4 tests GREEN: `pyproject.toml` (PEP 621, hatchling, exact pins), `code_review/__init__.py` (`__version__`), `schemas/sarif-2.1.0.json` (fetched from SchemaStore), `.gitignore` (covers `runs/`, `cache/`, `node_modules/`, `.venv/`).

**Next:** `s0-t1` — contracts module: `Analyzer` Protocol, `AnalyzerOutput`, `MetricSet`, `ReviewRequest`. Write tests first.

## Open questions
- `excludedCommands: ["uv *"]` not bypassing Seatbelt sandbox (SCDynamicStore panic). All `uv` commands require `dangerouslyDisableSandbox: true`. Needs investigation.
