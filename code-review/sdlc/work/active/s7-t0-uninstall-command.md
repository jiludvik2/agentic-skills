---
id: s7-t0-uninstall-command
kind: task
project: code-review
status: active
parent: s7-uninstall-from-claude
sources: [code_review/cli.py, .claude/skills/code-review/SKILL.md]
created: 2026-05-30
updated: 2026-05-30
tags: [cli, uninstall, safety, typer]
---

# s7-t0 — `polyreview uninstall` command

## Outcome

`polyreview uninstall` removes the installed skill bundle from
`${CLAUDE_CONFIG_DIR:-~/.claude}/skills/code-review/` — scoped to that directory,
gated on the bundle marker, idempotent, and provably non-destructive to host-owned
files. Reuses the config-dir resolver and bundle marker from s6. Implements every
s7-story scenario. Depends on s6.

## Acceptance criteria

(The five s7-story scenarios are the contract; restated as the per-task gate.)

### Scenario: removes the bundle
- **Given** an installed bundle (marker present)
- **When** `uninstall` runs
- **Then** exit 0 and `<config>/skills/code-review/` is gone.

### Scenario: no-op when absent
- **Given** no `skills/code-review/`
- **When** `uninstall` runs
- **Then** exit 0, "nothing to uninstall", no error.

### Scenario: refuses non-bundle dir
- **Given** `skills/code-review/` without the marker
- **When** `uninstall` runs
- **Then** non-zero exit, message names the marker check, directory intact.

### Scenario: host-owned files & siblings untouched
- **Given** `agents/reviewer.md` + `skills/other/` present
- **When** `uninstall` runs
- **Then** both and `<config>` itself are unchanged; only the bundle is removed.

### Scenario: install→uninstall round-trip clean
- **Given** a fresh install
- **When** `uninstall` runs
- **Then** the config dir matches its pre-install state.

## Test specification

Write first, confirm red, then implement. New `tests/test_uninstall_command.py`,
`CliRunner(capture="fd")`, `monkeypatch.setenv("CLAUDE_CONFIG_DIR", tmp_path)`.
Build the "installed" state by invoking the s6 install command (so the round-trip
test exercises both), or by seeding the marker file directly for the unit cases:

1. `test_uninstall_removes_bundle`: seed an installed bundle, run `uninstall`,
   assert the dir is gone, exit 0.
2. `test_uninstall_noop_when_absent`: no bundle, run `uninstall`, assert exit 0 and
   a "nothing to uninstall" message.
3. `test_uninstall_refuses_unmarked_dir`: create `skills/code-review/` without the
   marker, run `uninstall`, assert non-zero exit, message names the marker check,
   and the dir still exists.
4. `test_uninstall_leaves_reviewer_and_siblings`: seed `agents/reviewer.md` +
   `skills/other/x` + an installed bundle, run `uninstall`, assert only the bundle
   is removed and the rest is unchanged.
5. `test_install_uninstall_round_trip`: snapshot the tmp config dir, `install`,
   `uninstall`, assert the dir matches the snapshot (no orphans).

## Notes

- Import the config-dir resolver and the marker predicate from where s6-t2 placed
  them — do not re-implement the env→home fallback or the marker logic.
- The marker check is the load-bearing safety guard: never `rmtree` a path that
  fails it. Per ADR-0018 §5, decide whether a `--yes`/confirmation is required for
  the interactive (non-test) path; tests pass `--yes` (or its equivalent) so they
  stay non-interactive.
