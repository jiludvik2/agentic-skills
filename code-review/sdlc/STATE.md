# State — last updated 2026-05-28

**Active focus:** `epic-deployment-readiness` — plan filed, execution pending. SDLC v6.6 landed (Wrap verb, context-pressure halt, auto-Wrap on halts) and installed at project `.claude/skills/sdlc/`.
**Last completed:** Installed SDLC skill bundle at `code-review/.claude/skills/sdlc/` — SKILL.md, references/SDLC.md (v6.6), references/verifier.md, references/reviewer.md. Project-scoped skill takes precedence over the canonical user-level skill (still at v6.4); the repo now carries its own v6.6 SDLC bundle.
**Next:** operator reviews / edits the deployment-readiness plan; on approval, execute `s0-t0-importlib-resources` (first task of `s0-deployment-layout-fixup`).

## Active artefacts

- `epic-deployment-readiness.md` — epic shell
- `s0-deployment-layout-fixup.md` — story; 6 tasks `s0-t0` through `s0-t5`
- `s1-package-publication.md` — story; 6 tasks `s1-t0` through `s1-t5`. Depends on s0.
- `s3-plan.md`, `s4-plan.md` — lingering plans from prior epic (per project precedent; not archived)

## Open questions

- **Operator-supplied content** for `s1-t1` (README draft) — gates task close per "What stays human". (`s1-t0` authors email resolved: omitted by design.)
- **PyPI Trusted Publishers (OIDC) vs token-based** — offered during s1-t0 review; not yet decided. Default in `s1-t3` is token-based. Trusted Publishers removes long-lived secrets but adds a one-time PyPI-side trust-relationship setup. Revisit at s1-t3 execution.
- **PyPI name availability** for `code-review`. If taken, rename procedure documented in `s1-package-publication.md` Open Questions; first action of `s1-t0` is to confirm availability.
- **Workflow file location.** `.github/workflows/release.yml` lives at monorepo root (`agentic-skills/.github/workflows/`), outside the `code-review/` subdir — `s1-t3` flags this; may need operator file-system action if Claude's write path is blocked.
- **Lingering plans (`s3-plan.md`, `s4-plan.md`)** still in `active/` from the prior epic. Not blocking; sweep or leave is an operator call.
- **`intent-review` sibling project.** Bootstrap is a separate session; requirements at `/sdlc/docs/strategy/intent-review-requirements.md`.
- **Supply-chain gate.** Rule #26 N/A; could be formalised in a future story under this or a separate epic.
