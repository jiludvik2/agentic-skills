---
id: s6-t0-adr-install-uninstall
kind: task
project: code-review
status: active
parent: s6-install-into-claude
sources: [sdlc/docs/qa/analyzer-coverage/FINDINGS.md, .claude/skills/code-review/SKILL.md, code_review/paths.py, pyproject.toml]
created: 2026-05-30
updated: 2026-05-30
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

1. **Target-dir resolution.** Install/uninstall resolve the config dir as
   `CLAUDE_CONFIG_DIR` if set, else `~/.claude` (`Path.home() / ".claude"`); the
   bundle lives at `<config>/skills/code-review/`. Rationale: matches Claude Code's
   own config-dir convention and keeps tests hermetic (point the env at a tmp dir).
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
5. **Uninstall safety guards (governs s7).** `uninstall` removes **only**
   `<config>/skills/code-review/` and only when it looks like our bundle (a marker
   check — e.g. `SKILL.md` with the expected `name:` frontmatter — so a mistargeted
   env var can't `rmtree` an arbitrary dir). It must never touch
   `<config>/agents/reviewer.md`, sibling skills, or `<config>` itself. Decide the
   marker, whether a confirmation prompt / `--yes` is required, and the no-op
   message when nothing is installed.
6. **The CWD-anchored-cache seam.** `cache_root()` (`code_review/paths.py:15`)
   resolves CWD-relative `./.claude/skills/code-review`, **not** the user-level
   install target. Record that a user-level bundle gives agents skill *discovery*
   but does not relocate the runtime caches; the install command's closing hint
   points at cache provisioning. Mark full user-level cache relocation as deferred
   (out of epic scope) with the migration path (`POLYREVIEW_CACHE_DIR`) noted.

## Test specification

ADR is prose, not code — no automated test. Verification is the AC checklist above
plus operator sign-off on the design at plan review. The decisions become testable
contracts in s6-t1/s6-t2/s7-t0.

## Notes

This task only authors the decision record. No `cli.py`, `pyproject.toml`, or test
changes land here — those are s6-t1 onward.
