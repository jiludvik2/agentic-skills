# State — last updated 2026-06-01

**Active focus:** none — **`epic-analyzer-correctness` CLOSED** and pushed. `work/active/` is empty.
**Last completed:** **EPIC `epic-analyzer-correctness`** (s1 eslint legacy-config→unavailable; s2 gitleaks JSON-on-stdout + all-adapter output-capture audit + CI regression guard). All commits on `origin/main` (`…19a7073` + close commit).
**Next:** Operator decides the next epic. Optional carry-overs: cut `code-review-v0.1.1` (patch on GA 0.1.0; no contract change) and/or start TS-complexity work (vendor `@typescript-eslint/parser`, ADR-0022).

## Just closed (session 2026-06-01)

- **s1-t0 / s1** — eslint maps a legacy-only `.eslintrc*` to `unavailable` (vendored ESLint
  v9 is flat-config-only; previously exited 2 → spurious `error` on express).
- **s2-t0** — gitleaks writes an off-argv JSON report read back onto stdout (was a
  stderr-banner-only silent false-negative; 10 leaks missed on pygoat). QA xfail→real pass;
  FINDINGS F15 RESOLVED; verified e2e via the CLI.
- **s2-t1** — audited all 13 deterministic adapters: every one lands findings in
  `outputs[].stdout`; gitleaks was the sole defect, no sibling. New `output-capture-audit.md`
  + CI guard (`tests/test_analyzer_output_capture_coverage.py`); closed the jscomplexity
  QA-harness coverage gap (added a run_smoke CASE).
- Epic + the two retained records (`fu-gitleaks-json-output-capture`, withdrawn
  `s0-jscomplexity-complexity-threshold`) moved to `done/`. README unchanged (rule #17:
  fixes align behaviour with the documented available/unavailable model).

## Open questions / carried-forward follow-ups

- Cut `code-review-v0.1.1` now? (push the tag **standalone** — memory
  `feedback-release-tag-push-standalone`.)
- Next epic, or pause?
- **TS complexity** (post-epic): vendor `@typescript-eslint/parser`, widen `jscomplexity`
  to TS (ADR-0022 documented limitation) — no adapter rewrite.
- **Stale doc:** `stack-pins.md` §License floor cites `scripts/license_audit.py` (absent);
  no dependency-audit gate wired (rule #26 n/a here).

## Session gotchas (recurring)

- `uv run`/`uv build` panic under the sandbox → `.venv/bin/python|pytest|ruff|mypy`.
  `test_wheel_packaging`/`test_console_script_install` fail in-sandbox on `uv build`
  exit 101 — environmental, green in CI.
- semgrep trips exit-2 under the sandbox (`--x-` flag) — 2 `test_semgrep` tests red
  in-sandbox, green unsandboxed.
- CLI `--output` must be a path **within CWD** under the sandbox.
