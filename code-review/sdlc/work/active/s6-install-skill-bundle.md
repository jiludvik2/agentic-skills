---
id: s6-install-skill-bundle
kind: story
project: code-review
status: active
parent: epic-analyzer-ga-hardening
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md, README.md, .claude/skills/code-review/SKILL.md]
created: 2026-05-30
updated: 2026-05-30
tags: [install, cli, packaging, agent-skills, cross-agent, ga-readiness]
---

# s6 — `polyreview install` the skill bundle (agent-independent)

## Summary

Today there is **no install command**, and getting the skill bundle to where an
agent will discover it is a manual copy. Two problems: (1) `pip install polyreview`
ships only the `code_review` package + JSON contracts — the bundle assets
(`SKILL.md`, `code-review.toml.example`, `semgrep-rules/`, `package.json`,
`package-lock.json`) are not in the wheel at all; (2) there is no single "skills
directory" — the Agent Skills standard defines **per-agent** user-level locations,
and `code-review` is consumed cross-agent (Claude, Codex, GitHub Copilot, Gemini
CLI, Cursor, … — see the cross-agent discovery reference and AGENTS.md).

This story ships `polyreview install`: a one-command, idempotent copy of the skill
bundle into the **correct user-level skills directory for whatever agent(s) the
user runs** — not a Claude-only path.

### Target resolution (the agent-independent part)

The bundle lands at `<skills-dir>/code-review/`, where `<skills-dir>` is resolved
from a target **registry** (settled in ADR-0018):

| Target id | User-level skills dir | Notes |
|-----------|-----------------------|-------|
| `agents` (neutral) | `$HOME/.agents/skills/` | Read natively by **Codex**; aliased by **Gemini CLI**. The vendor-neutral default. |
| `claude` | `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/` | Claude / Claude Code (honours its own env override). |
| `copilot` | `$HOME/.copilot/skills/` | GitHub Copilot. |
| `gemini` | `$HOME/.gemini/skills/` | Gemini CLI (also reads `agents`). |

**Default action** (no `--agent`): install to the neutral `agents` target **plus
every agent home already present on the machine** (auto-detect — if `~/.claude`
exists, also install there; likewise `~/.copilot`, `~/.gemini`). This reaches the
agents the user actually has without conjuring homes for agents they don't.
`--agent <id[,id…]>` forces an explicit target set; `--all` installs to every
registry target (creating the homes). The same `code_review` package and the same
SKILL.md serve every agent — agent-specific frontmatter keys are ignored by agents
that don't use them, so one bundle is genuinely portable.

Install **places the bundle** (skill discovery); it does **not** provision the
offline caches (`node_modules/`, Trivy DB, semgrep cache) — `setup.sh` owns that,
and `cache_root()` is CWD-anchored, not skills-dir-anchored (ADR-0018 §6). The
install command's closing hint surfaces the cache step.

This story carries the user-facing contract; ADR-0018 carries the implementation
choices.

## Acceptance criteria

### Scenario: install creates the skills dir when it does not exist
- **Given** a `$HOME` with **no** `.agents/`, `.claude/`, `.copilot/`, or
  `.gemini/` directory at all
- **When** the user runs `polyreview install`
- **Then** exit 0, the neutral `$HOME/.agents/skills/code-review/` tree is created
  from nothing (parents included), and it holds every bundle manifest asset.
  (No pre-existing skills directory is a supported first-run case, not an error.)

### Scenario: install reaches the agents that are present (auto-detect)
- **Given** a `$HOME` where `.claude/` already exists but `.copilot/` and
  `.gemini/` do not
- **When** the user runs `polyreview install` with no `--agent`
- **Then** the bundle is installed to **both** `$HOME/.agents/skills/code-review/`
  (neutral) and `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/code-review/`, and
  **not** to `.copilot`/`.gemini` (absent → not conjured).

### Scenario: --agent targets a specific agent's default dir
- **Given** `--agent copilot`
- **When** install runs
- **Then** the bundle lands at `$HOME/.copilot/skills/code-review/` (created if
  missing) and nowhere else.

### Scenario: --agent claude honours CLAUDE_CONFIG_DIR
- **Given** `CLAUDE_CONFIG_DIR` set to a custom dir and `--agent claude`
- **When** install runs
- **Then** the target is `<CLAUDE_CONFIG_DIR>/skills/code-review/`, not
  `~/.claude/...`.

### Scenario: --all installs to every registry target
- **Given** `--all`
- **When** install runs
- **Then** the bundle is present under each of the four registry skills dirs
  (`agents`, `claude`, `copilot`, `gemini`), each created as needed.

### Scenario: re-install is idempotent; --force refreshes
- **Given** a target that already holds an installed bundle
- **When** `install` runs again without `--force` (reports, no-op per target,
  exit 0) and again with `--force` (in-place refresh)
- **Then** neither run errors or leaves a partial state.

### Scenario: install never touches host-owned files
- **Given** a target skills dir whose parent also holds `agents/reviewer.md`
  (Claude's reviewer sub-agent) and a sibling `skills/other-skill/`
- **When** install runs
- **Then** `reviewer.md` and `skills/other-skill/` are byte-for-byte unchanged;
  only `skills/code-review/` is written.

### Scenario: existing review invocation still resolves after the CLI restructure
- **Given** the subcommand restructure that adds `install`
- **When** a review is invoked through the post-restructure entry point
- **Then** the documented review run still works. The review subcommand spelling is
  decided in ADR-0018 and reflected in `SKILL.md`/README.

### Scenario: install reports per-target results and the cache-provisioning step
- **Given** any install
- **When** it finishes
- **Then** stdout lists each skills dir written (so a multi-target install is
  legible) and names the follow-up (`setup.sh` / provision caches) needed for full
  analyzer coverage.

## Tasks

- **s6-t0 — ADR-0018: install/uninstall design.** The target registry + neutral
  default + auto-detect policy, per-agent env overrides (`CLAUDE_CONFIG_DIR`),
  create-if-missing, the bundle manifest, CLI subcommand restructure,
  idempotency/`--force`, uninstall safety guards (governs s7), the CWD-cache seam.
- **s6-t1 — package the skill bundle in the wheel.** So a pip-installed
  `polyreview` has the bundle assets to copy. Depends on the manifest from s6-t0.
- **s6-t2 — `polyreview install` command.** Subcommand restructure + registry-based
  multi-target copy with auto-detect, `--agent`/`--all`, create-if-missing,
  idempotency/`--force`, host-file safety, per-target report + cache hint.
  Depends on s6-t1.

## Deferred

- **Relocating the runtime caches** to the user-level bundle (so `cache_root()`
  finds a user-level toolchain) — ADR-0018 §6 known seam; out of scope. Caches stay
  `setup.sh` / `POLYREVIEW_CACHE_DIR`.
- **Project-level (`.agents/skills/`, `.claude/skills/`, …) install target** — this
  story is user-level only (operator decision 2026-05-30). The copy mechanism is
  target-agnostic, so a future `--project` flag reuses the registry shape.
- **Symlink install mode** (one canonical copy + per-agent symlinks; Codex follows
  symlinks) — recorded in ADR-0018 as an alternative to N copies; not implemented
  now. Default stays copy-per-target.
