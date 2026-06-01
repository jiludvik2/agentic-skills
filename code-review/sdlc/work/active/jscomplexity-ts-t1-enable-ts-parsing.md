---
id: jscomplexity-ts-t1-enable-ts-parsing
kind: task
project: code-review
status: active
parent: story-jscomplexity-ts
sources: [story-jscomplexity-ts.md, adr-0022-js-complexity-tool.md]
created: 2026-06-01
updated: 2026-06-01
tags: [jscomplexity, typescript, eslint, complexity, config]
---

# Task — enable TypeScript parsing in the complexity config

## Outcome

The adapter-supplied complexity flat config parses `.ts/.tsx/.mts/.cts` with the vendored
`@typescript-eslint/parser`, so `jscomplexity` reports per-function cyclomatic complexity for
TypeScript at parity with JavaScript — no `tsconfig`, no type-aware setup (the `complexity`
rule is syntactic).

## Acceptance criteria

- A `.ts` target with a branchy function → a `complexity`-rule SARIF result naming that
  function with its computed value, in captured `stdout` (real vendored toolchain).
- JS behaviour unchanged (the existing `branchy.js` integration test still passes).
- The parser resolves via the adapter's existing vendored `NODE_PATH` export — no host
  `node_modules`, no config-lookup of the reviewed project (`--no-config-lookup` retained).
- Docstrings/comments asserting "JavaScript-only" / ".ts ignored" updated; SKILL.md +
  ADR-0022 "Declared limitations" reconciled (TS complexity now implemented).

## Test specification (write first, confirm RED)

1. Integration (real vendored toolchain, gated like the existing JS integration test): a
   fixture `tests/fixtures/js-complexity/branchy.ts` (a typed branchy function) →
   `jscomplexity` returns `status==ok` and ≥1 SARIF result with `ruleId` containing
   `complexity`, locating `branchy.ts`. **RED today:** the flat config sets no TS parser, so
   espree can't parse the annotations → 0 results (and pre-t0 the parser isn't even vendored).
2. Regression: the existing `branchy.js` integration test (`test_jscomplexity_reports_per_function_complexity`)
   still passes (JS path unchanged).
3. Update `test_jscomplexity.py`'s module docstring / any assertion that pins JS-only.

## Implementation notes

- `code_review/adapters/jscomplexity.py` `_COMPLEXITY_CONFIG`: add a second flat-config block
  scoping the TS files to the parser, e.g.:
  ```js
  const tsParser = require("@typescript-eslint/parser");
  module.exports = [
    { rules: { complexity: ["warn", 0] } },
    { files: ["**/*.ts","**/*.tsx","**/*.mts","**/*.cts"],
      languageOptions: { parser: tsParser },
      rules: { complexity: ["warn", 0] } },
  ];
  ```
  `require("@typescript-eslint/parser")` resolves via the `NODE_PATH` the adapter already
  exports to the vendored `node_modules` (same mechanism as the SARIF formatter) — confirm in
  the integration test, which runs from a cwd with no host `node_modules`.
- No `parserOptions.project` — `complexity` is syntactic; avoid coupling to a host tsconfig.
- Depends on t0 (parser vendored). Gates: `.venv/bin/pytest`, `.venv/bin/ruff check .`,
  `.venv/bin/mypy code_review`.
