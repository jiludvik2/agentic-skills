---
id: epic-analyzer-correctness
kind: epic
project: code-review
status: active
children:
  - s0-jscomplexity-complexity-threshold
  - s1-eslint-legacy-config-unavailable
  - s2-adapter-output-capture-audit
sources: [dogfood-2026-06-01-analyzer-defects.md, fu-gitleaks-json-output-capture.md]
created: 2026-06-01
updated: 2026-06-01
tags: [analyzer, adapters, correctness, dogfooding, post-ga]
---

# Epic — analyzer output correctness (dogfooding defects)

Post-GA correctness hardening of the shipped (0.1.0) analyzer layer. Three defects
surfaced by running polyreview against real public repos on 2026-06-01 (pygoat,
NodeGoat, requests/flask/scrapy, express/mocha/chalk/axios/webpack). Each is an
adapter producing **wrong signal** under the thin-runner raw-capture contract
(ADR-0020): noise that buries findings, a spurious error where a clean skip is
correct, or a silent false-negative.

## Why

The thin runner's value is that an agent reads each tool's raw output and trusts it.
That trust breaks when an adapter (a) floods the bundle with zero-value findings,
(b) reports `error` for a benign condition, or (c) captures nothing while the tool
actually found something. The dogfooding run hit all three on real repos — the kind
of defect unit tests miss because fixtures are too clean (cf. memory
`harness-needs-real-run-before-close`).

## Stories

- **s0 — jscomplexity complexity threshold.** jscomplexity (s4, ADR-0022) reuses
  ESLint's `complexity` rule with an effective threshold of 0, so every function is
  flagged "complexity of N, maximum allowed is 0" (1259 findings on NodeGoat). Set a
  sane default threshold (radon-cc parity) or report the metric without a 0 gate, so
  output carries signal not noise.
- **s1 — eslint legacy-config → unavailable.** The eslint adapter's availability
  check accepts legacy `.eslintrc*`, but the vendored ESLint v9.39.4 is
  flat-config-only and exits 2 on a legacy-only target (express) → reported as
  `error`. A legacy-only target should map to `unavailable` (ADR-0019), not pollute
  a review with a spurious red.
- **s2 — adapter output-capture audit.** gitleaks emits findings to stderr; captured
  stdout is empty → silent false-negative in a security analyzer (10 real leaks
  missed on pygoat). Fix gitleaks (off-argv JSON report path per the sandbox
  `/dev/stdout` constraint) AND audit every deterministic adapter that its real
  findings actually land in `outputs[].stdout`. Absorbs `fu-gitleaks-json-output-capture`.

## Out of scope (observations, not defects — see source)

JS cohesion analyzer absence (documented limitation, ADR-0022); TS complexity
(documented limitation); semgrep sandbox exit-2 (environment gotcha); pydeps
third-party-following + pkg self-cycles (precision enhancement); cohesion 0% for
exception/ABC classes (SKILL.md interpretation guidance); per-tool output formats
(by-design, ADR-0020). These may be promoted later but are not correctness defects.

## Sequencing

Independent defects — any order. s0 and s1 are small single-adapter fixes; s2 is
larger (one adapter fix + a cross-adapter audit). Tasks defined at Plan time.

## Source

Compiled from the 2026-06-01 dogfooding test-drives
(`dogfood-2026-06-01-analyzer-defects.md`) and the parked
`fu-gitleaks-json-output-capture.md` follow-up (now absorbed into s2).
