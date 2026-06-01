# State — last updated 2026-06-01

**Active focus:** **STORY `story-jscomplexity-ts`** (TypeScript complexity support, ADR-0022 follow-up). **t0 DONE; t1 next.** Halted at the task boundary for context pressure.
**Last completed:** **t0 `jscomplexity-ts-t0-vendor-parser`** — vendored `@typescript-eslint/parser ^8.60.0` (parser-only, operator decision), `capabilities.json` advertises `typescript`, stack-pins + ADR-0022 amendment. Verifier PASS (after a 1-line ADR-consistency fix), reviewer MINOR-ONLY.
**Next:** Execute **t1 `jscomplexity-ts-t1-enable-ts-parsing`** — wire the TS parser into the adapter's complexity flat config + TS fixture/integration test + lift the ADR-0022/SKILL.md JS-only limitation.

## Resume t1 (fresh session — suggest `/clear`)

- **t1 spec:** `sdlc/work/active/jscomplexity-ts-t1-enable-ts-parsing.md`. Add a second flat-config
  block in `code_review/adapters/jscomplexity.py` `_COMPLEXITY_CONFIG` pointing
  `languageOptions.parser` at `require("@typescript-eslint/parser")` for `**/*.{ts,tsx,mts,cts}`
  (resolves via the adapter's existing vendored `NODE_PATH`; no `tsconfig`/type-aware setup).
- **Tests-first:** new fixture `tests/fixtures/js-complexity/branchy.ts` (typed branchy fn) →
  integration test asserts ≥1 `complexity` SARIF result locating `branchy.ts` (RED today). Keep the
  `branchy.js` test green. Vendored eslint binary IS present, so the integration test runs locally.
- **Carried into t1 (from t0 reviewer, MINOR + watch-items):**
  - Add a drift anchor for the parser pin (assert `node_modules/@typescript-eslint/parser` in the
    lockfile matches stack-pins) — `jscomplexity` has no `npm_package` row so it's outside the
    existing `test_capabilities_node_versions_match_lockfile` guard.
  - When lifting the ADR-0022 "Declared limitations → TypeScript complexity" entry, add the
    "superseded note" the 2026-06-01 amendment promises (else the cross-ref dangles).
  - Nit: tidy the `test_jscomplexity_advertises_typescript` docstring citation trail.
- After t1: story-level review for `story-jscomplexity-ts`, then story close.

## Publish

- **2 commits unpushed** to `origin/main`: `95c1a22` (plan) + `f4a9d1d` (t0). Push is operator-gated
  (no pre-auth in AGENTS.md). No release tag needed until the story closes (would be a patch, e.g.
  `code-review-v0.1.2`, if cut).

## Session gotchas (recurring)

- `uv run`/`uv build` panic under the sandbox → `.venv/bin/python|pytest|ruff|mypy`. Wheel/
  console-script packaging tests fail in-sandbox on `uv build` exit 101 (environmental, green in CI).
- semgrep `--x-` exit-2 under the sandbox → 2 `test_semgrep` tests red in-sandbox, green unsandboxed.
- `npm install` (toolchain vendoring) needs the sandbox disabled — registry network AND
  `~/.npm/_cacache` writes are both blocked (memory `code-review-npm-install-needs-sandbox-disabled`).

## Open questions / carried-forward follow-ups

- Push the 2 commits now, or batch at story close?
- **TS cohesion** stays a documented gap (ADR-0022) — no suitable tool.
- **Stale doc:** `stack-pins.md` §License floor cites `scripts/license_audit.py` (absent).
