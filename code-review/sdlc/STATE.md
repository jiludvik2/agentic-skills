# State — last updated 2026-06-01

**Active focus:** **EPIC `epic-analyzer-correctness`** — **all stories DONE (s1, s2); at the epic boundary.** Epic close (move to `done/` + Document/File) gated on operator push per rule #18.
**Last completed:** **s2 CLOSED** (s2-t0 gitleaks JSON-on-stdout fix; s2-t1 output-capture audit + regression guard). s1 closed earlier (eslint legacy-config → unavailable). Both story-level reviews MINOR-ONLY, Minors remediated.
**Next:** Operator: **push** the 6 epic commits to `origin/main`; optionally cut a release tag (propose `code-review-v0.1.1`, patch — these are correctness fixes on 0.1.0); then the epic moves to `done/`.

## Just landed (session 2026-06-01, execute epic-analyzer-correctness)

- **s1-t0** (`3388327`): eslint maps a legacy-only `.eslintrc*` target to `unavailable`
  (vendored ESLint v9 is flat-config-only, exited 2 → spurious `error` on express).
  `_has_eslint_config`→`_discover_eslint_config` (flat|legacy|none). Verifier PASS, per-task
  CLEAN; story-level MINOR-ONLY (none-branch message no longer lists `.eslintrc*`).
- **s2-t0** (`1dba1a5`): gitleaks writes an off-argv JSON report (`--report-format json
  --report-path <tmp>`, sandbox-safe) read back onto stdout — was a stderr-banner-only
  silent false-negative (10 leaks missed on pygoat). QA xfail→real pass; FINDINGS F15
  RESOLVED. Verifier PASS, reviewer CLEAN. Verified e2e via the CLI (count_gitleaks=1).
- **s2-t1** (`db3ba6b`,`cad5a73`): audited all 13 adapters — every one lands findings in
  `outputs[].stdout`; gitleaks was the sole defect, no sibling. New `output-capture-audit.md`
  + a CI regression guard (`tests/test_analyzer_output_capture_coverage.py`: every
  deterministic adapter must have a stdout-oracle run_smoke CASE). Closed the one gap it
  found: jscomplexity was missing from run_smoke (added a CASE).

## Epic-close checklist (pending)

- **Push** (rule #18): local `main` is **6 commits ahead** of `origin/main`
  (`3388327..aba8912`). AGENTS.md has no push pre-authorization → operator runs the push.
- **Release tag?** Propose `code-review-v0.1.1` (patch on GA 0.1.0; correctness fixes only,
  no contract change). Push the tag **standalone**, not bundled with `git push main`
  (memory `feedback-release-tag-push-standalone`), or release.yml may not trigger.
- **Document:** README needs no change — the analyzer changes align behaviour with the
  already-documented available/unavailable capability model (rule #17 satisfied).
- **Move epic to `done/`** once pushed; at that point also tidy the two retained records in
  `active/`: `fu-gitleaks-json-output-capture.md` (now fully superseded by s2) and
  `s0-jscomplexity-complexity-threshold.md` (WITHDRAWN record).

## Session gotchas (recurring)

- `uv run`/`uv build` panic under the sandbox → `.venv/bin/python|pytest|ruff|mypy`.
  Packaging tests (`test_wheel_packaging`, `test_console_script_install`) fail in-sandbox
  on `uv build` exit 101 — environmental, pass in CI.
- semgrep trips exit-2 under the sandbox (`--x-` flag) — 2 `test_semgrep` tests red
  in-sandbox, green unsandboxed. Not a regression.
- CLI `--output` must be a path **within CWD** under the sandbox.

## Open questions / carried-forward follow-ups

- Push + (optional) `code-review-v0.1.1` tag now, or batch with other work?
- Start the next epic, or pause? (epic boundary — operator's call)
- **TS complexity** (post-epic): vendor `@typescript-eslint/parser`, widen `jscomplexity`
  to TS (ADR-0022 documented limitation) — no adapter rewrite.
- **Stale doc:** `stack-pins.md` §License floor cites `scripts/license_audit.py` (absent).
