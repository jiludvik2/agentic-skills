# State — last updated 2026-05-28

**Active focus:** s5 — **replanned**. Phase 1 (design capture) ✅; Phase 2 (implementation, tests-first) is next.
**Last completed:** Phase 1 of the s5 replan — wrote ADR-0010 (two-skill split), ADR-0011 (review-selection model), the new `s5-review-selection-scheme` story (extended with Combinations + Validation subsections — 22 ACs), and the `intent-review-requirements` handoff doc. Old s5 (`s5-subagent-integration-and-design-review`) retired in place and moved to `done/` with a retirement marker.
**Next:** Phase 2 — implement review-selection tests-first: per-analyzer `domain`/`subcategory`/`tier` tags in `capabilities.json` (+ schema), replace orphaned `--review-scope` with `--review`/`--depth` in `cli.py` per the precedence in `s5-review-selection-scheme.md` (incl. case-insensitive normalization, redundancy warnings to stderr, contradictory-`--depth` resolves to simpler), tests for all 22 ACs, SKILL.md taxonomy docs, green bar.

## s5 replan — what shipped in Phase 1

The original s5 (a unified reviewer sub-agent doing CLI invocation + LLM design review + dedup/routing) was retired during design. It split along the deterministic/probabilistic seam:

- **`code-review`** (this subdir) → standalone deterministic skill; no LLM inside; tests-first pytest-able. The new s5 scopes the remaining `code-review` work: the review-selection scheme.
- **`intent-review`** (new sibling subdir under `agentic-skills/`, separate project) → probabilistic LLM-based review skill, emits findings in the **same SARIF + sdlc_severity format** as `code-review`. Independent — no cross-skill aggregation/dedup. Bootstrapped in a separate session; requirements in `sdlc/docs/strategy/intent-review-requirements.md` Part A.
- **Consumer / integration** → explicitly out of scope. A future LLM that reads both skills' outputs and dedups by judgment + routes fix-tasks per rule #25. Requirements in `intent-review-requirements.md` Part B.

Architecture §8 (unified-reviewer) and ADR-0004 (three-review-scopes) are superseded.

## s5 replan — remaining phases

- **Phase 2** — implement review-selection (tests-first): capabilities tags + schema + CLI flags; SKILL.md docs; green bar. Drops orphaned `--review-scope`; eslint drops its `security` rule_class (kept as `quality`).
- **Phase 3** — split clean-cut: remove the bundled consumer from `code-review` (`agents/reviewer.md`, `setup.sh`'s reviewer-install step, the reviewer-content/setup-install tests, integration prose in SKILL.md) — content already captured in the handoff.
- **Phase 4** — close the epic + reconcile: rewrite epic to deterministic-only + close; move ADRs → `docs/decisions/`, architecture → `docs/architecture/` (§8 superseded), stories → `done/`; refresh STATE.

## Open questions / known debt

- `--capabilities` output still has no schema; `analyzers` key shape differs from review-response (deferred from s0/s1).
- `code-review.toml` read from skill dir (`_SKILL_DIR` in cli.py); ADR-0007 defers CWD-relative decision.
- Ruff is part of per-task green-bar; verifier/reviewer sub-agents still don't run it — run locally every task.
- Architecture doc retains Pact prose (light supersede per ADR-0008) and §8 unified-reviewer prose (now superseded by ADR-0010) — full purge handled at epic close (Phase 4).
- **s4 deferred Minor #5** (orphaned `--review-scope`) is resolved by Phase 2 (replaced by `--review`/`--depth`). Minor #4 (adapter multi-target hard-return) still open.
- **Supply-chain:** no formal gate defined (rule #26 N/A). pytest 8.3.4 / CVE-2025-71176 allow-listed until 2026-08-31 (blocked by `schemathesis==4.0.10` pinning `pytest<9`); consider an audit-gate ADR + pytest/schemathesis bump in a later story.
- **Housekeeping:** s3-plan.md and s4-plan.md linger in `active/` (plans aren't archived to `done/` per project precedent); s3 story/tasks were never moved to `done/` after s3 completed — pre-existing. Phase 4 may sweep these.
