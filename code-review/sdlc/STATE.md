# State — last updated 2026-05-28

**Active focus:** `epic-deployment-readiness` — s0 closed; s1 in progress (s1-t0 implementation committed, pending Verify+Review).
**Last completed:** Story `s0-deployment-layout-fixup` closed clean (all 6 planned tasks + 1 story-level Review fix `s0-fix3`). 299 tests pass; ruff + mypy clean. Skill now works across dev sibling, production nested, and wheel-installed layouts; ADR-0007 closed with addendum; `_SKILL_DIR` fully removed from `code_review/`.
**In flight:** `s1-t0-project-metadata` — code is committed (commit `<head-1>`: pyproject.toml rename to `claude-code-review`, console script renamed, authors/readme/urls/classifiers/keywords added; README.md stub; 10-test metadata suite). **Verify and Review are NOT yet run; task file still `status: active`**. Next-session-start must run Verify+Review on the s1-t0 commit before moving the task to `done/`.
**Next:** at session start — run Verify+Review on s1-t0; if PASS+CLEAN/MINOR-ONLY, close it and auto-progress to `s1-t1-readme-draft` (which needs operator-supplied content per "What stays human").

## Active artefacts

- `epic-deployment-readiness.md` — epic shell
- `s1-package-publication.md` — story; s1-t0 mid-task; s1-t1..s1-t5 pending
- `s1-t0-project-metadata.md` — IMPLEMENTATION COMMITTED, awaiting Verify+Review
- `s1-t1..s1-t5` — five s1 tasks not yet started; s1-t1 needs operator-supplied README content
- `s0-t6-cache-path-unification.md` — sibling debt under s0; pre-existing producer/consumer cache-path divergence; needs architectural decision before execution
- `s3-plan.md`, `s4-plan.md` — lingering plans from prior epic (not blocking)

## Open questions

- **Operator-supplied content** for `s1-t1` (README draft) — gates task close per "What stays human". A non-opinionated stub README.md was created during s1-t0 so the build doesn't fail; s1-t1 replaces it with the real content.
- **PyPI Trusted Publishers** setup (one-time, off-repo) — needed before `s1-t3` (release workflow) can publish; recorded in s1-t5 runbook.
- **Workflow file location** for `.github/workflows/release.yml` — at monorepo root (`agentic-skills/.github/workflows/`), sandbox-write-blocked; `s1-t3` notes operator may need to apply directly.
- **Cache-path unification (`s0-t6`)** — architectural decision pending across the three deployment layouts.
- **Supply-chain gate (rule #26)** — N/A for now; relevant when shipping to PyPI.
- **Lingering plans (`s3-plan.md`, `s4-plan.md`)** still in `active/` from the prior epic.

## Resolved this session (2026-05-28 afternoon → evening)

- **Auto-progress posture clarified mid-session.** Per SDLC §Execute line 140 and rule #22: tasks under an operator-approved story auto-execute (no per-task approval ask); Verify + Review run per task before move-to-done. I had been asking for per-task approval AND skipping Verify+Review — exactly inverted. Corrected and re-ran Verify+Review retroactively on s0-t0..s0-t5; all closed clean.
- **Story-level Review on s0** caught one Important (`semgrep.py:20-28` still used `Path(__file__)` sibling-layout arithmetic); remediated via `s0-fix3` (round-2 Reviewer CLEAN).
- **s0-t2 scope expansion** (operator-approved): `_SKILL_DIR` removal extended to trivy/js_base cache helpers using CWD-relative idiom.
- **s0 story boundary** (operator-approved option B): close with `s0-t6-cache-path-unification` as sibling carryover; auto-cross into s1.
- **s1-t0**: PyPI distribution name `claude-code-review`, console script renamed, author email omitted by design, full metadata for a polished PyPI page. README.md stub holding for s1-t1's full content.

## Auto-progress posture (2026-05-28)

Per SDLC §Execute line 140 and rule #22: tasks under an operator-approved story auto-execute; Verify + Review run per task; halts only on Verify failure, Review's 2-round bound, gate escalation, hard-stop, three failed attempts, ≥75% context, or operator interruption. Story-level Review at story boundary; auto-cross into the next operator-approved story without pause.
