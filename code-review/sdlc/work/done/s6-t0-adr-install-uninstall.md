---
id: s6-t0-adr-install-uninstall
kind: task
project: code-review
status: done
parent: s6-install-skill-bundle
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md, .claude/skills/code-review/SKILL.md, code_review/paths.py, pyproject.toml, reference-agentskills-cross-agent-discovery]
created: 2026-05-30
updated: 2026-05-30
closed: 2026-05-30
outputs: [adr-0018-skill-install-uninstall.md]
notes: >
  ADR-0018 authored and operator-ratified 2026-05-30. CLI contract (hard-stop)
  decided: review subcommand = `polyreview run`, bare `polyreview <flags>` dropped
  (pre-1.0 alpha). All 8 AC decisions (1, 1b, 2–7) recorded with rationale, no TBD.
  Prose ADR — no automated test; closure = AC checklist + operator sign-off per the
  task's own test spec. ADR co-locates in active/ until epic close.
tags: [adr, install, uninstall, packaging, cli]
---

# s6-t0 — ADR-0018: skill install/uninstall design

## Outcome

A committed `adr-0018-skill-install-uninstall.md` (co-located in
`sdlc/work/active/` per the SDLC co-location rule, `status: accepted`) that settles
the design for both `polyreview install` (s6) and `polyreview uninstall` (s7) so
the implementation tasks have no open design questions. Mirrors how ADR-0016
governs s0 and ADR-0017 governs s1.

## Acceptance criteria

### Scenario: every implementation decision is recorded
- **Given** ADR-0018
- **When** an implementer reads it before s6-t1/s6-t2/s7-t0
- **Then** each of the decisions below is stated with a rationale and no
  "TBD"/open question remains that blocks implementation.

The ADR must decide, at minimum:

1. **Target registry — agent-independent skills-dir resolution.** The bundle is an
   Agent Skills bundle consumed by many agents; there is **no single** skills dir.
   Define a registry mapping a target id → user-level skills dir:

   | id | dir | read by |
   |----|-----|---------|
   | `agents` (neutral) | `$HOME/.agents/skills/` | **Codex** (native); **Gemini CLI** (alias) |
   | `claude` | `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/` | Claude / Claude Code |
   | `copilot` | `$HOME/.copilot/skills/` | GitHub Copilot |
   | `gemini` | `$HOME/.gemini/skills/` | Gemini CLI |

   The bundle lives at `<skills-dir>/code-review/` (dir name must match SKILL.md
   `name:`). Each target honours its agent's own env override where one exists
   (`CLAUDE_CONFIG_DIR` for `claude`). Decide the **default target policy** (no
   `--agent`): recommended = neutral `agents` **plus** every agent home already
   present on the machine (auto-detect), so existing agents get native discovery
   without conjuring homes for agents the user lacks. `--agent <id[,id…]>` forces an
   explicit set; `--all` writes every registry target. Record the rationale and the
   detection rule (a home "is present" iff its base dir — `~/.claude`, `~/.copilot`,
   `~/.gemini` — exists). Resolution is `$HOME`-relative so tests stay hermetic by
   monkeypatching `$HOME` / the per-agent env vars to a tmp dir.

1b. **Create-if-missing.** A target skills dir that does not yet exist is the
   normal first-run case, not an error: install creates the full tree
   (parents included, `mkdir -p` semantics). Explicitly covers "the `.claude`
   (or `.agents`) directory does not exist yet."
2. **Bundle manifest — what is copied.** The wheel-shipped subset:
   `SKILL.md`, `code-review.toml.example`, `semgrep-rules/` (the vendored ruleset,
   ADR-0016), `package.json`, `package-lock.json`. **Not** copied: `node_modules/`,
   `cache/`, `runs/` (provisioned/produced, not shipped — they are large and
   host-specific). State the manifest as a single source of truth that s6-t1
   (wheel packaging), s6-t2 (install), and s7-t0 (uninstall guard) all read.
3. **CLI subcommand restructure.** Adding `install`/`uninstall` to the single-command
   `typer.Typer()` (`code_review/cli.py:23`, one `@app.command()` named `main`)
   turns the review run into a named subcommand. Decide the review subcommand
   spelling (e.g. `polyreview run`) and whether to preserve the bare
   `polyreview <flags>` invocation (Typer default-command / callback pattern).
   Note pre-1.0 CLI instability (README §Alpha) permits the change; record the
   chosen spelling so `SKILL.md`/README updates are unambiguous.
4. **Idempotency & `--force`.** Re-running `install` over an existing bundle is a
   reported no-op without `--force` and a clean in-place refresh with it. Define
   "in-place refresh": remove-then-copy vs. overwrite-merge, and what happens to a
   user-edited `code-review.toml` if one sits alongside (it shouldn't — the example
   is `code-review.toml.example`, but state the rule).
5. **Uninstall safety guards (governs s7).** `uninstall` mirrors the install
   registry and, **per target**, removes **only** `<skills-dir>/code-review/` and
   only when that dir looks like our bundle (a marker check — e.g. `SKILL.md` with
   the expected `name: code-review` frontmatter — so a mistargeted env var or a name
   collision can't `rmtree` an arbitrary dir). It must never touch a sibling
   `<skills-dir>/<other-skill>/`, the agent's `agents/reviewer.md` (Claude's
   reviewer sub-agent), the skills dir itself, or any agent home. Decide the marker,
   whether a confirmation prompt / `--yes` is required (tests run non-interactive),
   the no-op message when nothing is installed, and that a refusal on one target
   still reports the outcome of the others (no silent partial run).
6. **The CWD-anchored-cache seam.** `cache_root()` (`code_review/paths.py:15`)
   resolves CWD-relative `./.claude/skills/code-review`, **not** any user-level
   skills dir. Record that a user-level bundle gives agents skill *discovery* but
   does not relocate the runtime caches; the install command's closing hint points
   at cache provisioning. Mark full user-level cache relocation as deferred (out of
   epic scope) with the migration path (`POLYREVIEW_CACHE_DIR`) noted.
7. **Copy-per-target vs. symlink.** Default is an independent copy into each
   resolved skills dir. Record the symlink alternative (one canonical copy + per-agent
   symlinks; Codex follows symlinks) and why it's deferred — Windows portability and
   uninstall-guard complexity. State which the implementation uses (copy).

## Test specification

ADR is prose, not code — no automated test. Verification is the AC checklist above
plus operator sign-off on the design at plan review. The decisions become testable
contracts in s6-t1/s6-t2/s7-t0.

## Notes

This task only authors the decision record. No `cli.py`, `pyproject.toml`, or test
changes land here — those are s6-t1 onward.
