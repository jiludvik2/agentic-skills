---
id: epic-analyzer-correctness
kind: epic
project: code-review
status: done
children:
  - s1-eslint-legacy-config-unavailable
  - s2-adapter-output-capture-audit
sources: [dogfood-2026-06-01-analyzer-defects.md, fu-gitleaks-json-output-capture.md]
created: 2026-06-01
updated: 2026-06-01
note: |
  s0-jscomplexity-complexity-threshold WITHDRAWN 2026-06-01 (not a defect — intended
  radon-cc-parity design per ADR-0022). Ids s1/s2 kept stable rather than renumbered;
  the gap at s0 is intentional. The withdrawn story file is retained as a record.
tags: [analyzer, adapters, correctness, dogfooding, post-ga]
---

# Epic — analyzer output correctness (dogfooding defects)

## Close notes (2026-06-01)

**CLOSED.** Both stories done; commits `3388327..19a7073` pushed to `origin/main`.

- **s1** — eslint legacy-only `.eslintrc*` → `unavailable` (was a spurious exit-2 `error`;
  vendored ESLint v9 is flat-config-only). `_discover_eslint_config` → flat|legacy|none.
- **s2** — gitleaks now writes an off-argv JSON report read back onto stdout (was a
  stderr-banner-only silent false-negative); audited all 13 adapters (every one lands
  findings in `outputs[].stdout`, gitleaks was the sole defect, no sibling); added a CI
  regression guard (`tests/test_analyzer_output_capture_coverage.py`) and the
  `output-capture-audit.md` artefact; closed the jscomplexity QA-harness coverage gap.

All tasks: Verifier PASS, reviewer CLEAN/MINOR-ONLY (Minors remediated). FINDINGS F15
RESOLVED. **Document:** README unchanged — fixes align behaviour with the already-documented
available/unavailable model. **No QA artefacts pending relocation** — the QA docs live in
`sdlc/docs/qa/` already. **Release tag:** none cut (operator deferred); a `code-review-v0.1.1`
patch on GA 0.1.0 remains available if wanted.


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

## Withdrawn

- **s0 — jscomplexity complexity threshold (WITHDRAWN 2026-06-01).** The threshold-0
  "flags every function" behaviour is intended radon-cc-parity design (ADR-0022,
  `jscomplexity.py:13-24`), not a defect. Filed from a dogfooding run before the
  adapter source was read; retracted on review. Story file retained as a record.

## Sequencing

Independent defects — any order. **s1** is a small single-adapter fix; **s2** is
larger (one adapter fix + a cross-adapter audit). Tasks (planned 2026-06-01): s1-t0;
s2-t0, s2-t1.

## Source

Compiled from the 2026-06-01 dogfooding test-drives
(`dogfood-2026-06-01-analyzer-defects.md`) and the parked
`fu-gitleaks-json-output-capture.md` follow-up (now absorbed into s2).
