# State — last updated 2026-05-28

**Active focus:** `epic-deployment-readiness` — s0 + s1 both closed clean. Next operator decision: which story to plan next under the epic, or whether to close the epic.
**Last completed:** Story `s1-package-publication` closed (all 6 tasks done; story-level Review MINOR-ONLY, all three Minors resolved in the close commit). `claude-code-review` is now PyPI-ready: rename + metadata + console-script entry, README/ADR-0012/release.yml/runbook all in place. First real release is the only remaining publishing-gate work, blocked on operator-side Trusted Publisher setup on PyPI + TestPyPI (one-time, off-repo).
**In flight:** Nothing — the session ended at story close.
**Next:** at session start — operator decision: (a) plan and execute the very first release (per `sdlc/docs/runbooks/release.md`), (b) tackle `s0-t6-cache-path-unification` (sibling carryover; pre-existing producer/consumer cache-path divergence; needs an architectural decision before execution), (c) plan the next s2 story under the deployment-readiness epic, or (d) close the epic if `s0-t6` is reclassified.

## Active artefacts

- `epic-deployment-readiness.md` — epic shell, still open.
- `s0-t6-cache-path-unification.md` — sibling debt under s0; needs architectural decision before execution.
- `s3-plan.md`, `s4-plan.md` — lingering plans from prior epic (not blocking).

## Done this session (2026-05-28 evening)

- `s1-t0..s1-t5` — all six s1 tasks closed clean (each Verify PASS + Review CLEAN/MINOR-ONLY; s1-t5 round-2 CLEAN after `s1-t5-fix1`).
- Mid-story: `s1` parent story refreshed (commit `d23bbb4`) to drop the API-token drift the s1-t2 reviewer surfaced; tag-prefix and console-script-name drifts swept at the same time.
- Story-level Review: MINOR-ONLY; all three Minors resolved in the close commit (runbook moved+renamed to final home; runbook scaffold test added; `release.md:30` parenthetical tightened).

## Open questions

- **First-release timing.** The runbook is ready, the workflow is committed, but the first release blocks on operator-side configuration: pending publishers on `pypi.org` and `test.pypi.org` (per `sdlc/docs/runbooks/release.md` Trusted Publishers section).
- **`s0-t6-cache-path-unification`** — still needs an architectural decision before execution. Carry-over from s0 close.
- **Lingering plans (`s3-plan.md`, `s4-plan.md`)** — still in `active/` from the prior epic; should be triaged at some point (close, archive, or replan).
- **Pre-existing mypy `conftest.py: Source file found twice`** — reproduces on all parent commits; carried through s1 unchanged. Worth a small cleanup task (likely `tests/__init__.py` or `explicit_package_bases`), but does not block any task.

## Auto-progress posture (2026-05-28, unchanged)

Per SDLC §Execute line 140 and rule #22: tasks under an operator-approved story auto-execute; Verify + Review run per task; halts only on Verify failure, Review's 2-round bound, gate escalation, hard-stop, three failed attempts, ≥75% context, or operator interruption. Story-level Review at story boundary; auto-cross into the next operator-approved story without pause.
