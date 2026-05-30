---
id: s6-fix2-cli-restructure-release-runbook
kind: task
project: code-review
status: active
parent: s6-install-skill-bundle
sources: [s6-fix1-review-2026-05-30, sdlc/docs/runbooks/release.md]
created: 2026-05-30
updated: 2026-05-30
tags: [fix, cli, runbook, release, propagation, round-2]
---

# s6-fix2 — propagate `polyreview run` to the live release runbook

## Source

**Round-2** fix (rule #25 final round) from the s6-fix1 per-task Review. The
s6-fix1 Review confirmed the CI workflow + guard test were corrected but found the
**live** GA release runbook still instructs the operator to run the bare
`polyreview --capabilities` form (now exit 2) at three sites — same defect class,
in scope per s6-fix1's Outcome ("no bare … invocation … remains in CI or live
developer docs").

## Outcome

`sdlc/docs/runbooks/release.md` instructs `polyreview run --capabilities` at every
live invocation, so an operator executing the GA release this chain unblocks does
not hit a confusing exit-2 failure on the manual sanity steps, and the prose
describing the `test-dist` CI job matches the corrected workflow.

## Acceptance criteria

### Scenario: runbook manual steps use the run subcommand
- **Given** `sdlc/docs/runbooks/release.md` lines 52 and 74 (TestPyPI dry-run and
  post-PyPI verify smoke commands)
- **Then** both read `polyreview run --capabilities`.

### Scenario: runbook prose describing test-dist matches the workflow
- **Given** the line-110 prose describing the `test-dist` job
- **Then** it says `polyreview run --capabilities`.

### Scenario: no live bare form remains anywhere
- **Given** a sweep of all live surfaces (code, scripts, CI, README, SKILL.md,
  AGENTS.md, CLAUDE.md, runbooks) — excluding frozen `sdlc/work/done/` and
  superseded `sdlc/docs/{architecture,decisions,strategy}/` history
- **Then** zero bare `polyreview <flags>` / `python -m code_review.cli <flags>`
  invocations that exit 2 remain. (The bundle `code-review.toml.example`
  `--help` cross-reference is exempt: `--help` resolves without a subcommand,
  exit 0 — deferred per s6-t2/s6-fix1 notes.)

## Test specification

Doc-only change; no automated test. Verification is the AC checklist plus a grep
sweep proving no live bare form remains (the AC-3 sweep). `--version` (a
top-level flag, not a review invocation) and the `--help` toml.example reference
are excluded.

## Notes

If this round-2 fix's Review surfaces a further Critical/Important finding, that is
a round-3 trigger → halt and escalate to the operator per rule #25 (do not file a
round-3 fix autonomously).
