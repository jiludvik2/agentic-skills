---
id: s6-t2-install-command
kind: task
project: code-review
status: active
parent: s6-install-into-claude
sources: [code_review/cli.py, code_review/paths.py, .claude/skills/code-review/SKILL.md, README.md]
created: 2026-05-30
updated: 2026-05-30
tags: [cli, install, typer, claude-config-dir]
---

# s6-t2 — `polyreview install` command

## Outcome

`polyreview install` copies the wheel-shipped skill bundle (s6-t1) into
`${CLAUDE_CONFIG_DIR:-~/.claude}/skills/code-review/`, idempotently, without
touching host-owned files, and prints the cache-provisioning next step. Adds the
Typer subcommand restructure decided in ADR-0018. Depends on s6-t1. Implements the
s6 story's install + idempotency + safety + restructure + hint scenarios.

## Acceptance criteria

(The six s6-story scenarios are the contract; restated here as the per-task gate.)

### Scenario: clean install
- **Given** a tmp config dir (via `CLAUDE_CONFIG_DIR`) with no `skills/code-review/`
- **When** `polyreview install` runs
- **Then** exit 0 and `<config>/skills/code-review/` holds every manifest asset.

### Scenario: CLAUDE_CONFIG_DIR honoured; default is ~/.claude
- **Given** `CLAUDE_CONFIG_DIR` set / unset
- **When** install runs
- **Then** the target is the env dir when set, else `Path.home()/.claude`.

### Scenario: idempotent re-install; --force refreshes
- **Given** an already-installed bundle
- **When** `install` runs without `--force` (reports, no-op, exit 0) and again with
  `--force` (in-place refresh per ADR-0018)
- **Then** neither run errors or leaves a partial state.

### Scenario: host-owned files untouched
- **Given** the config dir also has `agents/reviewer.md` and `skills/other/`
- **When** install runs
- **Then** both are byte-for-byte unchanged.

### Scenario: review run still resolves post-restructure
- **Given** the subcommand restructure
- **When** a review is invoked via the post-restructure entry point
- **Then** the documented review path runs (no silent loss of the analyzer run).

### Scenario: closing hint names cache provisioning
- **Given** a successful install
- **Then** stdout names the follow-up (`setup.sh` / provision caches) for full
  analyzer coverage.

## Test specification

Write first, confirm red, then implement. New `tests/test_install_command.py`,
`CliRunner(capture="fd")`, `monkeypatch.setenv("CLAUDE_CONFIG_DIR", tmp_path)`:

1. `test_install_copies_bundle_to_config_dir`: run `install`, assert each manifest
   asset exists under `<tmp>/skills/code-review/`, exit 0.
2. `test_install_defaults_to_home_claude_when_env_unset`: with `CLAUDE_CONFIG_DIR`
   unset and `Path.home` monkeypatched to a tmp dir, assert target is
   `<home>/.claude/skills/code-review/`.
3. `test_install_idempotent_without_force`: install twice, assert exit 0 and a
   "already installed" message, no exception.
4. `test_install_force_refreshes_in_place`: pre-seed a stale marker file, run
   `install --force`, assert the bundle is refreshed and the stale file gone (or
   per the ADR-0018 refresh rule).
5. `test_install_leaves_reviewer_and_sibling_skills_untouched`: seed
   `agents/reviewer.md` + `skills/other/x`, run install, assert both unchanged.
6. `test_install_prints_cache_provisioning_hint`: assert stdout mentions cache /
   `setup.sh`.
7. `test_review_run_still_invokable_after_restructure`: invoke the review path via
   the post-restructure command spelling against the existing CLI fixtures; assert
   it behaves as before (reuse an existing `test_cli` happy-path assertion).

## Notes

- Resolve the config dir through a small helper (e.g. `_config_dir()` in `cli.py`
  or `paths.py`) so s7-t0 uninstall shares it — do not duplicate the
  env→home fallback.
- Copy the bundle from the package via the s6-t1 mechanism (`importlib.resources`).
  `code-review.toml.example` is copied as-is; the command does **not** write a live
  `code-review.toml` (that stays the user's choice — SKILL.md §Install).
