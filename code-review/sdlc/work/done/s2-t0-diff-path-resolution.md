---
id: s2-t0-diff-path-resolution
kind: task
project: code-review
status: done
parent: s2-skill-interpretation-and-golden-bundle
sources: [adr-0020-thin-invocation-runner.md, s1-t3-cli-bundle-and-delete-sarif-layer.md]
created: 2026-05-31
updated: 2026-05-31
tags: [diff, cli, bugfix]
---

# Task s2-t0 — diff-path resolution anchors on the repo root

## Outcome

A diff-scoped review (`polyreview run --diff <range>`) launched from a **repository
subdirectory** resolves changed-file paths correctly, so the analyzers receive paths that
point at real files regardless of where the CLI was invoked.

## The bug

`cli.py:113` calls `resolve_diff_paths(Path.cwd(), diff)`. `git diff --name-only` always
returns **repo-root-relative** paths (git's behaviour is independent of the cwd it runs in).
Those repo-relative paths are then placed in `request.target_paths` and handed to the
analyzers, which resolve them relative to `Path.cwd()`. When the CLI is run from the repo
root the two coincide and it works; when run from a subdirectory the paths mis-resolve and the
analyzers silently scan nothing or the wrong files (obs 3036, 2026-05-30). Silent zero-signal
on a security review is the worst failure mode (the F3 lesson).

## Design

- **Discover the real repo root** instead of assuming `Path.cwd()` is it. Add a helper (in
  `diff.py`) that runs `git rev-parse --show-toplevel` and returns the toplevel `Path`; fall
  back to `Path.cwd()` if the command fails (not a git repo / git absent) so the
  non-repo `--target` path is unaffected.
- **Return paths the analyzers can use from any cwd.** `resolve_diff_paths` resolves each
  repo-relative changed path against the discovered repo root and returns **absolute** paths
  (or repo-root-relative paths the analyzers are anchored to — pick one and make it consistent;
  absolute is simplest and unambiguous). The CLI passes the repo root (not `Path.cwd()`) into
  `resolve_diff_paths`.
- Keep the existing graceful-empty behaviour: a failed/zero-result `git diff` still returns
  `()`, and the run proceeds (selecting nothing to scan) rather than crashing.

## Acceptance criteria

- Running a diff-scoped review from a subdirectory of the repo produces `target_paths` that
  resolve to the actually-changed files (RED: the pre-fix code yields paths that don't exist
  relative to the subdir cwd; GREEN: they resolve).
- Running from the repo root is unchanged (regression: existing diff behaviour preserved).
- A non-git target (`--target .` outside a repo) still works — the repo-root discovery falls
  back to cwd without raising.
- `uv run pytest`, `uv run ruff check .`, `uv run mypy code_review` clean.

## Test specification (write first, confirm RED)

1. `tests/test_diff.py` — `test_diff_paths_resolve_from_subdir`: create a temp git repo with a
   committed file under a subdir, make a change, `chdir` into the subdir, call the
   diff-resolution path, assert the returned paths point at the real changed file (exist on
   disk from the cwd). RED against the current `Path.cwd()`-anchored code.
2. `test_repo_root_discovery_falls_back_outside_git`: in a non-git tmp dir, the repo-root
   helper returns cwd (or the documented fallback) without raising.
3. Preserve/extend the existing `resolve_diff_paths` happy-path test (run from root still
   returns the changed paths).

## Notes

- Touches `diff.py` and the `cli.py` call site only. No SARIF, no bundle-shape change.
- This is the s1-t3 "carry to s2" item — the CLI rewrite did not fix it in passing.
