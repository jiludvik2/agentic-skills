# State — last updated 2026-06-01

**Active focus:** None — `story-jscomplexity-ts` closed + pushed; a housekeeping pass cleared the absorbed dogfood raw and two stale doc claims. Awaiting operator direction on next work.
**Last completed:** Housekeeping (commit `402145a`): rm absorbed `dogfood-2026-06-01` raw; corrected `stack-pins.md` License-floor (no CI gate exists — manual policy); added pydeps/cohesion interpretation caveats to SKILL.md. Before that: **`story-jscomplexity-ts`** — TypeScript complexity for `jscomplexity` (verifier PASS, per-task + story-level review MINOR-ONLY, all fixed inline).
**Next:** Operator decides. The one remaining forward project is the **contract-testing skill spinout** (ADR-0021) — `sdlc/raw/contract-testing-skill.md` is a ready compile seed (lift `schemathesis_.py` + fixture from git history; new standalone skill; carries `pytest<9` constraint).

## Publish
- **1 commit unpushed** to `origin/main`: `402145a` (housekeeping). Everything through `a935615` (the jscomplexity-ts story) is already pushed. Push is operator-gated (no pre-auth in AGENTS.md).
- No release tag cut. A patch would be `code-review-v0.1.2` (push the tag standalone — release.yml trigger).

## Session gotchas (recurring)
- `uv run`/`uv build` panic under the sandbox → use `.venv/bin/python|pytest|ruff|mypy`. Full `pytest -q` shows 9 environmental fails (6 wheel + 1 console-script on `uv build` exit 101; 2 semgrep `--x-` exit 2) — all green in CI.
- `npm install` (toolchain vendoring) needs the sandbox disabled (registry + `~/.npm/_cacache`).

## Open questions / carried-forward follow-ups
- Push `402145a` now, or batch with the next story?
- **TS cohesion** stays a documented gap (ADR-0022) — no suitable thin tool. Only remaining `maintainability` boundary.
- **License-floor automation:** the allow-list audit (`scripts/license_audit.py`) was specified but never built; the floor is currently manual policy, not a CI gate. Build it, or formally accept manual enforcement (ADR)?
- Canonical-SDLC sync still pending (project SDLC 6.6 ahead of bundle 6.4).
