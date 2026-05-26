---
id: s1-fix1-scope-wiring-and-output-parent-dir
kind: task
project: code-review
status: done
parent: s1-reviewer-skill-and-capabilities
sources: [s1-story-level-review]
created: 2026-05-26
updated: 2026-05-26
notes: |
  Story-level review MINORs not filed as fixes (captured here):
  - --capabilities output `analyzers` (status map) shares the key name with review-response
    `analyzers` (outputs map); different commands, but a schema for --capabilities output would
    disambiguate. Deferred (would add a 4th schema).
  - _SKILL_DIR = __file__.parent.parent/.claude assumes package and .claude are siblings; breaks
    for a wheel/site-packages install. Acceptable while the skill runs from a co-located checkout;
    revisit if a wheel deploy target is introduced.
---

# s1-fix1 — Wire --review-scope into the request; create --output parent dir

## Context

Story-level review found two Important contract-vs-behaviour gaps:
1. `--review-scope` is parsed but discarded — `ReviewRequest.scope` is hardcoded `"standard"`, so
   lite/standard/full are behaviourally identical though documented as load-bearing.
2. `--output` writes without creating the parent directory; the documented dispatch path
   `.claude/skills/code-review/runs/<id>.json` (runs/ gitignored, never created) crashes with
   `FileNotFoundError` on a fresh checkout.

## Acceptance Criteria

- `--review-scope <scope>` flows into `_run_analyzers` and sets `ReviewRequest.scope` to that
  value; when the flag is unset the request scope defaults to `lite` (matching the documented
  default). The value is no longer hardcoded `"standard"`.
- `--output <path>` creates the output file's parent directory (`parents=True, exist_ok=True`)
  before the atomic write, after the CWD guard — so a path like `runs/x.json` under CWD whose
  parent does not yet exist is written successfully, not crashed.
- SKILL.md no longer states `npm ci` runs unconditionally; it notes the Node step is skipped
  until the JS toolchain lands (s3), mirroring the Status section's honesty.

## Test specification

- `test_review_scope_flows_into_request` (test_cli.py or test_scope_dispatch.py) — register a
  path/scope-capturing fake analyzer; invoke with `--review-scope standard`; assert the
  `ReviewRequest.scope` the analyzer received equals `"standard"`. Invoke without the flag; assert
  the request scope is `"lite"`.
- `test_output_creates_missing_parent_dir` (test_cli.py) — `monkeypatch.chdir(tmp_path)`; invoke
  `--output sub/dir/result.json` (parent absent) with a fake analyzer; assert exit 0, the nested
  file exists, no `.tmp` remains.
