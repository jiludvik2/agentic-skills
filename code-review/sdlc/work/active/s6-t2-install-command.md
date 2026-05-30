---
id: s6-t2-install-command
kind: task
project: code-review
status: active
parent: s6-install-skill-bundle
sources: [code_review/cli.py, code_review/paths.py, .claude/skills/code-review/SKILL.md, README.md, reference-agentskills-cross-agent-discovery]
created: 2026-05-30
updated: 2026-05-30
tags: [cli, install, typer, agent-skills, cross-agent]
---

# s6-t2 — `polyreview install` command (agent-independent)

## Outcome

`polyreview install` copies the wheel-shipped skill bundle (s6-t1) into the correct
user-level skills directory for whatever agent(s) the user runs — resolved from the
ADR-0018 target registry — creating the directory tree when absent, idempotently,
without touching host-owned files, reporting each target written, and printing the
cache-provisioning next step. Adds the Typer subcommand restructure. Depends on
s6-t1. Implements every s6-story scenario.

## Acceptance criteria

(The s6-story scenarios are the contract; restated here as the per-task gate.)

### Scenario: create-if-missing on a virgin HOME
- **Given** a tmp `$HOME` with no `.agents`/`.claude`/`.copilot`/`.gemini`
- **When** `polyreview install` runs
- **Then** exit 0 and `$HOME/.agents/skills/code-review/` is created from nothing
  (parents included) holding every manifest asset.

### Scenario: neutral + auto-detect default
- **Given** a tmp `$HOME` where only `.claude/` pre-exists
- **When** `install` runs with no `--agent`
- **Then** the bundle is written to both `$HOME/.agents/skills/code-review/` and
  `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/code-review/`, and not to
  `.copilot`/`.gemini`.

### Scenario: --agent scopes targets; --all writes every registry dir
- **Given** `--agent copilot` (then a separate run with `--all`)
- **When** `install` runs
- **Then** `--agent copilot` writes only `$HOME/.copilot/skills/code-review/`;
  `--all` writes the bundle under all four registry skills dirs, each created as
  needed.

### Scenario: --agent claude honours CLAUDE_CONFIG_DIR
- **Given** `CLAUDE_CONFIG_DIR=<tmp>` and `--agent claude`
- **Then** the target is `<tmp>/skills/code-review/`.

### Scenario: idempotent re-install; --force refreshes
- **Given** an already-installed target
- **When** `install` runs without then with `--force`
- **Then** neither run errors or leaves a partial state (per ADR-0018 refresh rule).

### Scenario: host-owned files untouched
- **Given** a target whose parent has `agents/reviewer.md` and `skills/other/`
- **When** install runs
- **Then** both are byte-for-byte unchanged.

### Scenario: review run still resolves post-restructure
- **Given** the subcommand restructure
- **When** a review is invoked via the post-restructure entry point
- **Then** the documented review path runs unchanged in behaviour.

### Scenario: per-target report + cache hint
- **Given** any successful install
- **Then** stdout lists each skills dir written and names the cache follow-up
  (`setup.sh` / provision caches).

## Test specification

Write first, confirm red, then implement. New `tests/test_install_command.py`,
`CliRunner(capture="fd")`. Make tests hermetic by pointing resolution at a tmp dir:
`monkeypatch.setenv("HOME", tmp)` (and `monkeypatch.setattr(Path, "home", …)` if the
code uses `Path.home()`), plus `monkeypatch.delenv`/`setenv` for `CLAUDE_CONFIG_DIR`:

1. `test_install_creates_neutral_dir_on_virgin_home`: virgin `$HOME`, run install,
   assert `$HOME/.agents/skills/code-review/` exists with every manifest asset.
2. `test_install_default_targets_neutral_plus_present_homes`: pre-create `~/.claude`
   only; assert bundle in `.agents` **and** `.claude`, absent from `.copilot`/`.gemini`.
3. `test_install_agent_flag_scopes_target`: `--agent copilot` → only `.copilot`.
4. `test_install_all_writes_every_registry_dir`: `--all` → bundle under all four dirs.
5. `test_install_claude_honours_config_dir_env`: `CLAUDE_CONFIG_DIR` + `--agent
   claude` → `<env>/skills/code-review/`.
6. `test_install_idempotent_without_force` / `test_install_force_refreshes`.
7. `test_install_leaves_reviewer_and_sibling_skills_untouched`.
8. `test_install_reports_targets_and_cache_hint`: stdout lists targets + mentions
   `setup.sh`/cache.
9. `test_review_run_still_invokable_after_restructure`: invoke the review path via
   the post-restructure spelling against existing CLI fixtures; reuse a
   `test_cli` happy-path assertion.

## Notes

- Put the registry + resolver in one place (e.g. `code_review/install.py` or a
  `paths.py` helper) so s7-t0 uninstall imports the **same** registry, env→home
  resolution, auto-detect predicate, and bundle marker — no duplication.
- Copy the bundle from the package via the s6-t1 mechanism (`importlib.resources`).
  `code-review.toml.example` is copied as-is; the command does not write a live
  `code-review.toml` (SKILL.md §Install — that stays the user's choice).
- One SKILL.md serves every agent (agent-specific frontmatter keys are ignored by
  agents that don't use them) — install copies the same bundle to each target.
