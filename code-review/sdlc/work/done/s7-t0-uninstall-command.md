---
id: s7-t0-uninstall-command
kind: task
project: code-review
status: done
parent: s7-uninstall-skill-bundle
sources: [code_review/cli.py, .claude/skills/code-review/SKILL.md, reference-agentskills-cross-agent-discovery]
created: 2026-05-30
updated: 2026-05-30
tags: [cli, uninstall, safety, typer, agent-skills, cross-agent]
notes: |
  Closed 2026-05-30. Verify PASS (6/6 AC scenarios covered), Review MINOR-ONLY.
  Impl: `uninstall(targets)` in code_review/install.py reuses the s6 registry/
  resolver/marker (is_our_bundle); `uninstall` Typer command in cli.py mirrors
  install (no --force). 9 tests, suite 413 passed, ruff+mypy clean.
  In-green-bar cleanup applied: added recursive-nested-tree removal test and
  mixed present+absent message-suppression test (2 of the reviewer's coverage Minors).
  Deferred Minors (opportunistic):
  - cli.py install/uninstall duplicate the comma-split + resolve_targets + ValueError
    →Exit(1) + per-result echo loop; hoist into a shared _resolve_targets_or_exit helper.
  - uninstall calls do_uninstall bare (no FileNotFoundError guard) by design (reads no
    bundle source); add a one-line comment marking the asymmetry intentional.
  - round-trip test asserts no `code-review` dir survives via rglob but does not snapshot
    full pre-install home parity (fidelity nit).
---

# s7-t0 — `polyreview uninstall` command (agent-independent)

## Outcome

`polyreview uninstall` removes the installed skill bundle from every target the s6
registry could have written to — `<skills-dir>/code-review/` for the neutral
`agents` dir plus each agent home — scoped per `--agent`/`--all`, gated on the
bundle marker, idempotent, and provably non-destructive to host-owned files. Reuses
the registry, resolver, and marker from s6. Implements every s7-story scenario.
Depends on s6.

## Acceptance criteria

(The s7-story scenarios are the contract; restated as the per-task gate.)

### Scenario: removes the bundle from every installed target
- **Given** a bundle (marker present) in both `~/.agents/skills/code-review/` and
  `~/.claude/skills/code-review/`
- **When** `uninstall` runs
- **Then** exit 0 and both are gone.

### Scenario: --agent scopes removal
- **Given** the bundle in `agents` and `claude` targets
- **When** `uninstall --agent claude` runs
- **Then** only `~/.claude/skills/code-review/` is removed; the `agents` copy stays.

### Scenario: no-op when absent
- **Given** no `code-review/` under any registry skills dir
- **When** `uninstall` runs
- **Then** exit 0, "nothing to uninstall", no error.

### Scenario: refuses a dir without the marker
- **Given** `<skills-dir>/code-review/` lacking the marker
- **When** `uninstall` runs
- **Then** non-zero exit, message names the marker check, that dir intact, and the
  outcome of other targets is still reported (no silent partial run).

### Scenario: host-owned files & siblings untouched
- **Given** `agents/reviewer.md` + `skills/other/` alongside an installed bundle
- **When** `uninstall` runs
- **Then** both and the skills dir itself are unchanged; only the bundle is removed.

### Scenario: install→uninstall round-trip clean across targets
- **Given** a fresh multi-target `install`
- **When** `uninstall` runs
- **Then** every touched skills dir matches its pre-install state (no orphans).

## Test specification

Write first, confirm red, then implement. New `tests/test_uninstall_command.py`,
`CliRunner(capture="fd")`, hermetic via `$HOME`/`CLAUDE_CONFIG_DIR` monkeypatch as
in s6-t2. Build "installed" state by invoking the s6 install command (so the
round-trip exercises both) or by seeding the marker file directly for unit cases:

1. `test_uninstall_removes_from_all_installed_targets`: seed `agents` + `claude`
   bundles, run `uninstall`, assert both gone, exit 0.
2. `test_uninstall_agent_flag_scopes_removal`: seed both, `--agent claude` → only
   `claude` removed.
3. `test_uninstall_noop_when_absent`: no bundle → exit 0, "nothing to uninstall".
4. `test_uninstall_refuses_unmarked_dir`: create `<skills-dir>/code-review/` without
   the marker → non-zero, marker-check message, dir survives.
5. `test_uninstall_leaves_reviewer_and_siblings`: seed `agents/reviewer.md` +
   `skills/other/x` + bundle → only bundle removed.
6. `test_install_uninstall_round_trip`: snapshot tmp `$HOME`, `install` (default
   multi-target), `uninstall`, assert it matches the snapshot.

## Notes

- Import the registry, resolver, auto-detect predicate, and marker from where s6-t2
  placed them — do not re-implement.
- The marker check is the load-bearing safety guard: never `rmtree` a path that
  fails it, on any target. Per ADR-0018 §5, decide whether `--yes`/confirmation
  guards the interactive path; tests pass `--yes` (or equivalent) to stay
  non-interactive.
