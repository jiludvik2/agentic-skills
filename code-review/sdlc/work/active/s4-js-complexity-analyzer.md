---
id: s4-js-complexity-analyzer
kind: story
project: code-review
status: active
parent: epic-analyzer-thin-runner
children:
  - s4-t0-adr-js-complexity-tool
  - s4-t1-jscomplexity-adapter
sources: [epic-analyzer-thin-runner.md, g8-js-complexity-cohesion-absent.md, adr-0011-review-selection-model.md, adr-0017-node-range-and-js-toolchain-pins.md]
created: 2026-05-31
updated: 2026-05-31
tags: [complexity, javascript, typescript, maintainability, eslint, radon-parity]
---

# Story s4 — G8: JS/TS complexity analyzer (radon parity)

## Why

The `maintainability/complexity` subcategory is Python-only: `radon cc --json` reports
per-function cyclomatic complexity, but there is **no JS/TS equivalent** (G8). A JS review
gets dead-code (knip), duplication (jscpd), coupling (depcruiser), and lint (eslint) — but
no complexity signal. This story adds one, giving `--review complexity` (and the
`maintainability` domain) parity across both language families.

This is the epic's **second architecture-validation** (G8): per ADR-0020 the thin-runner
design claims adding a JS complexity analyzer must be *near-trivial*. The s3 result (JS
semgrep rules, zero adapter change) supports that; G8 is a harder test because it adds a
genuinely new analyzer (adapter + registry + capabilities + selection), not just a rule
file. If it is hard, the architecture is wrong.

## The parity target (important — narrows scope)

The **radon adapter runs only `cc --json`** (cyclomatic complexity per function), not
`mi`/`raw`/`hal`. So "parity with radon" is precisely **per-function cyclomatic complexity
for JS/TS**, emitted as raw output for the agent to read — *not* maintainability-index or
Halstead metrics. This keeps s4 the same shape as radon and avoids scope creep.

## Tool selection (the key decision — resolved in s4-t0 as an ADR)

Choosing the JS complexity tool is a stack/tooling decision (SDLC rule #11/#15 hard-stop);
it is recorded in **ADR-0022** (s4-t0). Pins are currently silent on a JS complexity tool.
Three candidates, with the plan's recommendation:

1. **(Recommended) Reuse the vendored ESLint `complexity` core rule** via a dedicated,
   adapter-supplied flat config (the depcruiser pattern: the adapter ships its own config
   so the host project needs none). ESLint's `complexity` rule computes per-function
   cyclomatic complexity; configured at threshold `0` it reports **every** function with
   its complexity number — exact `radon cc` parity. **Zero new dependency** (eslint `^9` is
   already pinned, provisioned, and CI-matrix-tested on Node 20+22), strongest possible
   architecture-validation, no new license/maintenance surface. Exposed as a **distinct
   analyzer id** (e.g. `jscomplexity`) so it is not conflated with the lint adapter.
2. **`eslintcc`** — wraps ESLint complexity rules, emits per-function A–F ranks as JSON
   (closest visual parity to radon's ranks). Cost: a new npm dependency that pins its own
   ESLint, risking divergence from our vendored `eslint@^9`.
3. **`ts-complex`** — cyclomatic + Halstead + maintainability-index via the TS compiler
   (richer than radon). Cost: new dependency, smaller/less-maintained, and richer than the
   parity target requires.

If the operator picks (2) or (3) instead of (1), s4-t1 additionally adds the `package.json`
+ `package-lock.json` pin and a `stack-pins.md` row (ADR-0017); the rest of the plan is
unchanged. The story spec below is written against the recommended option (1).

## Scope

1. **ADR-0022** recording the tool choice, the `cc`-parity scope, and the **JS cohesion
   limitation** (see below). (s4-t0)
2. **New analyzer** (recommended: `jscomplexity`) — a thin-runner adapter that invokes the
   vendored ESLint with an adapter-supplied complexity-only flat config and the vendored
   SARIF formatter, capturing raw output (ADR-0020). Wired into `REGISTRY`, `_JS_ADAPTERS`,
   and `capabilities.json` (`domain=maintainability`, `subcategory=complexity`, `tier=quick`,
   `languages=[javascript, typescript]`). Tests: invocation-contract + integration.
   **SKILL.md docs land in the same task** (reading-guide row + capabilities row + cohesion
   limitation) — the `test_every_analyzer_documented` guard ties REGISTRY membership to the
   SKILL.md table, so code and docs must commit together to keep the suite green. (s4-t1)

## JS cohesion — documented limitation, not built (G8 second half)

Python has `cohesion` (LCOM4). There is **no maintained, thin, JSON-emitting JS/TS cohesion
tool** that fits the vendored-npm + raw-capture model. Per G8, JS cohesion is **declared a
known limitation** (documented in ADR-0022 and SKILL.md), not implemented. This is a
deliberate scope boundary, not an omission.

## Out of scope

- Maintainability-index / Halstead / raw-LOC metrics for JS (radon parity is `cc` only).
- JS/TS cohesion (LCOM) — documented limitation per above.
- Any change to the Python `radon` adapter or the existing JS adapters.
- Re-opening the review-selection scheme (ADR-0011); the new analyzer slots into the
  existing `maintainability/complexity` subcategory with no scheme change.

## Acceptance criteria

- ADR-0022 exists recording: the chosen tool + rationale, the `cc`-parity scope, and the JS
  cohesion limitation. Cross-referenced from the epic and SKILL.md.
- A new analyzer is registered in `REGISTRY`, `_JS_ADAPTERS`, and `capabilities.json` with
  `domain=maintainability`, `subcategory=complexity`, `tier=quick`,
  `languages=[javascript, typescript]`, `rule_classes=[complexity]`.
- The adapter follows the thin-runner contract: invoke + raw capture, ADR-0019
  `unavailable`-vs-`error` mapping (missing node/binary → unavailable; no JS files →
  unavailable; no targets → unavailable), no output parsing.
- Integration test: provisioned `node_modules` + a JS **and** TS fixture → `status=="ok"`
  and per-function complexity present in the captured output for both languages.
- `test_capabilities.py` locked-taxonomy table updated to include the new analyzer; all
  capability/registry consistency tests pass.
- `select_adapters({"javascript"})` and `{"typescript"}` include the new analyzer; a
  pure-Python selection does not.
- SKILL.md per-tool reading-guide row + capabilities table row added; JS cohesion limitation
  documented.
- If a new npm tool was chosen: `package.json` + `package-lock.json` pinned and
  `stack-pins.md` Node/JS table row added (ADR-0017), reconciled in the same commit.
- `uv run pytest` (+ integration), `uv run ruff check .`, `uv run mypy code_review` clean.

## Task sequence

- **s4-t0** — ADR-0022: JS complexity tool selection + cc-parity scope + cohesion limitation
  (no code; resolves the hard-stop).
- **s4-t1** — implement the analyzer adapter + registry/lang_select/capabilities wiring +
  SKILL.md docs + tests (test-first; the substantive work). Docs are in-task because the
  `test_every_analyzer_documented` guard couples REGISTRY membership to the SKILL.md table.

## Source

Compiled 2026-05-31 from `epic-analyzer-thin-runner.md` (s4 candidate-story description, G8;
"near-trivial" validation criterion) and the analyzer wiring read during planning
(`lang_select.py`, `selector.py`, `capabilities.json`, `adapters/{radon,eslint,depcruiser}.py`,
`test_capabilities.py` locked taxonomy table).
