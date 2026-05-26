---
id: s1-t1-capabilities-json-content
kind: task
project: code-review
status: active
parent: s1-reviewer-skill-and-capabilities
created: 2026-05-26
updated: 2026-05-26
---

# s1-t1 — capabilities.json content

## Outcome

`.claude/skills/code-review/capabilities.json` declares the skill's review kinds, stack coverage, analyzer registry, and taxonomies, and validates against `schemas/capabilities.json`. Values reflect what the test suite verifies, not aspirational coverage.

## Acceptance Criteria

- `review_kinds` array includes at minimum `per-task`, `story-level`, `contract-verification`, each with `id`, `description`, `scope` (one of `diff`, `cumulative-diff`, `story-level-only`), and `expected_duration_s` range.
- `stack_coverage` lists Python (with `version_range`, frameworks including `fastapi` and `django` with version ranges, and `analyzer_classes`) and TypeScript (frameworks `next`, `react`, `vite` with version ranges).
- `analyzers` array contains one entry per s0-registered analyzer (`semgrep`, `radon`), each with `id`, `kind`, `languages`, `rule_classes`, `taxonomies_tagged`, `default_timeout_s`, and optional `scope_restriction`.
- `taxonomies` lists CWE (with version), OWASP Top 10 (with version), and the SDLC severity taxonomy (with values `critical`, `important`, `minor`, `nit`).
- The document validates against `schemas/capabilities.json`.
- Each `stack_coverage` framework entry has at least one corresponding fixture directory under `tests/fixtures/` (coverage discipline). Frameworks without a fixture yet are omitted or marked, not listed aspirationally.

## Test specification

New `tests/test_capabilities.py`:

- `test_capabilities_validates_against_schema` — load `capabilities.json` and `schemas/capabilities.json`; `jsonschema.validate`; assert no error.
- `test_capabilities_has_required_sections` — assert keys `review_kinds`, `stack_coverage`, `analyzers`, `taxonomies` present.
- `test_review_kinds_minimum_set` — assert `per-task`, `story-level`, `contract-verification` ids present, each with required fields.
- `test_analyzers_match_s0_registry` — assert `semgrep` and `radon` entries present with all required fields; assert every analyzer id is a key in `code_review.adapters.REGISTRY`.
- `test_taxonomies_include_sdlc_severity` — assert SDLC severity taxonomy lists exactly `critical`, `important`, `minor`, `nit`.
- `test_stack_coverage_frameworks_have_fixtures` — for each framework listed under `stack_coverage`, assert a matching directory exists under `tests/fixtures/` (coverage discipline). For s1 the only verified fixture is `python-with-known-issues`; the test enforces that any listed framework is backed by a fixture.

## Notes / deferrals

- TypeScript fixtures don't exist yet (TS analyzers land in s3). The coverage-discipline test means TS frameworks listed in `stack_coverage` must either have a placeholder fixture or be represented as declared-but-unverified; resolve during execution by listing only Python as verified and TS as `status: planned`, keeping the test green.
