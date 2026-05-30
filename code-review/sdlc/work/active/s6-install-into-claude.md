---
id: s6-install-into-claude
kind: story
project: code-review
status: active
parent: epic-analyzer-ga-hardening
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md, README.md, .claude/skills/code-review/SKILL.md]
created: 2026-05-30
updated: 2026-05-30
tags: [install, cli, packaging, claude-config-dir, ga-readiness]
---

# s6 — `polyreview install` into the user's `.claude`

## Summary

Today there is **no install command**. Getting the skill bundle into a user's
`.claude/skills/code-review/` is a manual copy: `pip install polyreview` ships
only the `code_review` package + JSON contracts (`pyproject.toml`
`[tool.hatch.build.targets.wheel].include`), and the operator is left to hand-copy
`SKILL.md` and friends from a source checkout. The bundle assets that an installed
wheel would need — `SKILL.md`, `code-review.toml.example`, `semgrep-rules/`,
`package.json`, `package-lock.json` — are **not in the wheel at all** (they live at
`.claude/skills/code-review/` in the repo, outside the package).

This story ships `polyreview install`: a one-command, idempotent copy of the skill
bundle into the **user-level** Claude config directory so every project the user
opens can discover the skill (Claude Code and the ~40 agents that read
`.claude/skills/` — see the cross-agent discovery note). It has two prerequisites,
both owned here: (1) the bundle assets must be packaged into the wheel so there is
something to copy from a pip install; (2) the Typer app must move from its single
unnamed command to named subcommands so `install` (and s7's `uninstall`) can sit
alongside the review run.

Install **places the bundle**; it does **not** provision the offline caches
(`node_modules/`, Trivy DB, semgrep cache) — `setup.sh` owns that, and
`cache_root()` is CWD-anchored, not `~/.claude`-anchored. The interaction between a
user-level bundle and CWD-anchored caches is a known seam recorded in ADR-0018 and
surfaced to the user by the install command's closing hint, not solved here.

Design decisions (target-dir resolution, bundle manifest, CLI restructure,
idempotency, the cache seam) are settled in **ADR-0018** (authored in s6-t0). This
story carries the user-facing contract; ADR-0018 carries the implementation
choices.

## Acceptance criteria

### Scenario: install places the bundle in the user config dir
- **Given** a clean `${CLAUDE_CONFIG_DIR:-~/.claude}` with no `skills/code-review/`
- **When** the user runs `polyreview install`
- **Then** exit code is 0 and `<config>/skills/code-review/` exists containing at
  least `SKILL.md`, `code-review.toml.example`, `semgrep-rules/security.yaml`,
  `package.json`, and `package-lock.json`.

### Scenario: CLAUDE_CONFIG_DIR is honoured
- **Given** `CLAUDE_CONFIG_DIR` set to a custom directory
- **When** the user runs `polyreview install`
- **Then** the bundle is written under that directory's `skills/code-review/`, not
  under `~/.claude`.

### Scenario: re-install is idempotent
- **Given** a directory that already contains an installed bundle
- **When** the user runs `polyreview install` again **without** `--force`
- **Then** exit code is 0, the command reports the existing install, and it does
  not error or partially clobber. With `--force` the bundle is refreshed in place.

### Scenario: install never touches host-owned files
- **Given** a config dir that also contains `agents/reviewer.md` and a sibling
  `skills/other-skill/`
- **When** `polyreview install` runs
- **Then** `agents/reviewer.md` and `skills/other-skill/` are byte-for-byte
  unchanged.

### Scenario: existing review invocation still resolves after the CLI restructure
- **Given** the subcommand restructure that adds `install`
- **When** a review is invoked through the post-restructure entry point
- **Then** the documented review run still works (the restructure does not silently
  drop the analyzer-run path). The exact spelling of the review subcommand is
  decided in ADR-0018 and reflected in `SKILL.md`/README.

### Scenario: install reports the cache-provisioning next step
- **Given** a successful install
- **When** the command finishes
- **Then** stdout names the follow-up needed for full analyzer coverage (run
  `setup.sh` / provision caches), so the user is not left thinking a bundle copy
  alone makes every analyzer available.

## Tasks

- **s6-t0 — ADR-0018: install/uninstall design.** Target-dir resolution
  (`CLAUDE_CONFIG_DIR` → `~/.claude`), the bundle manifest (what is and isn't
  copied), CLI subcommand restructure + backwards-compat call, idempotency/`--force`
  semantics, uninstall safety guards (governs s7), and the CWD-anchored-cache seam.
- **s6-t1 — package the skill bundle in the wheel.** So a pip-installed
  `polyreview` has the bundle assets to copy. Depends on the manifest from s6-t0.
- **s6-t2 — `polyreview install` command.** Subcommand restructure + copy bundle to
  the resolved config dir; idempotency/`--force`; host-file safety; closing hint.
  Depends on s6-t1.

## Deferred

- **Relocating the runtime caches to the user-level bundle** (so `cache_root()`
  finds a user-level `node_modules/`/Trivy DB) — recorded in ADR-0018 as a known
  seam; out of scope for this story. Install stays a bundle copy; cache
  provisioning stays `setup.sh`/`POLYREVIEW_CACHE_DIR`.
- **Project-level (`./.claude`) install target** — this story is user-level only
  (operator decision 2026-05-30). The copy mechanism is target-agnostic, so a
  future `--project` flag is a small extension, not a redesign.
- **Uninstall** — s7.
