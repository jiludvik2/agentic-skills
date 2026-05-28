# State — last updated 2026-05-28

**Active focus:** `epic-deployment-readiness` — story `s0` closed; auto-crossing into `s1-package-publication` per rule #22.
**Last completed:** Story `s0-deployment-layout-fixup` — all 6 planned tasks (s0-t0..s0-t5) + 1 story-level Review fix (`s0-fix3`) closed clean. Story-level Review verdict: HAS-CRITICAL-OR-IMPORTANT (1 Important re semgrep.py sibling-layout regression). Important remediated via s0-fix3 (round-2 Review: CLEAN). 289 tests pass; ruff + mypy clean. The skill now works across dev sibling, production nested, and wheel-installed layouts; ADR-0007 closed with addendum.
**Next:** s1-package-publication is operator-approved → auto-progress to `s1-t0-project-metadata` per rule #22. Pending operator inputs to surface during s1: README content (s1-t1) and PyPI Trusted Publishers setup outside the repo.

## Active artefacts

- `epic-deployment-readiness.md` — epic shell
- `s1-package-publication.md` — story; depends on s0 (now done). s1-t0..s1-t5 ready for auto-progress.
- `s1-t0..s1-t5` — six s1 tasks, not yet started.
- `s0-t6-cache-path-unification.md` — sibling debt under s0's parent story, carried over per operator decision (B at story boundary). Pre-existing producer/consumer cache-path divergence between `scripts/setup.sh` and the trivy/js_base/semgrep adapters. Needs architectural decision before execution.
- `s3-plan.md`, `s4-plan.md` — lingering plans from prior epic (not blocking).

## Open questions

- **Operator-supplied content** for `s1-t1` (README draft) — gates task close per "What stays human".
- **PyPI Trusted Publishers** setup (one-time, off-repo) — needed before `s1-t3` (release workflow) can publish; recorded in s1-t5 runbook.
- **Workflow file location** for `.github/workflows/release.yml` — at monorepo root (`agentic-skills/.github/workflows/`), sandbox-write-blocked; `s1-t3` notes operator may need to apply directly.
- **Cache-path unification (`s0-t6`)** — needs architectural decision on cache contract across the three supported layouts (dev sibling, production nested, wheel-installed-no-producer). Possibly an ADR.
- **Supply-chain gate (rule #26)** — N/A for now; no `pip-audit`-style target defined. Could be formalised in a future epic, especially relevant once we ship to PyPI.
- **Lingering plans (`s3-plan.md`, `s4-plan.md`)** still in `active/` from the prior epic.

## Resolved during epic execution

- **PyPI distribution name** = `claude-code-review`; **Console-script** = `claude-code-review`; **Python import** = `code_review`; **Release tag prefix** = `code-review-v*`; **Release auth** = PyPI Trusted Publishers (OIDC).
- **s0-t2 scope expansion** (2026-05-28): `_SKILL_DIR` removal extended to `adapters/trivy.py` and `adapters/js_base.py`; cache helpers now use CWD-relative `Path.cwd() / ".claude" / "skills" / "code-review" / ...` idiom matching `code-review.toml`. Producer/consumer alignment deferred to `s0-t6`.
- **s0 story boundary** (2026-05-28): operator chose option B (close with carryover) — story-level Review run, Important remediated via s0-fix3, story closed; s0-t6 stays in `active/` as sibling debt. Auto-crossing into s1 (operator-approved plan exists).

## Auto-progress posture (2026-05-28)

Per SDLC §Execute line 140 and rule #22: tasks under an operator-approved story auto-execute (no per-task approval ask); halts only on Verify failure, Review's 2-round bound, gate escalation, hard-stop, three failed attempts, ≥75% context, or operator interruption. Verify + Review run per task before move-to-done. Story-level Review runs at story boundary; auto-cross into the next operator-approved story without pause.
