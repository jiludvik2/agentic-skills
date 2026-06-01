# State — last updated 2026-06-01

**Active focus:** None. `sdlc/work/active/` and `sdlc/raw/` are both empty — project at a stable post-GA resting state. Awaiting operator direction.
**Last completed:** Contract-testing fully out of scope (commit `30b1b9f`, ADR-0021 amended 2026-06-01): the parked separate-skill spinout is abandoned, no successor planned; discarded the `/sdlc/raw/` seed; cleared stale contract/schemathesis assumptions in the arch + intent-review docs. Before that: housekeeping (`402145a`) and **`story-jscomplexity-ts`** (TypeScript complexity, MINOR-ONLY reviews).
**Next:** Operator decides. No forward project queued. Lingering follow-ups only (see Open questions).

## Publish
- **4 commits unpushed** to `origin/main`: `402145a` (housekeeping), `dfdbe21` (wrap), `30b1b9f` (contract-testing out of scope), + this wrap. Everything through `a935615` (jscomplexity-ts story) is pushed. Push is operator-gated (no pre-auth in AGENTS.md).
- No release tag cut. A patch would be `code-review-v0.1.2` (push the tag standalone — release.yml trigger).

## Session gotchas (recurring)
- `uv run`/`uv build` panic under the sandbox → use `.venv/bin/python|pytest|ruff|mypy`. Full `pytest -q` shows 9 environmental fails (6 wheel + 1 console-script on `uv build` exit 101; 2 semgrep `--x-` exit 2) — all green in CI.
- `npm install` (toolchain vendoring) needs the sandbox disabled (registry + `~/.npm/_cacache`).

## Open questions / carried-forward follow-ups
- Push the 4 unpushed commits now?
- **pytest 9.x bump** now fully unblocked (schemathesis was the last blocker; gone) — deferred dev-dep-bump story, would drop the CVE-2025-71176 allow-list. Expiry 2026-08-31 (stack-pins §pytest).
- **License-floor automation:** the allow-list audit (`scripts/license_audit.py`) was specified but never built; the floor is currently manual policy, not a CI gate. Build it, or formally accept manual enforcement (ADR)?
- **TS cohesion** stays a documented gap (ADR-0022) — no suitable thin tool. Only remaining `maintainability` boundary.
- Canonical-SDLC sync still pending (project SDLC 6.6 ahead of bundle 6.4).
