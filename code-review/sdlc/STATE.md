# State — last updated 2026-05-29

**Active focus:** `epic-deployment-readiness` — s0, s1, s2 all closed clean. Next operator decision: cut the first real release, tackle `s0-t6-cache-path-unification` (sibling carryover), or close the epic.
**Last completed:** Story `s2-packaging-hardening` closed (all 6 tasks done; story-level Review MINOR-ONLY, all six Minors resolved in the close commit). Packaging is now at current PyPA best practice: LICENSE bundled in the wheel; runtime deps lower-bounded (ADR-0013 supersedes ADR-0003 §1 for runtime; dev stays exact-pinned); `__version__` single-sourced via `importlib.metadata`; release workflow restructured into build → test-dist → publish with OIDC scoped to publish and the official PyPA action; CI workflow added (pytest+ruff+mypy on push+PR with `code-review/**` + workflow path filter); SKILL.md leads with the installed binary; setup.sh's BUNDLE_DIR finds the example config.
**In flight:** Nothing — the session ended at story close.
**Next:** at session start — operator decision: (a) plan and execute the very first release (per `sdlc/docs/runbooks/release.md`, now describing the post-s2-t3 three-job topology); (b) tackle `s0-t6-cache-path-unification` (sibling carryover; pre-existing producer/consumer cache-path divergence; needs an architectural decision before execution); (c) plan a new story (e.g., supply-chain audit gate, GH-Actions SHA-pinning ADR, the deferred `--version` CLI flag); (d) close the epic.

## Active artefacts

- `epic-deployment-readiness.md` — epic shell, still open; children list now includes s2.
- `s0-t6-cache-path-unification.md` — sibling debt under s0; needs architectural decision before execution.
- `s3-plan.md`, `s4-plan.md` — lingering plans from prior epic (not blocking).

## Done this session (2026-05-29 morning)

- `s2-t0..s2-t5` — all six s2 tasks closed clean. Per-task verdicts:
  - s2-t0 (LICENSE bundling): Verify PASS, Review MINOR-ONLY (3 resolved in close).
  - s2-t1 (relax dep pins): round-1 Critical (ADR-0003 contradiction) + Important (unbounded schemathesis) remediated via `s2-t1-fix1` (operator-approved ADR-supersede path); round-2 MINOR-ONLY (resolved).
  - s2-t2 (importlib.metadata version): Verify PASS, Review MINOR-ONLY (4 resolved).
  - s2-t3 (release workflow): Verify PASS, Review MINOR-ONLY (4 resolved).
  - s2-t4 (CI workflow): Verify PASS, Review MINOR-ONLY (3 resolved).
  - s2-t5 (SKILL.md + setup.sh): Verify PASS, Review MINOR-ONLY (2 resolved).
- **New ADR**: ADR-0013-runtime-vs-dev-dependency-pinning, partially superseding ADR-0003 §1 for runtime deps. ADR-0003 status block updated to record the partial supersede. `stack-pins.md` §"Python dependencies" reworked to show spec floor + locked patch columns; §"Pinning policy" rewritten as split policy citing both ADRs.
- Story-level Review on `42045ba..24bc6e8` (13 commits): MINOR-ONLY, 6 Minor + 1 Nit. All six Minors resolved in close commit: architecture doc §10.2 cites ADR-0013 split; epic out-of-scope line replaced with split-policy phrasing; epic Stories list gains s2 entry; SKILL.md stale "not yet published" parenthetical replaced; ADR-0013 moved active/ → docs/decisions/; story file moved active/ → done/. Nit (README "once the flag lands" phrasing) dropped — intentional and self-documenting.
- Test count grew from 304 to 326 (+22 across the story): 3 new pyproject metadata assertions (license file form + byte-equality + runtime dep contracts), 1 new wheel test (LICENSE in dist-info), 3 new version-source tests, 9 new release-workflow tests, 8 new CI-workflow tests, 3 new SKILL.md invocation tests, 2 new setup.sh BUNDLE_DIR tests, minus 2 replaced anchor tests.

## Open questions

- **First-release timing.** The runbook is ready (post-s2-t3 three-job topology), the workflows are committed and tested structurally, but the first real release still blocks on operator-side configuration: pending publishers on `pypi.org` and `test.pypi.org`, plus GitHub `pypi` and `testpypi` environments (per `sdlc/docs/runbooks/release.md` Trusted Publishers section; environment names are now required after s2-t3 added them to the workflow). `release.md`'s frontmatter `verified-on: null` stays null until the first real tag ships.
- **`s0-t6-cache-path-unification`** — still needs an architectural decision before execution. Carry-over from s0 close.
- **Lingering plans (`s3-plan.md`, `s4-plan.md`)** — still in `active/` from the prior epic; should be triaged.
- **Pre-existing mypy `conftest.py: Source file found twice`** — reproduces on all parent commits; carried through s2 unchanged.
- **Deferred follow-ups identified during s2** (low-priority): a `--version` CLI flag (currently absent — README documents the `python -c` fallback); a GH-Actions pinning ADR (release.yml and ci.yml use major-tag-pinned actions; not covered by ADR-0003 or ADR-0013); a CHANGELOG.md; root `agentic-skills/README.md` still missing the `code-review` row.

## Auto-progress posture (2026-05-29, unchanged)

Per SDLC §Execute and rule #22: tasks under an operator-approved story auto-execute; Verify + Review run per task; halts only on Verify failure, Review's 2-round bound, gate escalation, hard-stop, three failed attempts, ≥75% context, or operator interruption. Story-level Review at story boundary; auto-cross into the next operator-approved story without pause.
