---
id: s0-t0-bandit-stdout-progress-bar
kind: task
project: code-review
status: done
parent: s0-analyzer-adapter-robustness
sources: [post-ga-self-review-findings.md, code_review/adapters/bandit.py]
created: 2026-05-30
updated: 2026-05-30
tags: [bandit, adapter, json-parse, sast, important]
notes: |
  Closed 2026-05-30. Verify PASS, Review MINOR-ONLY. Fix: `--quiet` + strip-to-first-`{`
  before json.loads; 3 new mocked tests (progress-bar/plain/garbage). In-green-bar:
  pinned the garbage-branch error message + softened the comment.
  Deferred Minor (opportunistic): bandit decode-first (`find("{")` on str) diverges
  from sibling adapters that json.loads raw bytes; could use `find(b"{")` to match house
  style. Harmless.
---

# s0-t0 — bandit: tolerate a progress-bar prefix on stdout (F3)

## Outcome

The bandit adapter parses bandit's findings even when bandit emits a Rich progress
bar (`Working... ━━━ 100% 0:00:00`) to stdout ahead of the JSON document — so the
primary Python SAST scanner stops returning `status: error` "invalid JSON" on
real-world Python repos.

## Root cause (confirmed)

`code_review/adapters/bandit.py:73` does `json.loads(result.stdout)`. Newer bandit
prints a progress bar to **stdout** before the JSON; the leading non-JSON line breaks
the parse. Intermittent — small/fast scans don't render the bar, larger trees do.

## Acceptance criteria

- **Given** bandit stdout of the form `Working... ━━━ 100% 0:00:00\n{ "results": [...] }`
- **When** the adapter parses it
- **Then** it returns `status: ok` with the findings, not `status: error`.
- Plain-JSON stdout (no progress bar) still parses (no regression).
- A genuinely malformed/empty stdout still yields a clear `status: error`.

## Test specification (tests-first)

In `tests/test_adapters/test_bandit.py` (create if absent):
1. `test_bandit_parses_stdout_with_progress_bar_prefix`: feed the adapter (via a
   patched `run_subprocess` returning a `SubprocessResult` whose stdout is a
   progress-bar prefix + valid bandit JSON) → assert findings parsed, status ok.
2. `test_bandit_parses_plain_json` (regression): plain JSON stdout → findings, ok.
3. `test_bandit_reports_error_on_garbage_stdout`: stdout with no JSON object at all →
   `status: error` (no silent empty).

Confirm RED first.

## Implementation note

Prefer `bandit -q`/`--quiet` in the invocation (suppresses the bar at source) **and/or**
slice from the first `{` before `json.loads` as a defensive parse. Keep whichever the
tests pin; the strip-to-`{` guard is robust even if a future bandit flag changes.
Self-contained, one commit.
