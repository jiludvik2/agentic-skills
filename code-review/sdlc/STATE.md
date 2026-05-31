# State — last updated 2026-05-31

**Active focus:** **EPIC `epic-analyzer-thin-runner`** (ADR-0020, stories s0–s5). **s0 + s1 DONE & pushed** (`main` @ `92d9450`). **s2 now PLANNED** (story + 4 task files written, committed locally, **awaiting operator approval** — not yet executed). Epic continues s2→s5.
**Last completed:** **Story s1** (thin-runner strangle: adapters → raw `CaptureOutput`; `polyreview run` emits `review-bundle.v1.json`; SARIF-normalisation layer deleted, −1604 LOC).
**Next:** **Approve s2 plan, then execute s2-t0.** Story `s2-skill-interpretation-and-golden-bundle` = SKILL.md per-tool interpretation guidance + golden-bundle hardening + 2 carry-overs. Tasks (execution order): **s2-t0** diff-path resolution (anchor on `git rev-parse --show-toplevel`, not `Path.cwd()`); **s2-t1** remove dead `sarif-2.1.0.json` + 3 packaging pins (operator-approved: remove); **s2-t2** recorded golden bundle + byte-equal regression guard + edge cases (operator-approved: full fixture); **s2-t3** (capstone) SKILL.md "Interpreting the bundle" section for all 12 registry analyzers + dedup-by-judgment + vulture/knip FP notes (G2/G7). On approval: auto-progress through the story, Verify+Review per task, story-level Review at boundary.

## Open questions / follow-ups
- **s2 plan awaiting approval** — committed locally, not pushed. If approved as-is, begin s2-t0. Operator may edit/re-order/split before execution.
- **Two design forks already resolved (2026-05-31):** dead SARIF schema → **remove**; golden-bundle → **recorded fixture + regression guard**. Baked into s2-t1/s2-t2 specs.
- **G2/G7 plan-time disposition:** vulture/knip FP handling folded into s2-t3 as concise inline notes (not a separate section) — keeps the runner thin (ADR-0020 guard-rail).
- **Guard-rail for the whole story:** no interpretation/ranking/dedup code re-enters `code_review/`; all guidance is SKILL.md prose.
- **Carry-over to s5:** `sdlc/docs/qa/analyzer-coverage/results/raw/*.json` are pre-ADR-0020 captures (old sarif/metrics shape) — regenerate against the raw bundle before s5 uses them.
- **`/dev/stdout` not writable under the OS sandbox** — file-output tools must use native stdout, never a `/dev/stdout` redirect.
- **CI mypy gate is package-scoped** (`uv run mypy code_review`); bare `mypy` shows pre-existing strict errors in test files outside the gate — not regressions.
