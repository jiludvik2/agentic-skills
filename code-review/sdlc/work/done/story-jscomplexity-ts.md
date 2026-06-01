---
id: story-jscomplexity-ts
kind: story
project: code-review
status: done
children:
  - jscomplexity-ts-t0-vendor-parser
  - jscomplexity-ts-t1-enable-ts-parsing
sources: [adr-0022-js-complexity-tool.md]
created: 2026-06-01
updated: 2026-06-01
tags: [jscomplexity, typescript, eslint, complexity, adr-0022, post-ga]
---

# Story — jscomplexity: TypeScript complexity support

## Why

`jscomplexity` (ADR-0022) reuses the vendored ESLint `complexity` core rule at threshold 0
to report per-function cyclomatic complexity — radon-`cc` parity for **JavaScript**. The
s4-t1 amendment narrowed it to JS only: ESLint's default parser (espree) can't parse `.ts`
type annotations, and `@typescript-eslint/parser` was not vendored. ADR-0022 names this
exact follow-up: *"Adding it later = vendor `typescript-eslint` + widen `capabilities`, no
rewrite."* This story does that, scoped to the **parser only** (operator decision
2026-06-01 — complexity is a syntactic rule, the lint plugin is not needed).

A TypeScript review currently gets dead-code (knip), duplication (jscpd), coupling
(depcruiser), lint (eslint) — but **no complexity signal**. This closes that gap.

## Scope

- `.ts/.tsx/.mts/.cts` already pass `has_js_files` (js_base) and `lang_select._JS_ADAPTERS`
  already routes them to `jscomplexity` — so the availability gate and diff-routing need **no
  change**. The only gaps are (a) the parser is not vendored and (b) the adapter-supplied flat
  config and the advertised `capabilities.languages` are JS-only.
- **No `tsconfig` / type-aware linting:** the `complexity` rule is syntactic (counts
  branches), so the TS parser needs no `parserOptions.project`. This preserves the
  host-config-independent determinism (`--no-config-lookup`) the adapter already relies on.

## Acceptance criteria

- A `.ts` target with a branchy function → `jscomplexity` reports that function's cyclomatic
  complexity as a `complexity`-rule SARIF result in captured `stdout` (real vendored
  toolchain), at parity with the existing JS behaviour.
- Existing JS behaviour unchanged (regression): a `.js` target still reports complexity.
- `jscomplexity` advertises `languages` including `typescript` (capabilities), so
  `--review complexity`/`maintainability` selects it for a TS diff.
- `@typescript-eslint/parser` is vendored, pinned, and recorded in `stack-pins.md` +
  an ADR-0022 amendment; the JS-only limitation note (ADR-0022 / SKILL.md) is updated.
- The parser resolves via the adapter's existing vendored `NODE_PATH` export (no host
  `node_modules` dependency).

## Tasks (plan)

- **t0 — vendor `@typescript-eslint/parser`** + widen advertised capabilities to TS.
- **t1 — enable TS parsing** in the adapter's complexity flat config + TS fixture/integration
  test + docs.

## Notes

- Dependency pin (`@typescript-eslint/parser ^8`, MIT, eslint-9/TS-5 compatible) goes through
  ADR-0022 amendment + `stack-pins.md` in the same commit as the manifest change (free-pass
  dep-add implied by an accepted decision; ADR-0017 governs node pins).
- `typescript@^5` (the compiler) is already vendored for depcruiser; `@typescript-eslint/parser`
  needs `typescript` + `eslint` peers, both present.

## Close notes (2026-06-01)

All 5 ACs met. **t0** vendored `@typescript-eslint/parser ^8.60.0` (parser-only) + advertised
`typescript` in capabilities + stack-pins/ADR amendment. **t1** wired the parser into the
complexity flat config for `.ts/.tsx/.mts/.cts`, added fixture + integration tests + a
stack-pins↔lockfile drift anchor, and reconciled all "JS-only" docs.

Story-level review: **MINOR-ONLY** (no Critical/Important). Both Minors fixed inline rather
than deferred: (a) ADR-0022 title still said "(JS-only; TS deferred)" → updated to "(TS added
2026-06-01)"; (b) advertised glob covered 4 extensions but only `.ts` was tested → added a
parametrized integration test for `.tsx/.mts/.cts` (empirically confirmed all four fire the
complexity rule). The one Nit (exit-code comment) dropped per taxonomy.

Gates at close: 11 jscomplexity tests green, ruff + mypy clean. Full suite shows only the 9
documented environmental sandbox failures (wheel/console-script `uv build` exit 101; semgrep
`--x-` exit 2) — green in CI. Rule #26 (supply-chain gate) N/A: project defines no such gate.

No epic parent — standalone post-GA story. Pause at this boundary.
