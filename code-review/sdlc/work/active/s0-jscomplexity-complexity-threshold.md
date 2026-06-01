---
id: s0-jscomplexity-complexity-threshold
kind: story
project: code-review
status: active
parent: epic-analyzer-correctness
sources: [dogfood-2026-06-01-analyzer-defects.md, adr-0022-js-complexity-tool.md]
created: 2026-06-01
updated: 2026-06-01
tags: [analyzer, jscomplexity, eslint, noise, s4-regression]
---

# Story — jscomplexity flags every function (threshold 0)

## Discovered

2026-06-01 dogfooding. jscomplexity run on real JS repos returns one finding **per
function in the codebase**, each reading:

> Function has a complexity of N. Maximum allowed is 0.

Counts: NodeGoat 1259, mocha 732, express 109, chalk 45. A complexity-1 trivial
function is flagged identically to a complexity-21 hotspot. The output is pure
noise — an agent reading the bundle cannot distinguish signal.

## Problem

jscomplexity (shipped in s4, ADR-0022) reuses the vendored ESLint `complexity` rule
to get radon-`cc` parity for JS. The rule is being configured with an effective
**maximum of 0**, so ESLint emits a violation for every function (complexity ≥ 1 > 0).
The intent (per ADR-0022) was a complexity *metric* comparable to radon's per-function
cyclomatic complexity, not a lint gate that fails everything.

Root cause to confirm in t0: where the `complexity` rule's threshold is set (the
adapter's inline ESLint config / rule options) and why it resolves to 0.

## Acceptance criteria

- jscomplexity reports **signal, not every function**. Either: (a) the `complexity`
  rule uses a sane threshold (e.g. radon's default sensitivity) so only genuinely
  complex functions are flagged; or (b) it emits the per-function complexity *metric*
  (parity with radon `cc`) without a 0-gate that flags everything. Decide in t0 and
  record the choice (ADR amendment if it changes ADR-0022's stated behaviour).
- On a known fixture with a mix of trivial and complex functions, the finding count
  is proportional to genuinely-complex functions, not total function count.
- A regression test asserts that a file of trivial (complexity-1) functions produces
  **zero** (or metric-only) findings — the exact inversion of today's behaviour.
- radon-cc parity claim from ADR-0022 is re-validated or the ADR is amended.

## Test specification (defined before implementation)

- RED: a fixture `jscomplexity-threshold/` with ~3 trivial functions and 1 high-CC
  function; assert the adapter's raw output flags only the high-CC function (or emits
  metrics for all without a max-0 violation). Today this fails (all 4 flagged).
- Unit: the adapter constructs its ESLint `complexity` rule config with the intended
  threshold (assert the constructed argv/config, not a live run).
- Integration via the analyzer-coverage QA harness: the existing jscomplexity case's
  oracle asserts the corrected finding shape.

## Notes

- Small, single-adapter fix. The fix is in the jscomplexity adapter's ESLint
  invocation/config, not in the consumer.
- Confirmed across 4 real repos — this is a shipped-GA regression, high confidence.
