---
id: s0-t0-adr-semgrep-rule-provenance
kind: task
project: code-review
status: active
parent: s0-semgrep-rule-source
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md]
created: 2026-05-29
updated: 2026-05-29
tags: [semgrep, adr, decision]
---

# s0-t0 — ADR: semgrep rule provenance & resolution

## Outcome

An ADR (co-located `adr-00NN-semgrep-rule-provenance.md` in `work/active/`,
moved to `docs/decisions/` at epic close) that records, with rationale, how the
semgrep analyzer obtains its rules and how the adapter resolves them.

## Decisions to record (recommended values — operator confirms via plan approval)

1. **Provenance — DECIDED (operator, 2026-05-29): vendored-in-bundle.** Vendor a
   curated security ruleset *inside the skill bundle*
   (`.claude/skills/code-review/semgrep-rules/`), copied into
   `cache_root()/cache/semgrep/rules/` by `setup.sh`. Rationale: offline,
   deterministic, no network/login at setup, no registry-download license
   ambiguity. (Alternative considered: prefetch-download from the semgrep
   registry — rejected for network + license-review cost.)
2. **Ruleset scope & license:** security rules for python + js/ts; confirm the
   chosen rules' license fits the `stack-pins.md` floor (LGPL-2.1 OK via
   subprocess; **no AGPL**). Record the rule source and version.
3. **Resolution precedence (unchanged shape, fixed anchor):** explicit
   `semgrep_rules` config override → `cache_root()/cache/semgrep/rules` →
   missing-cache behavior (see #4). Note that the dir resolves through
   `cache_root()` (honoring `$POLYREVIEW_CACHE_DIR`), correcting today's
   `Path.cwd()`-only anchor.
4. **Missing-cache behavior:** when no rules are found, the adapter returns
   `status=error` with an actionable message ("run scripts/setup.sh") rather
   than the current broken `--config auto` + `--metrics off` combination.
5. **CLI exposure of `semgrep_rules`:** decide whether to wire the
   already-read-but-never-populated `config["semgrep_rules"]` through
   `code-review.toml` / `load_config`. (Recommended: yes, small, closes the gap
   the integration test already assumes.)

## Acceptance criteria

### Scenario: ADR exists and records the five decisions
- **Given** the repo after this task
- **When** `adr-00NN-semgrep-rule-provenance.md` is read
- **Then** it states a decision (with rationale) for each of provenance, ruleset
  scope & license, resolution precedence, missing-cache behavior, and CLI
  exposure — and supersedes/links the stale "Semgrep rule packs in s3" note in
  `stack-pins.md` / architecture.

## Test specification

Decision artefact — no automated test. Verification is a content check that all
five decisions are present and the operator has approved the ADR. (Mirrors
s1-package-publication's "Scenario: PyPI publication ADR exists".)
