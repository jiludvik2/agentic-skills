---
id: s6-fix1-cli-restructure-release-pipeline
kind: task
project: code-review
status: done
parent: s6-install-skill-bundle
sources: [s6-story-level-review-2026-05-30, .github/workflows/release.yml, tests/test_release_workflow.py, AGENTS.md]
created: 2026-05-30
updated: 2026-05-30
closed: 2026-05-30
notes: >
  Fixed release.yml:79 (polyreview run --capabilities under pipefail),
  test_release_workflow.py guard (red→green, now asserts the run form + retains
  claude-code-review-absent), AGENTS.md:15 source-checkout note. Verify PASS.
  Review HAS-IMPORTANT → spawned ROUND-2 fix s6-fix2 (live runbook
  sdlc/docs/runbooks/release.md still had the bare form at 3 sites). Minor
  (toml.example --help, exit 0) deferred. Round-2 is the final allowed round
  (rule #25); a further Critical/Important on s6-fix2 review → escalate.
tags: [fix, cli, ci, release, propagation]
---

# s6-fix1 — propagate the `polyreview run` restructure to the release pipeline

## Source

Round-1 fix from the s6 story-level Review (2026-05-30). **Important** finding:
the s6-t2 CLI restructure (`polyreview <flags>` → `polyreview run <flags>`,
ADR-0018 §3) propagated to SKILL.md/README but **not** to the release pipeline.

## Outcome

The GA release smoke gate invokes the working `polyreview run --capabilities`
form, its structural guard test asserts the same, and the source-checkout
developer note in `AGENTS.md` matches SKILL.md. No bare `polyreview <flags>` /
`python -m code_review.cli <flags>` invocation that now exits 2 remains in CI or
live developer docs.

## Acceptance criteria

### Scenario: release smoke step uses the run subcommand
- **Given** `.github/workflows/release.yml` `test-dist` job (runs under
  `set -euo pipefail`)
- **When** it smoke-tests the installed binary
- **Then** it invokes `polyreview run --capabilities` (exit 0), not the bare form
  (which Typer now rejects with exit 2, failing the pipefail'd step).

### Scenario: the guard test pins the corrected form
- **Given** `tests/test_release_workflow.py::test_test_dist_smoke_invokes_renamed_binary`
- **Then** it asserts `polyreview run --capabilities` is present in the run blocks
  (and still asserts the old `claude-code-review` name is absent).

### Scenario: AGENTS.md developer note matches SKILL.md
- **Given** `AGENTS.md` source-checkout fallback line
- **Then** it reads `python -m code_review.cli run --capabilities`, consistent with
  SKILL.md's Developer note.

## Test specification

Write/adjust the test first, confirm red against the current workflow, then fix.

1. Update `test_test_dist_smoke_invokes_renamed_binary` to expect
   `polyreview run --capabilities`. Run it → **red** (current release.yml has the
   bare form). Then edit `release.yml:79` to `polyreview run --capabilities` → green.
2. (No automated test for AGENTS.md prose — corrected by inspection; the existing
   `tests/test_skill_md_invocation.py` already guards SKILL.md.)

## Notes

- Deferred from this fix (recorded, not blocking): the bundle-shipped
  `code-review.toml.example` cross-references `python -m code_review.cli --help`
  (Minor, still exit 0 — `--help` resolves without a subcommand); and `--force`
  atomicity + the mixed-`--all`-refusal cache-hint, both deferred in s6-t2 notes.
