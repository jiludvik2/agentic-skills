---
id: s2-t1-output-capture-audit
kind: task
project: code-review
status: done
parent: s2-adapter-output-capture-audit
sources: [s2-adapter-output-capture-audit.md]
created: 2026-06-01
updated: 2026-06-01
tags: [analyzer, output-capture, audit, regression-guard]
---

# Task — output-capture audit across all deterministic adapters

## Outcome

Every deterministic adapter is verified to land its genuine findings in
`outputs[].stdout` (not stderr-only, not an unread file). gitleaks was the one the
QA harness caught (s2-t0); this task confirms there are no silent siblings and adds a
guard so a uniformly-silent adapter can't pass green again.

## Acceptance criteria

- An audit table (checked into the QA docs / a test docstring) enumerating every
  deterministic adapter: **tool → where it emits findings → captured into stdout? →
  action**. Covers at minimum: semgrep, bandit, gitleaks, trivy, radon, vulture,
  pydeps, cohesion, eslint, jscpd, knip, depcruiser, jscomplexity.
- For each adapter capable of producing findings, an integration assertion that a
  known-positive fixture yields ≥1 signal **in captured stdout** (the existing
  analyzer-coverage oracles cover most; fill gaps).
- Any sibling defect found (findings on stderr / in an unread file) is filed as its
  own `s2-t1-fixN-*` task (or fixed inline if a one-line argv change) — do not leave
  a known silent adapter unaddressed.
- A regression guard: the QA harness's "≥1 signal" check is tightened so it inspects
  the channel the contract promises (stdout), preventing a recurrence of the gitleaks
  class of false-negative.

## Test specification (write first, confirm RED where applicable)

- For each adapter without an existing positive-signal-in-stdout assertion, add a
  fixture + RED test, then confirm it passes after any needed adapter fix.
- The audit table is a deliverable artefact; its correctness is validated by the
  per-adapter assertions, not prose alone (avoid status==ok masking zero-signal — cf.
  memory `feedback-analyzer-integration-tests-assert-findings`).

## Implementation notes

- Depends on s2-t0 (gitleaks) landing first — it establishes the read-back pattern
  and is the first row of the audit table.
- Likely-clean adapters (already emit JSON/SARIF to stdout): semgrep, bandit, trivy,
  radon, eslint, jscpd, knip, depcruiser, jscomplexity, pydeps. Confirm, don't assume
  — the dogfooding lesson is that assumed behaviour ≠ real behaviour.
- Suspect by output style: cohesion (prints a human report to stdout — confirm the
  oracle parses real signal), vulture (text lines to stdout — confirm).
- Scope guard: this is an *audit + guard*, not a rewrite of working adapters. Fixes
  beyond a trivial argv change spawn their own fix tasks.
- Gates: `.venv/bin/pytest`, `.venv/bin/ruff check .`, `.venv/bin/mypy code_review`.
