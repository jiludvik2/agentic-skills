# State — last updated 2026-05-28

**Active focus:** `epic-deployment-readiness` — story `s0-deployment-layout-fixup` mid-execution; tasks s0-t0..s0-t2 closed clean.
**Last completed:** `s0-t2-cwd-relative-toml` — CWD-relative `code-review.toml` lookup + `--config` flag; `_SKILL_DIR` fully removed from `code_review/` (scope-expanded to trivy + js_base cache helpers per operator OK 2026-05-28). 281 tests pass; ruff + mypy clean. Verify PASS; Review HAS-CRITICAL-OR-IMPORTANT (1 Important re cache-path producer/consumer alignment) — Important deferred per operator decision to new task `s0-t6-cache-path-unification` (pre-existing latent divergence, not a regression).
**Next:** auto-progress into `s0-t3-production-layout-smoke` per rule #22.

## Active artefacts

- `epic-deployment-readiness.md` — epic shell
- `s0-deployment-layout-fixup.md` — story; s0-t0..s0-t2 closed; s0-t3..s0-t5 remaining; s0-t6 newly filed (architectural follow-up).
- `s0-t3-production-layout-smoke.md`, `s0-t4-cleanup-and-docs.md`, `s0-t5-toml-starter-template.md` — remaining planned tasks.
- `s0-t6-cache-path-unification.md` — new, filed 2026-05-28 in lieu of a fix task against s0-t2.
- `s1-package-publication.md` — story plan; depends on s0.
- `s1-t0..s1-t5` — s1 tasks (not yet started).
- `s3-plan.md`, `s4-plan.md` — lingering plans from prior epic (not blocking).

## Open questions

- **Operator-supplied content** for `s1-t1` (README draft) — still pending.
- **Workflow file location** for `.github/workflows/release.yml` — monorepo root, sandbox-write-blocked; `s1-t3` notes operator may need to apply directly.
- **Lingering plans (`s3-plan.md`, `s4-plan.md`)** still in `active/` from the prior epic.
- **Cache-path unification (`s0-t6`)** — needs architectural decision on cache contract across the three supported layouts (dev sibling, production nested, wheel-installed-no-producer). Possibly an ADR.
- **Supply-chain gate.** Rule #26 N/A; could be formalised in a future story.

## Resolved during epic execution

- **PyPI distribution name** = `claude-code-review`; **Console-script** = `claude-code-review`; **Python import** = `code_review`; **Release tag prefix** = `code-review-v*`; **Release auth** = PyPI Trusted Publishers (OIDC).
- **s0-t2 scope expansion** (2026-05-28): `_SKILL_DIR` removal extended to `adapters/trivy.py` and `adapters/js_base.py`; cache helpers now use CWD-relative `Path.cwd() / ".claude" / "skills" / "code-review" / ...` idiom matching `code-review.toml`. Producer/consumer alignment deferred to `s0-t6`.

## Auto-progress posture (2026-05-28)

Confirmed mid-session: per SDLC §Execute line 140 and rule #22, tasks under an operator-approved story auto-execute (no per-task approval ask); halts only on Verify failure, Review's 2-round bound, gate escalation, hard-stop, three failed attempts, ≥75% context, or operator interruption. Verify + Review run **per task** before move-to-done.
