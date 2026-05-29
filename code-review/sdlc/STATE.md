# State — last updated 2026-05-29

**Active focus:** `epic-deployment-readiness` — s0, s1, s2 closed. **s3-multi-agent-rename drafted but NOT YET APPROVED** (status: `proposed` in `/sdlc/work/active/`). Operator has approved the three design decisions inside it; story plan itself is the gate to execution.
**Last completed:** Story `s2-packaging-hardening` closed (commit `0279c9c`; story-level Review MINOR-ONLY, all six Minors resolved). Packaging is now at current PyPA best practice.
**In flight at wrap:**
- **`s3-multi-agent-rename` awaiting operator approval.** Plan filed in `/sdlc/work/active/s3-multi-agent-rename.md`. Three tasks: ADR-0014 (decision doc) → atomic rename (pyproject + version-lookup + README + SKILL.md + runbook + ADR-0012 cross-refs) → AGENTS.md + CLAUDE.md redirect.
- **Trusted Publisher setup question.** Operator asked for step-by-step setup instructions for Trusted Publishers; session was interrupted before delivery. Resume with: (a) clarify whether the operator wants TP set up under the CURRENT name `claude-code-review` or PRE-EMPTIVELY under the s3 target name `polyreview`; (b) deliver step-by-step covering both registries (pypi.org + test.pypi.org) and the GitHub `Settings → Environments` setup for `pypi` + `testpypi`.

**Operator decisions taken this session (locked, ready to execute under s3):**
1. **PyPI distribution rename**: `claude-code-review` → `polyreview` (short, coined, vendor-neutral; Ruff/Semgrep family; PyPI-available 2026-05-29).
2. **Cross-agent instructions file**: Add `AGENTS.md` at repo root (canonical) + shrink `CLAUDE.md` to a one-line `See AGENTS.md.` redirect. AGENTS.md is the Linux Foundation-stewarded standard, adopted by 60k+ repos, native readers Copilot/Codex/Cursor/Aider/GitLab Duo.
3. **Redirect meta-package**: Publish `claude-code-review` 0.x.y as a thin redirect depending only on `polyreview`. Deferred follow-up — depends on `polyreview` shipping first.

**Critical research finding (load-bearing for s3 scope):** As of 2025-12-18 (Agent Skills standard open-sourced), GitHub Copilot, VS Code, Cursor, Codex, Gemini CLI, Goose, ~40 other agents read `.claude/skills/`, `.github/skills/`, and `.agents/skills/` interchangeably. **The existing skill bundle at `.claude/skills/code-review/SKILL.md` is already consumed by Copilot today** — no skill-side move is needed for the multi-agent port. The `claude-` prefix on the PyPI distribution name is the only real coupling.

**Next:** at session start — operator decision:
- **(a) Approve s3 and execute** the three tasks under it. The natural order before first release.
- **(b) Trusted Publisher setup walk-through first** (resume the wrapped-mid-flight question). Useful if the operator wants to reserve `polyreview` on PyPI + TestPyPI before s3 lands (belt-and-braces against name-squatting; unblocks first release immediately after s3 closes).
- **(c) `s0-t6-cache-path-unification`** — sibling carryover; 3 adapters hardcode `.claude/skills/code-review/cache/...`. Becomes a more obvious blocker once s3 ships (Copilot users would have analyzers writing to a `.claude/` cache path). Worth tackling before any non-Claude consumer adopts the tool.
- **(d) First release.** Blocked on operator-side Trusted Publisher setup (and on the s3 rename if (a) is taken first).

## Active artefacts

- `epic-deployment-readiness.md` — epic shell; children now: s0, s1, s2 (done), s3 (proposed).
- `s3-multi-agent-rename.md` — story plan, status `proposed`, awaiting operator approval.
- `s0-t6-cache-path-unification.md` — sibling debt; pre-existing carryover; gains urgency post-s3.
- `s3-plan.md`, `s4-plan.md` — lingering plans from prior epic (not blocking).

## Done this session (2026-05-29)

- **s2-packaging-hardening closed** (full session 1: morning execution, evening wrap). 6 tasks, 14 commits, test count 304 → 326. New ADR-0013 partially superseding ADR-0003 §1 for runtime deps. Release workflow restructured (build → test-dist → publish, OIDC scoped). New CI workflow on push+PR. SKILL.md leads with installed binary. `setup.sh` BUNDLE_DIR fix.
- **Multi-agent strategy research + audit** (post s2 close). Identified the `.claude/skills/` cross-agent compatibility finding and the `claude-` distribution-name liability. PyPI-availability checks done for the candidate names. Operator picked `polyreview` + AGENTS.md + redirect.
- **s3 story drafted.** Plan filed in `/sdlc/work/active/s3-multi-agent-rename.md`. Not yet approved — operator was asking for Trusted Publisher details when session wrapped.

## Open questions

- **Trusted Publisher procedure (in flight, pre-empted by wrap).** Operator wants step-by-step. Cover: (1) the right name to register — `polyreview` (s3 target, recommended for belt-and-braces) and/or `claude-code-review` (current name, only needed if operator wants to test the existing workflow before s3 lands); (2) PyPI side — `https://pypi.org/manage/account/publishing/` → Add a new **pending** publisher; (3) TestPyPI side — same form at `https://test.pypi.org/manage/account/publishing/`; (4) GitHub side — `Settings → Environments` create `pypi` + `testpypi` environments with exact name match.
- **First-release timing.** Now coupled to (a) operator-side TP setup and (b) s3 rename decision.
- **`s0-t6-cache-path-unification`** — gains urgency post-s3 (Copilot adopters would have analyzers writing to `.claude/`).
- **Pre-existing mypy `conftest.py: Source file found twice`** — reproduces on all parent commits; carried through s2 unchanged.
- **Deferred L1 items from s2 audit**: agentic-skills root README still missing the `code-review` row; CHANGELOG.md not yet created; `--version` CLI flag still unfiled.

## Auto-progress posture (2026-05-29, unchanged)

Per SDLC §Execute and rule #22: tasks under an operator-approved story auto-execute; Verify + Review run per task; halts only on Verify failure, Review's 2-round bound, gate escalation, hard-stop, three failed attempts, ≥75% context, or operator interruption. Story-level Review at story boundary. **s3 is `proposed`, not yet approved — auto-progress does NOT apply until the operator approves the story plan.**
