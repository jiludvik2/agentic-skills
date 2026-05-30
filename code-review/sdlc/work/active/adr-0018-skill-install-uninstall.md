---
id: adr-0018-skill-install-uninstall
kind: decision
project: code-review
status: accepted
parent: s6-t0-adr-install-uninstall
sources: [s6-install-skill-bundle.md, s7-uninstall-skill-bundle.md, reference-agentskills-cross-agent-discovery, code_review/paths.py, code_review/cli.py, pyproject.toml]
created: 2026-05-30
updated: 2026-05-30
tags: [adr, install, uninstall, packaging, cli, agent-skills, cross-agent, ga-readiness]
---

# ADR-0018: Skill install/uninstall design

## Status

Accepted. Governs `epic-analyzer-ga-hardening` / s6 (`polyreview install`) and
s7 (`polyreview uninstall`). Mirrors how ADR-0016 governs s0 and ADR-0017 governs
s1. The decisions here become testable contracts in s6-t1 (wheel packaging),
s6-t2 (install command) and s7-t0 (uninstall command).

## Context

`code-review` is an Agent Skills bundle. Two gaps block GA:

1. **The wheel ships only code, not the bundle.** `pip install polyreview` installs
   the `code_review` package plus its JSON contracts (`pyproject.toml` →
   `[tool.hatch.build.targets.wheel]` includes only `capabilities.json` and
   `schemas/*.json`). The bundle assets an agent discovers — `SKILL.md`,
   `code-review.toml.example`, `semgrep-rules/`, `package.json`,
   `package-lock.json` — live in the repo at `.claude/skills/code-review/` and are
   absent from the wheel entirely.
2. **There is no single "skills directory."** The Agent Skills standard defines
   **per-agent**, user-level skill locations, and this bundle is consumed
   cross-agent (Claude, Codex, GitHub Copilot, Gemini CLI, Cursor, … — see the
   cross-agent discovery reference and AGENTS.md). Getting the bundle to where an
   agent looks is, today, a manual copy.

`polyreview install` closes both gaps with one idempotent command; `polyreview
uninstall` reverses it safely. The design must be **agent-independent** — no
Claude-only path — and must keep tests hermetic (resolution is `$HOME`-relative,
monkeypatchable to a tmp dir).

## Decision

### 1. Target registry — agent-independent skills-dir resolution

The bundle is placed at `<skills-dir>/code-review/` (the directory name **must**
match the SKILL.md `name: code-review` frontmatter, or the agent won't discover
it). `<skills-dir>` resolves from a registry keyed by target id:

| id | user-level skills dir | read by | env override |
|----|-----------------------|---------|--------------|
| `agents` (neutral) | `$HOME/.agents/skills/` | **Codex** (native); **Gemini CLI** (alias) | none |
| `claude` | `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/` | Claude / Claude Code | `CLAUDE_CONFIG_DIR` |
| `copilot` | `$HOME/.copilot/skills/` | GitHub Copilot | none |
| `gemini` | `$HOME/.gemini/skills/` | Gemini CLI (also reads `agents`) | none |

**Default target policy (no `--agent`):** install to the neutral `agents` target
**plus every agent home already present on the machine** (auto-detect). A home is
"present" iff its base dir exists — `~/.claude`, `~/.copilot`, `~/.gemini`. This
gives the agents the user actually runs native discovery without conjuring homes
for agents they lack. The neutral `agents` target is **always** written (it is the
vendor-neutral default and Codex/Gemini's shared read location), even on a machine
with no agent home at all (first-run case).

- `--agent <id[,id…]>` forces an explicit target set (comma-separated), creating
  those homes if missing.
- `--all` writes **every** registry target, creating all four homes.

Resolution is `$HOME`-relative and reads the per-agent env override at call time,
so tests monkeypatch `$HOME` (and `CLAUDE_CONFIG_DIR`) to a tmp dir and stay
hermetic. The registry is the single source of truth for both install and
uninstall.

*Rationale:* there is no cross-agent "skills dir" standard yet; the neutral
`~/.agents/skills/` is the closest thing (Codex reads it natively, Gemini aliases
it), so it anchors the default. Auto-detect favours reach-what-exists over
install-everywhere, which would litter homes for agents the user never runs.

### 1b. Create-if-missing

A target skills dir that does not exist is the **normal first-run case, not an
error**. Install creates the full tree with `mkdir -p` semantics (parents
included). This explicitly covers "`~/.agents` / `~/.claude` does not exist yet."

### 2. Bundle manifest — the single source of truth for what is copied

A manifest constant — `BUNDLE_MANIFEST` in a new `code_review/bundle.py` — names
exactly the assets that constitute the bundle. s6-t1 (wheel packaging via
`force-include`), s6-t2 (install copy) and s7-t0 (uninstall guard) all read this
one constant so the three operations cannot diverge.

**Copied (shipped in the wheel, placed by install):**

- `SKILL.md`
- `code-review.toml.example`
- `semgrep-rules/` (vendored ruleset, ADR-0016; ~4 KB)
- `package.json`
- `package-lock.json`

**Not copied (provisioned or produced, not shipped):**

- `node_modules/` (~102 MB, host- and platform-specific — `npm ci` territory)
- `cache/` (~1 GB — Trivy DB, prefetched at setup)
- `runs/` (review outputs, produced at runtime)

*Rationale:* the manifest is small, text/config only, and platform-neutral. The
excluded trio is large and host-specific; shipping it in a wheel is infeasible and
wrong — it is `setup.sh`'s job (see §6).

### 3. CLI subcommand restructure

`code_review/cli.py` is a single-command Typer app (`app = typer.Typer(...)`, one
`@app.command()`), so today the review runs as bare `polyreview <flags>`. Adding
`install` and `uninstall` as commands forces Typer to require a command name on
every invocation — the review **must** become a named subcommand.

**Decision: the review subcommand is `polyreview run`; the bare
`polyreview <flags>` form is not preserved.** `install` and `uninstall` join it as
sibling subcommands. The pre-1.0 alpha status (README §Alpha, `Development Status
:: 3 - Alpha`) permits the breaking CLI change. `SKILL.md` (Invocation section)
and `README.md` update to `polyreview run …` in s6-t2.

*Rationale:* an explicit `run` subcommand is unambiguous and avoids the Typer
callback / `invoke_without_command` gymnastics needed to fake a default command
while still parsing per-subcommand flags. Three peer verbs (`run` / `install` /
`uninstall`) read cleanly. **This decision is the public CLI contract and was
ratified by the operator on 2026-05-30 (hard-stop: public API shape).**

### 4. Idempotency & `--force`

- **Without `--force`:** if a target already holds an installed bundle (detected
  by the §5 marker at `<skills-dir>/code-review/SKILL.md`), install reports a
  no-op for that target and exits 0. A partially-present or non-bundle dir at the
  path is treated as "not our bundle" and install refuses that target with a clear
  message rather than overwriting (symmetry with the uninstall guard).
- **With `--force`:** in-place refresh, defined as **remove-then-copy** — `rmtree`
  the existing `<skills-dir>/code-review/` then copy the manifest fresh. This
  guarantees no stale file from a previous bundle version survives (an
  overwrite-merge would leave deleted-upstream files behind).
- **User config is never touched.** The bundle ships `code-review.toml.example`,
  never a live `code-review.toml`. Install neither writes nor overwrites a
  `code-review.toml`; if a user keeps one elsewhere (CWD, per project config), it
  is out of the install target tree and unaffected.

### 5. Uninstall safety guards (governs s7)

`uninstall` walks the **same registry** and, per target, removes **only**
`<skills-dir>/code-review/`, and only when that directory passes a **marker
check**: a readable `SKILL.md` whose frontmatter declares `name: code-review`.

- The marker prevents a mistargeted env var or a name collision from `rmtree`-ing
  an arbitrary directory.
- Uninstall **never** touches a sibling `<skills-dir>/<other-skill>/`, the agent's
  `agents/reviewer.md` (Claude's reviewer sub-agent), the skills dir itself, or any
  agent home.
- **Non-interactive, no confirmation prompt.** The operation is marker-guarded,
  narrowly scoped, and reversible (re-install), and tests run non-interactive, so
  there is no `--yes` prompt to bypass. A `--dry-run` flag is **not** in scope for
  s7 (the deferred symlink mode, §7, would change its shape).
- **No-op when nothing is installed:** a target with no `code-review/` dir reports
  "nothing to uninstall" and exits 0.
- **Refusal is reported, never silent.** If a target's `code-review/` dir exists
  but fails the marker check, uninstall skips it with an explicit refusal message
  and continues to the remaining targets. The command's overall exit code is
  non-zero iff at least one target was refused (a real anomaly worth surfacing);
  clean removals and genuine no-ops keep exit 0.

### 6. The CWD-anchored-cache seam

`cache_root()` (`code_review/paths.py:15`) resolves `$POLYREVIEW_CACHE_DIR` if set,
else **CWD-relative** `./.claude/skills/code-review` — matching the
`code-review.toml` lookup and the `--output` guard (ADR-0015). It does **not**
resolve any user-level skills dir.

Therefore a user-level install gives an agent skill **discovery** but does **not**
relocate the runtime caches (`node_modules/`, Trivy DB). `setup.sh` /
`POLYREVIEW_CACHE_DIR` still own cache provisioning, CWD-anchored. The install
command's closing hint names this follow-up explicitly (run `setup.sh` / provision
caches for full analyzer coverage).

**Full user-level cache relocation is deferred** (out of epic scope). The migration
path when it is taken: point `cache_root()` at a user-level location with
`POLYREVIEW_CACHE_DIR`, or teach it to fall back to the installed bundle dir. Not
done now — it would change the cache contract for every adapter and every CI run.

### 7. Copy-per-target vs. symlink

**Default and chosen implementation: an independent copy into each resolved skills
dir.** N targets → N copies of the (small, text-only) manifest.

The **symlink alternative** — one canonical copy plus per-agent symlinks (Codex
follows symlinks) — is recorded and **deferred**: it complicates the uninstall
guard (a symlink's marker check and safe removal differ from a real dir) and is
not portable to Windows. The manifest is small enough that copy-per-target costs
nothing meaningful. Default stays copy.

## Consequences

- s6-t1 packages `BUNDLE_MANIFEST` into the wheel (hatch `force-include`), so a
  pip-installed `polyreview` carries the assets install copies.
- s6-t2 builds `run` / `install` and the registry resolver; `SKILL.md` + `README`
  switch to `polyreview run`.
- s7-t0 builds `uninstall` against the same registry + marker guard.
- The CLI break (`polyreview <flags>` → `polyreview run <flags>`) is a one-time
  pre-1.0 change; any doc or agent invocation referencing the bare form updates in
  s6-t2.
- Caches remain CWD-anchored; the discovery/cache split is documented, not closed.

## Deferred

- User-level cache relocation (§6).
- Symlink install mode (§7).
- Project-level install target (`.agents/skills/`, `.claude/skills/`, … in a repo)
  — user-level only this story; the registry shape is reusable for a future
  `--project` flag.
