---
id: s0-t3-end-to-end-green-from-clean-setup
kind: task
project: code-review
status: done
parent: s0-semgrep-rule-source
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-29
updated: 2026-05-29
tags: [semgrep, integration, qa, docs]
notes: |
  Manual smoke verification (AC scenario 2): cleared cache/semgrep, ran
  scripts/prefetch_caches.py (the setup.sh path) → "provisioned 1 semgrep rule
  file(s)"; then `cli --analyzer semgrep --target tests/fixtures/
  python-with-known-issues` with no override → status=ok, 1 finding
  (subprocess-shell-true). Clean setup.sh is sufficient.
  Review (MINOR-ONLY):
  - [APPLIED] Minor: e2e test asserted only len>=1; now also asserts the
    AC-named subprocess-shell-true ruleId fires.
  - [DEFERRED] Minor: the importlib loader for prefetch_caches.py duplicates
    _load_prefetch() in test_prefetch_semgrep_rules.py — worth hoisting to a
    shared conftest helper; opportunistic, low value, not filed as a task.
  - 1 Nit dropped.
---

# s0-t3 — End-to-end: semgrep green from a clean setup

## Outcome

Prove semgrep produces findings using only what `setup.sh` provisions (no manual
rule copying), align the analyzer-coverage smoke harness to that reality, and
document the provisioning. Depends on s0-t1 and s0-t2.

## Acceptance criteria

### Scenario: security review yields findings on a fresh setup
- **Given** `cache/semgrep/rules` provisioned by `setup.sh` (no manual override)
- **When** a `security` review runs against
  `tests/fixtures/python-with-known-issues`
- **Then** semgrep returns ≥1 finding (e.g. `subprocess-shell-true`), `status=ok`.

### Scenario: smoke harness no longer self-provisions semgrep
- **Given** the analyzer-coverage smoke test
- **When** it runs after `setup.sh`
- **Then** `run_smoke.py`'s `_provision_semgrep_rules()` is removed (or asserts
  the cache is already populated rather than copying into it), and the semgrep
  case still passes — i.e. a clean `setup.sh` is sufficient.

### Scenario: provisioning is documented
- **Given** the docs after this task
- **Then** SKILL.md (and the QA README) state that semgrep rules are provisioned
  by `setup.sh`, and FINDINGS.md F3 is marked resolved.

## Test specification

Write first, confirm red, then implement:

1. `test_semgrep_end_to_end_with_provisioned_cache` (marked `integration`, skip
   if semgrep not on PATH): provision rules into a `tmp_path` cache_root, run the
   adapter against the known-issues fixture, assert ≥1 finding and valid SARIF.
2. Update `run_smoke.py`: drop/neuter `_provision_semgrep_rules`; re-run the full
   smoke and confirm the semgrep row still passes from a clean cache (manual
   verification recorded in the close notes, since the smoke test is the
   capability harness, not a pytest case).
