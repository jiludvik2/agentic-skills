# State — last updated 2026-05-28

**Active focus:** `epic-deployment-readiness` — make the skill redistributable. Plan filed; execution pending operator approval.
**Last completed:** Plan filed for `epic-deployment-readiness`: epic shell + 2 stories (`s0-deployment-layout-fixup`, `s1-package-publication`) + 12 task files. Total: 15 new artefacts in `/sdlc/work/active/`. Locked design choices: `importlib.resources` for package data; CWD-relative `code-review.toml` + `--config` flag; PyPI registry; GitHub Actions on tag push; semver with manual bumps.
**Next:** operator reviews / edits the plan; on approval, execute `s0-t0-importlib-resources` (first task).

## Active artefacts

- `epic-deployment-readiness.md` — epic shell
- `s0-deployment-layout-fixup.md` — story; 6 tasks `s0-t0` through `s0-t5`
- `s1-package-publication.md` — story; 6 tasks `s1-t0` through `s1-t5`. Depends on s0.
- `s3-plan.md`, `s4-plan.md` — lingering plans from prior epic (per project precedent; not archived)

## Open questions

- **Operator-supplied content** for `s1-t0` (authors email) and `s1-t1` (README draft). Both gate task close per "What stays human".
- **PyPI name availability** for `code-review`. If taken, rename procedure documented in `s1-package-publication.md` Open Questions; first action of `s1-t0` is to confirm availability.
- **Workflow file location.** `.github/workflows/release.yml` lives at monorepo root (`agentic-skills/.github/workflows/`), outside the `code-review/` subdir — `s1-t3` flags this; may need operator file-system action if Claude's write path is blocked.
- **Lingering plans (`s3-plan.md`, `s4-plan.md`)** still in `active/` from the prior epic. Not blocking; sweep or leave is an operator call.
- **`intent-review` sibling project.** Bootstrap is a separate session; requirements at `/sdlc/docs/strategy/intent-review-requirements.md`.
- **Supply-chain gate.** Rule #26 N/A; could be formalised in a future story under this or a separate epic.
