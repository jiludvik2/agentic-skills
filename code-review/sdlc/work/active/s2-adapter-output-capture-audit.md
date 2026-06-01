---
id: s2-adapter-output-capture-audit
kind: story
project: code-review
status: active
parent: epic-analyzer-correctness
children:
  - s2-t0-gitleaks-json-report
  - s2-t1-output-capture-audit
sources: [dogfood-2026-06-01-analyzer-defects.md, fu-gitleaks-json-output-capture.md]
created: 2026-06-01
updated: 2026-06-01
tags: [analyzer, gitleaks, output-capture, security, false-negative, audit]
---

# Story — adapter output-capture audit (gitleaks false-negative + siblings)

Absorbs and supersedes `fu-gitleaks-json-output-capture` (parked follow-up, promoted
to a story under epic-analyzer-correctness). See that file for the original analysis.

## Discovered

2026-06-01 dogfooding confirmed the parked gitleaks issue on **real repos**, not just
a planted fixture: gitleaks found **10 real leaks on pygoat** and **3 on NodeGoat**,
but in every case captured **stdout was empty** (exit 1, findings printed to stderr in
banner form). A bundle consumer — the LLM agent the thin runner serves — sees empty
stdout and concludes "no secrets." Silent false-negative in a security analyzer.

## Problem

Two layers:

1. **gitleaks specifically.** The adapter invokes `gitleaks detect --source <target>
   --no-git` with no JSON report path, so findings go to stderr and stdout is empty.
   The fix must respect the `/dev/stdout`-not-writable-under-sandbox constraint
   (memory `code-review-dev-stdout-not-writable-under-sandbox`): write JSON to a real
   temp file and read it back (the trivy/jscpd pattern), not a `/dev/stdout` redirect.

2. **The class of bug.** Under raw-capture (ADR-0020), ANY adapter whose real findings
   land on stderr or in a file instead of captured `stdout` reads as zero signal. The
   old SARIF-normalizing facade may have masked siblings. The QA harness only checks
   "≥1 signal," so it cannot catch a uniformly-silent adapter.

## Acceptance criteria

- **gitleaks:** findings captured as machine-readable JSON in bundle `outputs[].stdout`
  (off-argv report path, sandbox-safe); the QA `gitleaks` case moves from xfail to a
  real pass; `count_gitleaks` asserts ≥1 against real output.
- **Audit:** every deterministic adapter is checked that its genuine findings land in
  `outputs[].stdout` (not stderr / not an unread file). Produce a short audit table
  (adapter → where findings go → captured? → action). Any sibling defect is filed as
  its own task under this story (or fixed inline if trivial).
- A regression guard so a uniformly-silent security adapter can't pass: for gitleaks
  (and any sibling found), an integration assertion on real output ≥1 finding against
  a known-positive fixture.

## Test specification (defined before implementation)

- RED: integration test — gitleaks against a fixture containing a known secret asserts
  ≥1 finding parsed from captured `stdout`. Today fails (stdout empty; currently xfail
  in run_smoke.py KNOWN_DEFERRED).
- Unit: gitleaks adapter constructs an off-argv JSON report path and reads it back
  (assert the argv shape + the read-back, sandbox-safe — no `/dev/stdout`).
- Audit deliverable: a checked-in table/test enumerating each adapter's output channel
  and asserting capture; siblings get their own RED test before fix.

## Notes

- Larger than s0/s1: one concrete adapter fix (gitleaks) + a cross-adapter audit that
  may spawn fix tasks. Plan may split into t0 (gitleaks fix) + t1 (audit + sibling
  fixes).
- Related history: FINDINGS.md F2 (jscpd `/dev/stdout` mkdir) and the dev-stdout
  memory are the same bug class.
- The original `fu-gitleaks-json-output-capture.md` is retained for provenance and
  annotated as superseded by this story.
