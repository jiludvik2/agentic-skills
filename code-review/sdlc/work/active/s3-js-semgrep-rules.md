---
id: s3-js-semgrep-rules
kind: story
project: code-review
status: active
parent: epic-analyzer-thin-runner
children:
  - s3-t0-js-rules-fixture-test
  - s3-t1-docs
sources: [epic-analyzer-thin-runner.md, adr-0016-semgrep-rule-provenance.md]
created: 2026-05-31
updated: 2026-05-31
tags: [semgrep, javascript, typescript, security, rules, vendored]
---

# Story s3 — G6: vendor JS/TS semgrep rules

## Why

The vendored semgrep ruleset (`security.yaml`) covers Python only. JS/TS security scanning has
been a tracked follow-up since ADR-0016 was amended 2026-05-30 to defer it from s0. This story
closes that gap.

This is also the architecture's first validation: the epic states that adding a JS ruleset must
be "near-trivial on the new design — if it's hard, the architecture is wrong." The thin-runner
design (ADR-0020) means no adapter changes are needed — only extend the vendored rules, create a
fixture, add a test.

## Scope

1. **JS/TS security rules** (`security-js.yaml` in the skill bundle) — a minimal, deterministic
   set of JS/TS patterns (eval, innerHTML XSS) vendored under
   `.claude/skills/code-review/semgrep-rules/`. The provisioning path already globs `*.y*ml` —
   no plumbing changes needed.
2. **Fixture** — `tests/fixtures/js-with-security-issues/vuln.js` with planted JS defects that
   the new rules must fire on. A separate fixture from the existing `js-with-known-issues/`
   (which plants knip/eslint issues, not security issues).
3. **Integration test** — asserts the vendored JS rules fire end-to-end through the adapter.
4. **Documentation** — SKILL.md semgrep row updated to note Python + JS/TS coverage; ADR-0016
   amended to close the JS/TS follow-up.

## Out of scope

- Extending the smoke-test QA fixture (`sdlc/docs/qa/analyzer-coverage/semgrep-rules/`) — that
  is a separate harness (s5 concern). Only the unit/integration test fixtures are in scope.
- React-specific patterns (`dangerouslySetInnerHTML`) — deferred; require more complex semgrep
  pattern syntax and a React fixture. Keep s3 to the simplest deterministic rules first.
- Any adapter code change — the architecture validation criterion is that none is needed.

## Acceptance criteria

- A new `security-js.yaml` exists in `.claude/skills/code-review/semgrep-rules/` with at least
  two JS/TS security rules (eval, innerHTML).
- `tests/fixtures/js-with-security-issues/vuln.js` exists with planted defects matching those
  rules.
- The integration test in `test_semgrep.py` asserts that running the adapter against the JS
  fixture with a provisioned cache yields `status == "ok"` and SARIF results containing the
  expected JS rule IDs.
- `test_prefetch_semgrep_rules.py` still passes without modification (provisiong globs
  dynamically; the new file is auto-covered).
- No adapter code was modified (architecture validation: extension is additive only).
- SKILL.md semgrep row notes Python + JS/TS; ADR-0016 records the follow-up as delivered.
- `uv run pytest` (+ integration), `uv run ruff check .`, `uv run mypy code_review` clean.

## Task sequence

- **s3-t0** — JS/TS rules + fixture + integration test (test-first; the substantive work).
- **s3-t1** — documentation: SKILL.md update + ADR-0016 amendment.

## Source

Compiled 2026-05-31 from `epic-analyzer-thin-runner.md` (s3 candidate-story description,
"near-trivial" validation criterion) and `adr-0016-semgrep-rule-provenance.md` (JS/TS
follow-up tracking; provisioning path already in place).
