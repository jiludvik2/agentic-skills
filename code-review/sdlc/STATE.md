# State — last updated 2026-05-29

**Active focus:** `epic-deployment-readiness` — s0, s1, s2, s3 all closed. Epic substantively complete; first PyPI release is the remaining operator-side step.
**Last completed:** `s3-multi-agent-rename` closed (commits `7dba060`/`b15bbda`/`215a2ab`/`0c63b94`; story-level Review MINOR-ONLY, all resolved). Dist + binary renamed `claude-code-review` → `polyreview`; AGENTS.md added; CLAUDE.md → redirect. Import name `code_review`, skill bundle path, and `code-review-v*` tag prefix kept (ADR-0014).
**Next:** operator decision — (a) close the epic (`document` README reconcile + rule-#18 publication verify), (b) cut the first release under `polyreview`, or (c) `s0-t6-cache-path-unification`.

## Open questions

- **First release under `polyreview`.** Operator created the `polyreview` PyPI + TestPyPI projects + Trusted Publishers. Rename has landed, so the build now produces a `polyreview` wheel matching the publisher. The rc tag `code-review-v0.1.0-rc1` on origin points at the PRE-rename commit `e99e323` — delete + re-cut it on current `main` (HEAD `0c63b94`) so the workflow builds `polyreview==0.1.0rc1`. Earlier the tag push did NOT trigger the release workflow (zero runs) — re-push as a standalone tag event to fire it.
- **CI failing on `main`** (pre-existing; the only run is a CI `failure`). Independent of `release.yml`; investigate separately.
- **`s0-t6-cache-path-unification`** — 3 adapters hardcode `.claude/skills/code-review/cache/...`; gains urgency now `polyreview` targets non-Claude agents.
- **`claude-code-review` redirect meta-package** — deferred; publish once `polyreview` is live (ADR-0014; runbook Rename history).
- **Pre-existing mypy `conftest.py: Source file found twice`** when mypy points at `tests/` — carried unchanged.

## Epic boundary

All 4 stories (s0–s3) of `epic-deployment-readiness` closed. Per SDLC the loop paused here for the operator to decide epic-close vs first-release vs next work; auto-progress did NOT cross into unplanned work.
