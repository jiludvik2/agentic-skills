---
id: s1-t3-setup-script
kind: task
project: code-review
status: active
parent: s1-reviewer-skill-and-capabilities
created: 2026-05-26
updated: 2026-05-26
---

# s1-t3 — scripts/setup.sh (idempotent installer)

## Outcome

`./scripts/setup.sh` installs Python and Node deps, prefetches offline caches (stub for s1; real fetches arrive with the adapters in s3), and copies the reviewer sub-agent into the host project. Re-running is idempotent and the script exits non-zero with a clear message on any step failure.

## Acceptance Criteria

- `scripts/setup.sh` runs, in order: `uv sync --frozen`, `npm ci` (guarded — skip gracefully if no `package.json`/`package-lock.json` yet), `python scripts/prefetch_caches.py` (a stub that creates `cache/` and is content-addressed/no-op on re-run), and copies `.claude/agents/reviewer.md` from the skill into the host project's `.claude/agents/`.
- `set -euo pipefail` semantics: any failed step aborts with a non-zero exit and a human-readable error naming the failed step.
- Idempotent: a second run when `cache/` and deps already exist refreshes without error and does not redundantly re-download (content-addressed check).
- The copied `.claude/agents/reviewer.md` is byte-identical across two consecutive runs.

## Test specification

New `tests/test_setup_script.py`:

- `test_setup_script_exists_and_executable` — assert `scripts/setup.sh` exists and has the executable bit; assert `scripts/prefetch_caches.py` exists.
- `test_setup_script_passes_shellcheck_or_bash_n` — run `bash -n scripts/setup.sh`; assert exit 0 (syntax valid). If `shellcheck` is on PATH, run it and assert no errors (skip if absent).
- `test_prefetch_caches_idempotent` — run `prefetch_caches.py` twice in a tmp CWD; assert exit 0 both times; assert `cache/` exists; assert the second run does not re-create already-present content (check mtime or a sentinel).
- `test_setup_script_fails_loud_on_bad_step` (subprocess) — invoke a copy of the script with an injected failing command; assert non-zero exit and error text names the step.

## Notes / deferrals

- Real Trivy DB / Semgrep rule-pack fetches → s3 (the adapters that need them). `prefetch_caches.py` is a typed stub here. The full "setup.sh installs everything" and "sandbox-installable" integration scenarios are exercised manually outside the sandbox; this task covers the script's structure, idempotency, and failure semantics via unit/subprocess tests.
- `npm ci` step is guarded because no `package.json` exists until TS analyzers land (s3).
