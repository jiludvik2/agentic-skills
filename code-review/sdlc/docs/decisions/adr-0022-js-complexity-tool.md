---
id: adr-0022-js-complexity-tool
kind: decision
project: code-review
status: accepted
parent: s4-t0-adr-js-complexity-tool
sources: [s4-js-complexity-analyzer.md, epic-analyzer-thin-runner.md, g8-js-complexity-cohesion-absent.md, adr-0011-review-selection-model.md, adr-0017-node-range-and-js-toolchain-pins.md, adr-0019-analyzer-unavailable-vs-error.md, adr-0020-thin-invocation-runner.md]
created: 2026-05-31
updated: 2026-05-31
tags: [complexity, javascript, eslint, cohesion, maintainability]
---

# ADR-0022: JS complexity analyzer — tool selection (JS-only; TS deferred)

## Status

Accepted (operator-approved 2026-05-31, story s4 / G8). Co-located in `sdlc/work/active/`
while `epic-analyzer-thin-runner` is in flight; moves to `sdlc/docs/decisions/` at epic
close.

> **Amendment (2026-05-31, s4-t1 — scope narrowed to JavaScript).** During s4-t1
> validation against the real vendored toolchain, the "reuse vendored ESLint → JS **and**
> TS at zero new dependency" premise was found **false for TypeScript**: ESLint's default
> parser (espree) cannot parse `.ts` type annotations, and `.ts` is not matched by a default
> flat config. Parsing TS requires `@typescript-eslint/parser`, which is **not** vendored
> (we ship `typescript@5.9.3`, the compiler, but not the ESLint parser bridge). So TS parity
> and the zero-new-dependency property are in conflict. **Operator decision (gate
> escalation, 2026-05-31): ship `jscomplexity` JavaScript-only** (`languages=[javascript]`),
> preserving the zero-dependency rationale, and **declare TypeScript complexity a documented
> limitation** alongside JS cohesion (below). This mirrors the existing JS-scoping of jscpd.
> Adding TS complexity later is a clean follow-up: vendor `typescript-eslint` (v8, MIT,
> eslint-9/TS-5 compatible), pin it (ADR-0017 + stack-pins), and widen `capabilities`
> `languages` — no adapter rewrite. Decision 1 and the §3 selection metadata below are read
> with `languages=[javascript]` per this amendment.

## Context

The `maintainability/complexity` subcategory is **Python-only**: the `radon` adapter runs
`radon cc --json`, reporting per-function cyclomatic complexity. There is no JS/TS
equivalent (gap G8). A JS review currently gets dead-code (knip), duplication (jscpd),
coupling (depcruiser), and lint (eslint) — but no complexity signal.

Two facts narrow the decision:

1. **The parity target is `cc` only.** The radon adapter invokes *only* `cc` — not `mi`
   (maintainability index), `raw`, or `hal` (Halstead). So "parity with radon" is precisely
   **per-function cyclomatic complexity**, nothing richer. A tool that adds MI/Halstead
   exceeds the target rather than matching it.
2. **Pins were silent** on a JS complexity tool, making the choice a stack/tooling hard-stop
   (SDLC rule #11/#15) requiring an operator decision recorded here.

Candidate tools considered:

- **Vendored ESLint `complexity` core rule.** ESLint (`^9`) is already pinned (ADR-0017),
  provisioned by `setup.sh`, and CI-matrix-tested on Node 20 + 22. Its built-in `complexity`
  rule computes per-function cyclomatic complexity; at threshold `0` *every* function exceeds
  it and is reported with its computed value — exact `radon cc` parity. No new dependency.
- **`eslintcc`.** Wraps ESLint complexity rules and emits per-function A–F ranks as JSON
  (closest visual parity to radon's ranks). But it is a new npm dependency that pins *its
  own* ESLint, risking divergence from our vendored `eslint@^9` and a second ESLint in the
  tree.
- **`ts-complex`.** Cyclomatic + Halstead + maintainability-index via the TS compiler —
  richer than radon. A new, smaller/less-maintained dependency, and richer than the parity
  target requires.

## Decision

1. **Reuse the vendored ESLint `complexity` core rule.** The new analyzer invokes the
   already-vendored ESLint with an **adapter-supplied complexity-only flat config** (the
   depcruiser pattern — the adapter ships its own config so the host project needs none) and
   the vendored `@microsoft/eslint-formatter-sarif` formatter, capturing raw SARIF (ADR-0020,
   no parsing). The complexity threshold is set to **`0`**: ESLint's `complexity` rule
   normally flags only functions *above* its limit, but at `0` every function exceeds it and
   is reported with its computed cyclomatic value — turning a violations rule into a
   full-coverage metric that matches radon's `cc` output. The host project's own ESLint
   config is **not** merged (config-lookup suppressed) so the complexity report is
   deterministic and independent of the reviewed project's lint setup.

   **ADR-0019 interaction.** Because this adapter supplies its own config, the `eslint` lint
   adapter's "no flat config discoverable → `unavailable`" path (ADR-0019) **does not apply**
   to `jscomplexity` — a complexity scan never lacks a config. The only `unavailable` triggers
   are the language/provisioning ones (missing node/binary, no target paths, no JS/TS files);
   the precise mapping is specified and tested in s4-t1.

   Chosen over `eslintcc`/`ts-complex` because: **zero new dependency** (no new license,
   maintenance, or Node-compat surface; no second ESLint), it is exact parity rather than
   excess (radon runs only `cc`), and it is the strongest possible validation of the
   thin-runner architecture's "near-trivial to add an analyzer" criterion (G8).

2. **Distinct analyzer id: `jscomplexity`.** Exposed as its own analyzer — separate from the
   `eslint` lint adapter — so the lint and complexity signals are independently selectable
   (`--review`) and independently interpretable in the bundle. Same vendored binary, two
   analyzers, two configs.

3. **Selection-scheme placement (no scheme change).** `jscomplexity` slots into the existing
   ADR-0011 scheme under `domain=maintainability`, `subcategory=complexity`, `tier=quick`,
   `languages=[javascript]` (per the s4-t1 amendment above), `rule_classes=[complexity]` —
   mirroring how `knip` (JS dead-code) mirrors `vulture` (Python dead-code). `--review
   complexity` and `--review maintainability` then cover both language families (Python via
   radon, JS via jscomplexity), with diff-language filtering selecting
   the right one.

4. **No new pin.** Because the analyzer reuses vendored ESLint, `package.json` /
   `package-lock.json` / `stack-pins.md` are unchanged. The adapter-supplied flat config is
   hand-authored, MIT (same provenance policy as the depcruiser config and the semgrep
   ruleset).

## Declared limitations, not implemented

Two scope boundaries, documented in SKILL.md and here — explicitly boundaries, not
oversights:

- **JS/TS cohesion (LCOM).** Python has `cohesion` (LCOM4). There is no maintained, thin,
  JSON-emitting JS/TS cohesion tool that fits the vendored-npm + raw-capture model. Not
  implemented for any JS/TS.
- **TypeScript complexity.** `jscomplexity` is JavaScript-only (see the s4-t1 amendment
  above): TS parsing needs `@typescript-eslint/parser`, which is not vendored, and adding it
  would forfeit the zero-new-dependency rationale. TS cyclomatic complexity is therefore not
  provided. Adding it later = vendor `typescript-eslint` + widen `capabilities`, no rewrite.

Revisit either if a suitable tool/decision emerges (a future ADR/story).

## Consequences

- A JavaScript review gains a complexity signal at parity with Python's, with no new
  dependency — the cheapest possible closure of G8's JS half and a clean second proof of the
  thin-runner design. (TypeScript complexity is deferred — see the limitations above.)
- The `complexity` signal for JS is cyclomatic-only; maintainability-index and Halstead are
  out of scope (radon parity). If richer JS metrics are wanted later, that is a new decision
  (reconsider `ts-complex`), not a regression here.
- The adapter depends on ESLint's `complexity` rule remaining a core rule and on the v9
  flat-config invocation shape; both are pinned by ADR-0017's ESLint pin, which is the
  version guard. The s4-t1 integration test exercises the real vendored binary so a future
  ESLint major that changes the rule or config surface fails loudly.
- JS cohesion stays a documented gap until a suitable tool exists.
