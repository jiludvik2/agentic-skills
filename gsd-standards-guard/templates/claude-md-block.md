## Standards enforcement

**Code review is the enforcement point.** When reviewing a change, treat
`docs/ARCHITECTURE.md` (invariants + standing-rule ledger), `docs/STANDARDS.md`,
and the standing rules in `docs/adr/index.yaml` whose globs match the files you
are changing as **binding**. Apply those rules — you need not read the full ADR
corpus. Any code that contradicts a rule is a finding; cite the source (e.g.
*"violates ADR-024 — view DDL must run at the composition root, not in a
repository"*). Open `docs/adr/<NNN>-*.md` only when a rule is ambiguous for the
change. Do not infer rules beyond these documents; they define the standard.

The `gsd-standards-guard` PreToolUse hook injects the matching rules into the
GSD code-reviewer automatically; this block is the backstop for the main-agent
path. Run `/standards-audit` for a whole-codebase sweep and `/write-adr` to
record a new decision.
