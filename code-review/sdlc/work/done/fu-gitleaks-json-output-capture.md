---
id: fu-gitleaks-json-output-capture
kind: task
project: code-review
status: active
parent: epic-analyzer-thin-runner
sources: [qa-analyzer-coverage-findings.md, s5-t2-regenerate-captures-and-docs.md]
created: 2026-05-31
updated: 2026-06-01
superseded-by: s2-adapter-output-capture-audit
tags: [adapter, gitleaks, output-capture, follow-up, superseded]
---

> **Superseded 2026-06-01 by `s2-adapter-output-capture-audit`** (epic-analyzer-correctness).
> Compiled into that story after the 2026-06-01 dogfooding run confirmed the defect on
> real repos (10 real leaks missed on pygoat, 3 on NodeGoat). Retained for provenance;
> the live spec is s2. Do not plan/execute from this file.

# Follow-up — gitleaks adapter emits no JSON on stdout (output-capture audit)

## Discovered

s5-t2 (analyzer-coverage QA harness, bundle migration). The migrated harness runs
each analyzer and reads its **raw stdout** from the review bundle (ADR-0020). The
`gitleaks` case is reported as **xfail** (`KNOWN_DEFERRED` in `run_smoke.py`):
gitleaks genuinely detects the planted secret but the adapter never sees it.

## Problem

The gitleaks adapter invokes:

```
gitleaks detect --source <target> --no-git
```

with **no** `--report-format json` / report path. So:

- findings print to **stderr** in human (banner) format;
- captured **stdout is empty**;
- gitleaks exits **1** (leaks found).

A bundle consumer — the QA oracle, and more importantly the *LLM agent* the whole
thin-runner exists to serve — sees an empty stdout and concludes "no secrets",
even though gitleaks's stderr says `leaks found: 1`. This is a correctness defect
in a security analyzer: silent false-negative.

The fix is not just `--report-format json` to stdout, because of the
`/dev/stdout`-not-writable-under-sandbox constraint (see memory
`code-review-dev-stdout-not-writable-under-sandbox`): gitleaks must write its JSON
report to a real temp file and the adapter must read it back (the pattern the
trivy/jscpd adapters already use), or capture native stdout if gitleaks supports
`--report-path -` reliably across platforms.

## Scope — broader than gitleaks (the real value)

The QA harness only checks **≥1 signal**, so *any* adapter that emits to stderr or
to a file instead of captured stdout silently reads as zero under the raw-capture
model. **Audit every adapter** for output-capture correctness against the bundle:
confirm each one's real findings actually land in `outputs[].stdout`. gitleaks is
the one the harness caught; there may be siblings (the old SARIF-normalizing
facade may have masked others).

## Acceptance criteria (when this is planned into a story)

- The gitleaks adapter captures its findings as machine-readable output in the
  bundle `stdout` (JSON), not stderr; the QA `gitleaks` case moves from xfail to a
  real pass and `count_gitleaks` asserts ≥1 against real output.
- An output-capture audit covers all deterministic adapters; any sibling defects
  are filed.
- Off-argv report path respects the sandbox `/dev/stdout` constraint.

## Notes

- This is shipping-`code_review/`-adapter work (tests-first, its own Verify/Review),
  **out of scope for s5** (which is QA-harness + oracle work). It is parked here as
  a `-fu-` human-discovered follow-up; the operator decides whether it becomes its
  own story/epic post-`epic-analyzer-thin-runner`.
- Related history: FINDINGS.md F2 (jscpd `/dev/stdout` mkdir) and the
  dev-stdout-not-writable memory are the same class of bug.
