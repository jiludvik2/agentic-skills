---
id: s0-t1-vendor-and-provision-ruleset
kind: task
project: code-review
status: done
parent: s0-semgrep-rule-source
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-29
updated: 2026-05-29
closed: 2026-05-29
verify: PASS — 17/17 tests; provisioning idempotent + cache_root-anchored; no drift from ADR-0016. Vendored rules validated via live semgrep (both planted defects fire).
review: MINOR-ONLY — 3 Minor + 2 Nit, no Critical/Important. Applied in-place: warn on missing vendored source; corrected stale `_provision_semgrep_rules()` comment ref; documented flat-layout glob assumption. Nits (public/private naming, read-to-compare) dropped. Also updated the stale "Semgrep rule packs in s3" notes in prefetch_caches.py docstring + setup.sh:88 (ADR-0016-assigned to s0-t1).
tags: [semgrep, setup, prefetch, rules]
---

# s0-t1 — Vendor the ruleset & provision it via setup.sh

## Outcome

The curated semgrep ruleset (per s0-t0's ADR) lives in the skill bundle, and a
clean `./scripts/setup.sh` installs it into `cache_root()/cache/semgrep/rules/`
idempotently. Depends on s0-t0.

## Acceptance criteria

### Scenario: ruleset vendored in the bundle
- **Given** the repo after this task
- **Then** `.claude/skills/code-review/semgrep-rules/` contains the curated
  rule file(s), pinned/sourced per the ADR.

### Scenario: setup.sh provisions the runtime cache
- **Given** a clean checkout (no `cache/semgrep/rules`)
- **When** `./scripts/setup.sh` runs
- **Then** `cache_root()/cache/semgrep/rules/` contains the ruleset, and the
  prefetch manifest records it.

### Scenario: idempotent
- **Given** the cache already provisioned
- **When** `setup.sh` (or `prefetch_caches.py`) runs again
- **Then** it no-ops (no error, no needless rewrite), consistent with the
  existing `prefetch_caches.py` manifest contract.

## Test specification

Write first, confirm red, then implement:

1. `test_prefetch_provisions_semgrep_rules`: point `$POLYREVIEW_CACHE_DIR` at a
   `tmp_path`, run the provisioning entrypoint, assert
   `<tmp>/cache/semgrep/rules/` exists and contains ≥1 `.yaml` rule file.
2. `test_prefetch_semgrep_rules_idempotent`: run provisioning twice against the
   same `tmp_path`; assert the second run reports up-to-date / does not raise and
   the rule files are unchanged.
3. Extend the existing `prefetch_caches.py` manifest test (if any) to cover the
   new artifact entry without breaking the empty-manifest idempotence contract.
