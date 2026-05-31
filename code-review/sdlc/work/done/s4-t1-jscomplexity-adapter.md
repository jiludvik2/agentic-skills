---
id: s4-t1-jscomplexity-adapter
kind: task
project: code-review
status: done
parent: s4-js-complexity-analyzer
sources: [s4-t0-adr-js-complexity-tool.md, adr-0020-thin-invocation-runner.md, adr-0011-review-selection-model.md]
created: 2026-05-31
updated: 2026-05-31
tags: [adapter, complexity, javascript, capabilities, test-first]
---

# Task s4-t1 — JS complexity adapter + wiring + tests

## Outcome

A new JS/TS complexity analyzer runs end-to-end: selected for JS/TS targets, it invokes the
chosen tool (recommended: vendored ESLint + adapter-supplied complexity config), captures
raw output, and reports per-function cyclomatic complexity. Wired into all four touchpoints,
proven by an invocation-contract test and an integration test. This is the substantive G8
architecture-validation: measure how additive it really is.

## Files to add / change (recommended option: reuse vendored ESLint)

1. **New adapter** `code_review/adapters/jscomplexity.py` — mirror `depcruiser.py`
   (adapter ships its own config in a `TemporaryDirectory`) + `eslint.py` (NODE_PATH export
   so the vendored `@microsoft/eslint-formatter-sarif` resolves). Class `JsComplexityAdapter`:
   - `name = "jscomplexity"`, `kind = "deterministic"`, `node_tool = "eslint"`,
     `default_timeout_s = 90`, `scope_restrictions = frozenset()`.
   - Availability (ADR-0019): `node_binary("eslint") is None` → unavailable (provisioning
     gap); `not request.target_paths` → unavailable; `not has_js_files(...)` → unavailable
     ("no JavaScript/TypeScript files in target"). Reuse `js_base` helpers.
   - Ship a complexity-only flat config to a tmp file, e.g.:
     ```js
     module.exports = [{ rules: { complexity: ["warn", 0] } }];
     ```
     (threshold 0 ⇒ every function reported with its computed complexity). Confirm the
     correct flat-config shape for eslint `^9` against the vendored binary before pinning
     the test (the eslint adapter notes v9 flat-config discovery quirks).
   - Invoke `node <eslint> --config <tmp-config> --no-config-lookup --format
     @microsoft/eslint-formatter-sarif <rel-targets>`; `--no-config-lookup` (or equivalent)
     so the host project's own config is NOT merged — the adapter's config is authoritative.
     `ok_exit_codes=(0, 1)` (1 = findings present), cwd anchored at the targets' common
     ancestor like the eslint adapter, NODE_PATH exported. Raw capture, no parsing.
2. **`code_review/adapters/__init__.py`** — import + `REGISTRY["jscomplexity"]`.
3. **`code_review/lang_select.py`** — add `"jscomplexity"` to `_JS_ADAPTERS`.
4. **`code_review/capabilities.json`** — new entry: `id="jscomplexity"`,
   `kind="deterministic"`, `domain="maintainability"`, `subcategory="complexity"`,
   `tier="quick"`, `languages=["javascript"]` (JS-only per ADR-0022 s4-t1 amendment),
   `rule_classes=["complexity"]`, `taxonomies_tagged=[]`, `default_timeout_s=90`,
   `scope_restriction=null`. Validate against `code_review/schemas/capabilities.json`.
5. **`tests/test_capabilities.py`** — add `jscomplexity` to the **locked-taxonomy table**
   in `test_taxonomy_matches_locked_table` (else it fails).
6. **Fixture** — `tests/fixtures/js-complexity/branchy.js` containing a function whose
   cyclomatic complexity is unmistakably > 1 (a chain of `if`/`else`/`&&`/ternary branches)
   so the reported number is non-trivial and stable. JS-only (TS is out of scope per the
   ADR-0022 amendment; eslint cannot parse `.ts` without the unvendored parser).

If the operator chose `eslintcc`/`ts-complex` instead: also add the `package.json` +
`package-lock.json` pin and a `stack-pins.md` Node/JS-toolchain row (ADR-0017), reconciled
in the same commit (SDLC rule #1b); the adapter then invokes that tool's CLI instead.

7. **SKILL.md docs (in this task — the guard forces it).** Adding `jscomplexity` to
   `REGISTRY` turns `test_every_analyzer_documented` RED until SKILL.md documents it, so the
   docs commit with the code:
   - **Per-tool reading guide** (near the radon row): a `jscomplexity` row — SARIF from the
     eslint complexity rule; each result names a function and its cyclomatic complexity;
     weight like radon's E/F ranks.
   - **Capabilities table** (the `maintainability | complexity | quick | py | any` row): show
     JS/TS coverage (broaden the row or add a sibling — match the table's convention).
   - **Limitations:** short lines stating (a) JS/TS cohesion (LCOM) is not provided (no thin
     tool fits) and (b) `jscomplexity` is JavaScript-only — TS complexity is not provided
     (eslint needs the unvendored `@typescript-eslint/parser`) — both cross-referencing
     ADR-0022.

## Acceptance criteria

- `JsComplexityAdapter` conforms to the `Analyzer` protocol (isinstance test) with the
  class attributes above.
- ADR-0019 mapping: missing eslint binary / no targets / no JS files each → `unavailable`
  (never `error`), and the tool is not invoked in those cases.
- Invocation-contract test pins the load-bearing argv: `--config <adapter config>`, the
  config-lookup suppression flag, `--format @microsoft/eslint-formatter-sarif`, NODE_PATH in
  env, `ok_exit_codes=(0, 1)`, cwd anchored at the common ancestor.
- Integration test (`@pytest.mark.integration`, skip if node/eslint absent): provisioned
  `node_modules` + the `js-complexity` `.js` fixture → `status=="ok"` and the captured SARIF
  contains a `complexity`-rule finding naming the fixture function and its computed value
  (assert the `complexity` ruleId and a `.js` location uri).
- `select_adapters(frozenset({"javascript"}))` includes `jscomplexity`;
  `select_adapters(frozenset({"python"}))` does not. (It is in `_JS_ADAPTERS` so a `{"typescript"}`
  selection also lists it; the capabilities `languages=[javascript]` filter is what scopes it
  to JS at selection time — no separate assertion needed beyond the python-exclusion.)
- All `test_capabilities.py` consistency tests pass (schema, REGISTRY membership, locked
  taxonomy, taxonomy tags).
- No change to `radon.py` or any existing JS adapter.
- SKILL.md documents `jscomplexity` (reading-guide row + capabilities row) and the JS
  cohesion limitation; `test_every_analyzer_documented` passes.
- `uv run pytest` (+ integration), `uv run ruff check .`, `uv run mypy code_review` clean.

## Test specification (write first, confirm RED)

1. **Adapter unit/contract tests** — new `tests/test_adapters/test_jscomplexity.py`,
   modelled on `test_semgrep.py`/`test_eslint` patterns:
   - protocol conformance;
   - argv-pinning test with `run_and_capture` patched (assert `--config`, config-lookup
     suppression, SARIF formatter, NODE_PATH, `ok_exit_codes`, cwd);
   - three `unavailable` pre-flights (no binary / no targets / no JS files), asserting the
     tool is never invoked.
   These run without node (mocked) and must be RED before the adapter exists (import error /
   missing attrs), GREEN after.
2. **Capabilities test** — extend `test_taxonomy_matches_locked_table`; RED until
   `capabilities.json` + the locked table both list `jscomplexity`.
3. **lang_select test** — assert `jscomplexity` selected for js/ts, not for python-only;
   RED until `_JS_ADAPTERS` updated.
4. **Integration test** — as in the AC. The eslint complexity-config invocation is already
   validated against the real vendored binary (s4-t1 pre-work): `node <eslint>
   --no-config-lookup --config <cfg.cjs> --format @microsoft/eslint-formatter-sarif <targets>`
   with `module.exports = [{ rules: { complexity: ["warn", 0] } }]` emits SARIF with one
   `complexity` result per function (e.g. "Function 'branchy' has a complexity of 7"),
   exit 0, NODE_PATH pointing at the vendored node_modules. `.ts` targets are silently
   ignored by eslint ("File ignored…", exit 0) — consistent with the JS-only scope.
5. **Doc guard** — `test_every_analyzer_documented` goes RED when `jscomplexity` enters
   `REGISTRY`; confirm it, then add the SKILL.md row to make it GREEN (this is why docs are
   in-task).

## Notes

- The eslint adapter (`eslint.py`) is the reference for NODE_PATH + cwd-anchoring + the v9
  flat-config discovery behaviour; depcruiser (`depcruiser.py`) is the reference for an
  adapter shipping its own config via `TemporaryDirectory`. This adapter combines both.
- Keep the analyzer id distinct from `eslint` so the lint and complexity analyzers remain
  separately selectable and separately interpretable in the bundle.
- ADR-0020: capture raw, do not parse. The agent reads the SARIF the formatter emits.
