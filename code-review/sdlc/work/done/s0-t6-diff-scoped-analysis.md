---
id: s0-t6-diff-scoped-analysis
kind: task
project: code-review
status: done
parent: s0-analyzer-facade-and-two-adapters
created: 2026-05-26
updated: 2026-05-26
---

# s0-t6 — Diff-scoped analysis

## Outcome

`code_review/diff.py` resolves changed file paths from a git diff range. The CLI `--diff <range>` flag passes the result into `ReviewRequest.target_paths`; both adapters honour it and scope their analysis to only the listed files. Pre-existing findings in unchanged files are absent from the output.

## Acceptance Criteria

- `code_review/diff.py` exports `async def resolve_diff_paths(repo_root: Path, diff_range: str) -> tuple[str, ...]` that runs `git diff --name-only <diff_range>` via `asyncio.create_subprocess_exec` (reusing `base.run_subprocess`) and returns a tuple of repo-relative paths.
- When `--diff` is passed, `ReviewRequest.target_paths` is set to the resolved paths; without `--diff`, `target_paths = (str(target),)`.
- `SemgrepAdapter` passes `request.target_paths` as positional path arguments to Semgrep; only findings in those paths appear in output.
- `RadonAdapter` restricts its `cc_visit` / `mi_visit` calls to `request.target_paths`; only those files appear in `MetricSet.per_file`.
- Running the CLI with `--diff HEAD~1..HEAD` against a temp repo where a finding exists only in commit 2's file returns only that finding; commit 1's file (unchanged by that diff) produces no results.
- `mypy --strict` passes on `diff.py`.

## Test specification

`tests/test_diff.py` — written first:

- `test_resolve_diff_paths_returns_changed_files` — create a temp git repo (`git init`, author config, two commits: file A in commit 1, file B in commit 2); call `asyncio.run(resolve_diff_paths(repo, "HEAD~1..HEAD"))`; assert result == `("file_b.py",)` (or the equivalent relative path).
- `test_resolve_diff_paths_empty_range` — assert that a diff range with no changes (e.g. `HEAD..HEAD`) returns an empty tuple.

`tests/test_cli.py` additions:

- `test_diff_scope_excludes_unchanged_files` — use `FakeAnalyzer` seeded with findings for both `"changed.py"` and `"unchanged.py"`; mock `resolve_diff_paths` to return `("changed.py",)`; run CLI with `--diff HEAD~1..HEAD`; load output JSON; assert only `"changed.py"` findings present, no `"unchanged.py"` findings.

Note: the diff-scoping test uses `FakeAnalyzer` with a mocked `resolve_diff_paths` to stay deterministic without depending on the real fixture repo's git history.
