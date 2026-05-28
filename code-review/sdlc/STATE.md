# State — last updated 2026-05-28

**Active focus:** `epic-deployment-readiness` — plan filed and fully refined, execution pending. SDLC v6.6 landed (Wrap verb, context-pressure halt, auto-Wrap on halts) and installed at project `.claude/skills/sdlc/`.
**Last completed:** Plan refinement during epic review — resolved (1) PyPI distribution name (`claude-code-review`; bare `code-review` is taken), (2) console-script binary name (`claude-code-review` — renamed from `code-review` to avoid `$PATH` collisions), (3) workflow tag pattern (`code-review-v*` prefix so the monorepo-root workflow only fires for this subproject), (4) release auth (**PyPI Trusted Publishers / OIDC** — no long-lived secrets; one-time pending-publisher setup on PyPI and TestPyPI). Edits applied across `s1-package-publication.md`, `s1-t0`, `s1-t1`, `s1-t2`, `s1-t3`, `s1-t4`, `s1-t5`. SDLC skill bundle still installed at `code-review/.claude/skills/sdlc/`.
**Next:** operator approves the refined plan; on approval, execute `s0-t0-importlib-resources` (first task of `s0-deployment-layout-fixup`).

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
