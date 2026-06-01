# State — last updated 2026-06-01

**Active focus:** **EPIC `epic-analyzer-correctness`** (post-GA analyzer correctness) — **PLANNED, awaiting operator go to execute.** 2 stories / 3 tasks filed; none started.
**Last completed:** **EPIC `epic-analyzer-thin-runner` CLOSED** (s0–s5). Document + File done; analyzer layer ships `review-bundle.v1.json` raw capture (ADR-0020), facade deleted.
**Next:** Operator decides — execute `epic-analyzer-correctness` (start `s1-t0`), push, and/or cut a release tag.

## Just landed (session 2026-06-01)

- **Dogfooded the GA analyzer layer** on public repos: pygoat, NodeGoat,
  requests/flask/scrapy (Python coupling/cohesion), express/mocha/chalk/axios/webpack
  (JS coupling). webpack = 1670 circular edges; flask/scrapy SCCs detected by pydeps.
- **Filed + planned `epic-analyzer-correctness`** from the dogfooding defects.
- **Closed `epic-analyzer-thin-runner`:** epic → `done/` (status done + close-notes);
  ADRs 0020/0021/0022 → `docs/decisions/`; README reconciled (bundle model already
  present; added `jscomplexity` to the JS analyzer list).
- **`fu-gitleaks-json-output-capture`** superseded by `s2-adapter-output-capture-audit`;
  retained in `active/` as a record (banner).

## epic-analyzer-correctness — planned, NOT started

- **s1-t0-eslint-legacy-config-unavailable** — legacy-only `.eslintrc*` target →
  `unavailable`, not exit-2 `error` (vendored ESLint v9 is flat-config-only).
- **s2-t0-gitleaks-json-report** — off-argv JSON report read-back so structured
  findings land in `stdout` (empirically only a count reaches either stream); QA
  `gitleaks` xfail → pass.
- **s2-t1-output-capture-audit** — audit all 13 deterministic adapters for stdout
  capture; tighten the QA "≥1 signal" guard.
- **s0-jscomplexity WITHDRAWN** — not a defect (intended radon-cc parity, ADR-0022);
  kept as a record, ids s1/s2 left stable (gap at s0 intentional).
- All tasks carry tests-first specs. Gates: `.venv/bin/{pytest,ruff,mypy code_review}`
  (NOT `uv run` — sandbox panic).

## Publish

- Local `main` is ahead of `origin/main` (this session's compile + plan + close
  commits). Push when ready (rule #18; push a release tag standalone if cutting one).
- **No release tag** cut for the thin-runner epic close — propose one? Current GA is
  `0.1.0` (epic-analyzer-polish); thin-runner is an internal re-architecture (no
  user-facing CLI/contract break beyond what 0.1.0 shipped) — likely a minor/patch
  bump if tagged.

## Session gotchas (recurring)

- `uv run` panics under the sandbox (macOS system-configuration probe) →
  `.venv/bin/python|ruff|mypy`.
- semgrep trips exit-2 under the sandbox (`--x-` flag) — run outside sandbox
  (operator-approved) for real semgrep findings; in-sandbox it reads as `error`.
- gitleaks emits findings to stderr as a **count only** (no per-finding detail on
  either stream) until the s2-t0 report-path fix lands.

## Open questions / carried-forward follow-ups

- Execute `epic-analyzer-correctness` now, or other priorities first?
- Release tag for the thin-runner close (and version)?
- **TS complexity** (post-epic): vendor `@typescript-eslint/parser`, widen
  `jscomplexity` to TS (ADR-0022 documented limitation) — no adapter rewrite.
- **Stale doc:** `stack-pins.md` §License floor cites `scripts/license_audit.py`
  (absent); no dependency-audit gate wired (rule #26 n/a here).
