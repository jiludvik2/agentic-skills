---
id: s0-fix3-semgrep-rules-cwd-relative
kind: task
project: code-review
status: done
parent: s0-deployment-layout-fixup
sources: [s0-deployment-layout-fixup.md, story-level review of s0]
created: 2026-05-28
updated: 2026-05-28
tags: [deployment, cache, semgrep, story-level-fix]
---

# s0-fix3 — semgrep rules cache: CWD-relative (story-level Review fix)

## Outcome

`code_review/adapters/semgrep.py:20-28` migrates its `_DEFAULT_RULES` from `Path(__file__).parent.parent.parent / ".claude" / "skills" / "code-review" / "cache" / "semgrep" / "rules"` to the same CWD-relative idiom used by `_trivy_cache_dir()` and `_node_modules()` in trivy.py / js_base.py.

## Why this is a story-level fix

Story `s0-deployment-layout-fixup` aimed to eliminate sibling-layout path arithmetic across `code_review/`. The AC2 grep check passed because it grepped for the literal `_SKILL_DIR` token, but the AC's intent — "nothing computes `.claude/skills/code-review/` from `__file__`" — was violated by `_DEFAULT_RULES` in semgrep.py. The story-level Reviewer flagged this as Important.

## Acceptance criteria

- `_DEFAULT_RULES` constant is replaced by a `_semgrep_rules_dir()` function returning `Path.cwd() / ".claude" / "skills" / "code-review" / "cache" / "semgrep" / "rules"` (same shape as `_trivy_cache_dir()` / `_node_modules()`).
- The two call sites at semgrep.py:53-54 use the function.
- `grep -rn "Path(__file__).resolve().parent.parent.parent" code_review/` returns empty after the change.
- Full test suite passes (existing semgrep tests do not patch `_DEFAULT_RULES`; they use the `semgrep_rules` config dict override, so no test migration needed).
- Ruff and mypy clean.

## Test specification

- **Regression-only**: existing `tests/test_adapters/test_semgrep.py` and `tests/test_sandbox_compatibility.py` must continue to pass without modification.
- No new test added in this fix task: cache-path-unification testing is the scope of `s0-t6`, which will introduce a single producer/consumer resolver across all three adapters.

## Notes

- The fix mirrors the pattern landed in s0-t2 for trivy/js_base. When `s0-t6-cache-path-unification` is planned, this third call site folds in alongside trivy and js_base into a shared `_cache_root()` helper.
- Story-level Reviewer also flagged the duplicated layout literal across three adapters (Minor); that consolidation is correctly owned by `s0-t6` and is not in scope here.
