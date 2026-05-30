---
id: s0-semgrep-rule-source
kind: story
project: code-review
status: done
parent: epic-analyzer-ga-hardening
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-29
updated: 2026-05-29
tags: [semgrep, security, setup, ga-readiness]
notes: |
  Closed 2026-05-29. Tasks: s0-t0 (ADR-0016, 09c6154), s0-t1 (vendor+provision,
  9a5bab1), s0-t2 (adapter cache_root/fail-loud/config wiring, 37c83ac), s0-t3
  (clean-setup e2e + de-hack smoke + resolve F3, 7f207e0). Resolves FINDINGS F3.

  Story-level Review: MINOR-ONLY (no Critical/Important). Deferred Minors for
  opportunistic cleanup:
  - [DEFER] `--capabilities` reports semgrep available on binary presence only;
    it doesn't check the rules cache, so capabilities can say available while a
    security run errors "rules not found". Mitigated by the adapter's loud
    runtime error. Consider having the semgrep probe also assert the rules dir.
  - [DEFER] provision_semgrep_rules copies but never prunes — a renamed/removed
    vendored rule leaves a stale copy in cache/semgrep/rules. Low risk at one
    rule file; mirror-sync or document the additive cache + manual-clear-on-rename.
  - [DEFER] no test for the producer's missing-source warning branch
    (prefetch_caches.py returns 0 with a stderr warning); consumer error
    branches are covered, producer degraded path is not.
  - [NIT] _bundled_semgrep_rules docstring says it "copies"; it only locates.

  **OPERATOR DECISION (resolved 2026-05-30):** ADR-0016 §Decision #2 said
  "Security rules for Python AND JS/TS" but the vendored security.yaml ships
  Python-only. Operator chose to **amend ADR-0016 #2 to "Python-first; JS/TS a
  tracked follow-up"** (rather than author JS/TS rules now). Amendment note added
  to the ADR; s0 stays closed on the proven Python coverage.
---

# s0 — Semgrep rule source

## Summary

On a fresh install, the semgrep analyzer produces **zero** findings — it errors
out. Two compounding defects (FINDINGS.md F3):

1. **`setup.sh`'s prefetch ships 0 semgrep rules.** `cache/semgrep/rules` is
   never populated, so the adapter never takes its intended
   `--config <local-dir>` path.
2. **The `auto` fallback is self-contradictory.** With no local cache the adapter
   runs `--config auto` *and* `--metrics off`; semgrep refuses the combination:
   `Cannot create auto config when metrics are off`. So the fallback always
   errors.

The adapter's local-rules logic is correct — the smoke test proves semgrep finds
the planted `eval`/`shell=True` defects once `cache/semgrep/rules` holds a
ruleset. The gap is provisioning + the broken fallback.

Also: `--x-ignore-semgrepignore-files` is not a recognized flag in the installed
semgrep (warning only, currently non-fatal) and should be dropped or
version-guarded.

## Use case

- **As a** host operator who ran `setup.sh`
- **I want** `polyreview --review security` to actually return semgrep findings
- **so that** advertised security scanning isn't silently empty.

## Acceptance criteria

### Scenario: setup.sh provisions a working ruleset
- **Given** a clean checkout
- **When** `./scripts/setup.sh` runs
- **Then** `cache/semgrep/rules/` is populated with a pinned ruleset (vendored or
  prefetched), and `polyreview --capabilities` reports semgrep `available`.

### Scenario: security review surfaces findings on a fresh install
- **Given** setup.sh has run and no manual rule provisioning was done
- **When** the analyzer-coverage smoke test's semgrep case runs
- **Then** semgrep returns ≥1 finding on `fixtures/python/sec_vuln.py` (the
  harness no longer needs to copy `semgrep-rules/` into the cache).

### Scenario: the auto fallback no longer silently errors
- **Given** no local rule cache exists
- **When** the semgrep adapter runs
- **Then** it either (a) runs successfully (the `--metrics off` / `--config auto`
  conflict resolved), or (b) returns an `error` status with an actionable
  message naming the missing rule cache — never a silent empty success.

### Scenario: no unsupported flags
- **Given** the installed semgrep version
- **When** the adapter builds its command
- **Then** it passes no flag the installed semgrep rejects (drop or
  version-guard `--x-ignore-semgrepignore-files`).

## Task plan

1. **s0-t0** — ADR: semgrep rule provenance & resolution (decision; operator-approved).
2. **s0-t1** — vendor the curated ruleset in the bundle; `setup.sh` provisions
   `cache/semgrep/rules` idempotently. (← t0)
3. **s0-t2** — adapter: resolve rules via `cache_root()`, fail loudly instead of
   `auto`+`--metrics off`, drop the unsupported `--x-` flag. (← t0)
4. **s0-t3** — end-to-end: semgrep green from a clean `setup.sh`; align the QA
   smoke harness; document provisioning; mark FINDINGS F3 resolved. (← t1, t2)

## Notes

- Rule provenance (vendored-in-bundle vs prefetched-at-setup) is decided in t0's
  ADR — it sets a maintenance commitment for rule updates. Recommended: vendored.
- The adapter already reads `config["semgrep_rules"]` (exercised by the
  integration test) but `load_config` never populates it — t0 decides whether to
  wire it through `code-review.toml`; t2 implements if so.
