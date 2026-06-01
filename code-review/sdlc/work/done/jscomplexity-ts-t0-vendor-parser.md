---
id: jscomplexity-ts-t0-vendor-parser
kind: task
project: code-review
status: done
parent: story-jscomplexity-ts
sources: [story-jscomplexity-ts.md, adr-0022-js-complexity-tool.md]
created: 2026-06-01
updated: 2026-06-01
tags: [jscomplexity, typescript, dependency, stack-pins, adr-0022]
---

# Task — vendor `@typescript-eslint/parser` + advertise TS

## Outcome

`@typescript-eslint/parser` is vendored into the JS toolchain (resolvable via the adapter's
existing `NODE_PATH`), pinned and recorded; `jscomplexity` advertises `typescript` so the
selection scheme routes a TS diff to it. (Wiring the parser into the complexity config is t1.)

## Acceptance criteria

- `@typescript-eslint/parser` added to the vendored `package.json` dependencies, pinned
  `^8` (MIT; eslint-9 / TS-5 compatible — peers `eslint@^9` + `typescript@^5` already present),
  and locked in `package-lock.json`.
- `code_review/capabilities.json` `jscomplexity.languages` = `["javascript", "typescript"]`.
- `stack-pins.md` Node/JS toolchain table gains a `@typescript-eslint/parser` row (manifest
  pin + role, ADR-0017 style); ADR-0022 carries an amendment recording the parser-only
  decision (operator 2026-06-01) and that TS complexity is now implemented (move it out of
  "Declared limitations, not implemented" — coordinate the prose with t1's doc updates).
- Any capabilities↔manifest drift guard still passes.

## Test specification (write first, confirm RED)

1. Unit/capabilities: assert the `jscomplexity` analyzer entry advertises `typescript` (read
   `capabilities.json` or the capabilities API). **RED today:** `languages == ["javascript"]`.
2. If a capabilities-vs-registry / manifest-drift meta-test exists (cf.
   `test_node_integration_gating`, `test_capabilities`), confirm it still passes with the
   widened languages and the new dependency.

## Implementation notes

- **Network gate:** vendoring runs `npm install @typescript-eslint/parser@^8` in the skill
  `node_modules` (updates `package.json` + `package-lock.json`). `registry.npmjs.org` is **not**
  in the sandbox allow-list, so the install needs either an operator-approved sandbox-disable
  for that one command or the operator runs it. Escalate at that step (do not disable the
  sandbox unilaterally — memory `feedback-always-ask-before-disabling-sandbox`).
- Vendored install dir: `.claude/skills/code-review/` (package.json there; `setup.sh` runs
  `npm ci`, so no setup.sh change beyond the manifest).
- `capabilities.json` is the static source of truth (lockfile is SSOT for versions per
  ADR-0017) — edit the `languages` array directly.
- Gates: `.venv/bin/pytest`, `.venv/bin/ruff check .`, `.venv/bin/mypy code_review`.
