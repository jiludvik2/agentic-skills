---
id: s2-t2-fix1
kind: fix-task
project: code-review
status: done
parent: s2-t2-hotspots
created: 2026-05-26
updated: 2026-05-26
---

# s2-t2-fix1: empty diff_files treated as per-task instead of story-level

## Finding (from reviewer)

Important: `diff_files=set()` was guarded with `if diff_files is not None`, so an empty set
silently returned `[]` instead of story-level scope. Spec AC states "None (or empty)" signals
story-level.

## Fix

Changed both guards in `hotspots.py` from `if diff_files is not None` → `if diff_files`
(truthiness), so `set()` falls through to story-level logic identically to `None`.

Also fixed Minor findings:
- `test_story_level_scope_includes_all_files`: `issubset` → `==`
- Added `test_empty_diff_files_is_story_level_scope` covering the Important case
- Added `test_story_level_scope_includes_metric_only_files` covering MetricSet-only files

## Verification

108 tests pass. ruff + mypy strict clean.
