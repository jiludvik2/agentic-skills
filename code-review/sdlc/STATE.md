# State — last updated 2026-05-28

**Active focus:** `epic-deployment-readiness` — plan filed, refined, and pushed; execution pending.
**Last completed:** Commit `ab2f33a` (pushed to `origin/main`) — refined s1 plan across 7 artefacts + STATE.md: PyPI distribution name `claude-code-review`, console-script binary `claude-code-review`, release tag prefix `code-review-v*`, release auth via PyPI Trusted Publishers (OIDC). No code changes; planning-only.
**Next:** operator re-affirms approval at next session start (prior-session approval does not carry forward per SDLC §Glossary); on approval, execute `s0-t0-importlib-resources` (first task of `s0-deployment-layout-fixup`).

## Active artefacts

- `epic-deployment-readiness.md` — epic shell
- `s0-deployment-layout-fixup.md` — story; 6 tasks `s0-t0` through `s0-t5`
- `s1-package-publication.md` — story; 6 tasks `s1-t0` through `s1-t5`. Depends on s0. Refined 2026-05-28: PyPI name `claude-code-review`, console-script `claude-code-review`, tag prefix `code-review-v*`.
- `s3-plan.md`, `s4-plan.md` — lingering plans from prior epic (per project precedent; not archived)

## Open questions

- **Operator-supplied content** for `s1-t1` (README draft) — gates task close per "What stays human". (`s1-t0` authors email resolved: omitted by design.)
- **Workflow file location.** `.github/workflows/release.yml` lives at monorepo root (`agentic-skills/.github/workflows/`), outside the `code-review/` subdir — sandbox-write-blocked path for Claude; `s1-t3` notes the operator may need to apply the file directly.
- **Lingering plans (`s3-plan.md`, `s4-plan.md`)** still in `active/` from the prior epic. Not blocking; sweep or leave is an operator call.
- **`intent-review` sibling project.** Bootstrap is a separate session; requirements at `/sdlc/docs/strategy/intent-review-requirements.md`. When it lands, the monorepo-root workflow will need a parallel `intent-review-v*` tag pattern (separate workflow file with its own Trusted Publisher binding, or a matrixed branch).
- **Supply-chain gate.** Rule #26 N/A; could be formalised in a future story under this or a separate epic.

## Resolved during epic review (2026-05-28)

- **PyPI distribution name** = `claude-code-review` (bare `code-review` is taken on PyPI; checked by operator).
- **Console-script binary name** = `claude-code-review` (renamed from `code-review` to avoid `$PATH` collisions with the existing PyPI `code-review` package).
- **Python import name** = `code_review` (unchanged; `python -m code_review.cli …` still works from source checkouts).
- **Release tag prefix** = `code-review-v*` (e.g., `code-review-v0.1.0`, `code-review-v0.1.0-rc1`) — disambiguates this subproject from any future sibling subproject sharing the monorepo's `.github/workflows/`.
- **Release auth** = **PyPI Trusted Publishers (OIDC)**. No long-lived secrets in the GitHub repo. One-time PyPI-side setup: pending publishers on PyPI and TestPyPI bind to repo `jiludvik2/agentic-skills`, workflow filename `release.yml`. Workflow grants `permissions: id-token: write` on the publish job; `uv publish` discovers the OIDC token automatically.
