---
id: s1-t0-fix1-skill-md-honesty
kind: task
project: code-review
status: done
parent: s1-reviewer-skill-and-capabilities
sources: [s1-t0-reviewer]
created: 2026-05-26
updated: 2026-05-26
notes: |
  Reviewer Minors folded in opportunistically (same files): harden section-split
  anchoring in test_skill_scaffold.py (false-positive risk on bare-substring split),
  assert sandbox snippet has top-level "sandbox" key.
  Reviewer false-positive (not actioned): review-request.json review_scope "defaults
  to lite" does NOT contradict cli.py ReviewRequest.scope="standard" — different fields
  (internal analysis-scope vs operator review-depth config). Schema is forward-correct.
---

# s1-t0-fix1 — SKILL.md documentation honesty

## Outcome

SKILL.md no longer presents not-yet-built features (`--review-scope` flag, rich
`--capabilities` output, `capabilities.json` instance, `scripts/setup.sh`) as
currently working. A concise "Status" note distinguishes what s0 ships from what
lands across the rest of s1, so a reader (or the Reviewer sub-agent) is not misled
mid-story.

## Acceptance Criteria

- SKILL.md contains a "Status" section listing what is live now (s0 CLI: `--analyzer`,
  `--target`, `--diff`, `--output`, and `--capabilities` emitting the analyzer-name list)
  versus what is landing in s1 (scope selection / `--review-scope`, rich `--capabilities`
  merge, `capabilities.json`, `scripts/setup.sh`).
- No present-tense claim in SKILL.md asserts a feature works that the s0 CLI does not
  yet provide, without that feature being covered by the Status note.
- Existing s1-t0 tests remain GREEN.

## Test specification

Additions/hardening to `tests/test_skill_scaffold.py`:

- `test_skill_md_has_status_section` — assert a "Status" header is present and its text
  references both `--capabilities` and `setup.sh` (so the live-vs-planned split is documented).
- Harden `test_skill_md_has_required_sections` — anchor the "Review scopes" section slice
  to the matched header position (use the regex match end), not a bare-substring split.
- Harden `test_skill_md_sandbox_snippet_is_valid_json` — anchor to the `Sandbox configuration`
  header and assert the parsed JSON has a top-level `sandbox` key.
