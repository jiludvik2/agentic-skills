# State — last updated 2026-05-26

**Active focus:** s1 (reviewer skill packaging) complete and closed — all tasks (t0, t0-fix1, t1, t2, t3, t3-fix1, t4) + story-level fix (s1-fix1) in done/. Story-level review remediated (2 Important: --review-scope wiring, --output parent dir), reviewer CLEAN. 74/74 non-integration GREEN; ruff + mypy strict clean.

**Last completed:** `s1-reviewer-skill-and-capabilities` — skill scaffold + SKILL.md + contract schemas, capabilities.json, --capabilities runtime introspection, setup.sh installer, scope-aware bundled reviewer.md. `--review-scope` now flows into the request; `--output` creates its parent dir.

**Next:** `s2-aggregator-and-severity-mapping` — UNPLANNED. Proposed task plan awaiting operator approval (see chat). Plan approval stays human (SDLC rule #22).

## Open questions
- s2 plan needs operator approval before execution (unplanned next story → pause).
- Ruff is now part of the per-task green-bar (was missed in s0/s1 → 40 violations cleared mid-s1; see memory feedback-run-ruff-in-green-bar). Verifier/reviewer sub-agents still don't run ruff — keep running it locally.
- Known deferred debt (noted in done artefacts): --capabilities output lacks a schema + `analyzers` key shape differs from review-response; `_SKILL_DIR` sibling-path assumption breaks for a wheel install; semgrep integration test needs the binary on PATH (sandbox-gated).
