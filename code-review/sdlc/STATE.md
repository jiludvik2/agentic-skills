# State — last updated 2026-05-26

**Active focus:** Executing s0 — t0–t6 complete and committed. Only `s0-t7` (error isolation + atomic write + hardened CWD guard) remains.

**Last completed:** `s0-t6` — diff-scoped analysis: `code_review/diff.py` (`resolve_diff_paths` via `git diff --name-only`), `--diff` wired into `_run_analyzers`, `cwd` param added to `base.run_subprocess`. 30/30 tests GREEN, mypy strict clean. Adapters already honour `request.target_paths` (Semgrep positional, Radon file collection).

**Next:** `s0-t7` — read spec at `sdlc/work/active/s0-t7-error-isolation-and-atomic-write.md`. Write tests first (RED), implement, GREEN, commit. Then s0 story is complete → consider Verify/Review per SDLC.

**Sandbox:** RESOLVED. rtk hook prefixes commands with `rtk `; `excludedCommands` now lists `rtk uv *`/`rtk gh *`/`rtk pre-commit *`. uv/gh/pre-commit run unsandboxed correctly (verified `uv sync` exit 0, no SCDynamicStore panic). pytest/mypy run fine sandboxed. No more `dangerouslyDisableSandbox` needed.

## Open questions
- `sw-delivery-harness/.claude/settings.json` has the same excludedCommands fix applied but uncommitted (separate repo) — commit there when convenient.
