# State — last updated 2026-06-01

**Active focus:** None — `story-jscomplexity-ts` closed cleanly at its story boundary (standalone post-GA story, no epic parent). Awaiting operator direction on next work.
**Last completed:** **`story-jscomplexity-ts`** — TypeScript cyclomatic-complexity support for `jscomplexity` (t0 vendored `@typescript-eslint/parser ^8.60.0` parser-only + advertised `typescript`; t1 wired it into the complexity flat config for `.ts/.tsx/.mts/.cts` + fixture/integration tests + drift anchor + doc reconciliation). Verifier PASS, per-task + story-level review MINOR-ONLY (both Minors fixed inline).
**Next:** Operator decides. Candidates: push the 5 unpushed commits (+ optional `code-review-v0.1.2` patch tag), or start the next epic/story.

## Publish
- **5 commits unpushed** to `origin/main`: `95c1a22` (plan), `f4a9d1d` (t0), `d791c80` (prior wrap), `2f8d90c` (t1), `d1348b3` (story close). Push is operator-gated (no pre-auth in AGENTS.md).
- No release tag cut. If published as a patch it would be `code-review-v0.1.2` (push the tag standalone — release.yml trigger).

## Session gotchas (recurring)
- `uv run`/`uv build` panic under the sandbox → use `.venv/bin/python|pytest|ruff|mypy`. Full `pytest -q` shows 9 environmental fails (6 wheel + 1 console-script on `uv build` exit 101; 2 semgrep `--x-` exit 2) — all green in CI.
- `npm install` (toolchain vendoring) needs the sandbox disabled (registry + `~/.npm/_cacache`).

## Open questions / carried-forward follow-ups
- Push the 5 commits now, or batch with the next story?
- **TS cohesion** stays a documented gap (ADR-0022) — no suitable thin tool. Only remaining `maintainability` boundary.
- **Stale doc:** `stack-pins.md` §License floor cites `scripts/license_audit.py` (absent) — pre-existing, unaddressed.
- Canonical-SDLC sync still pending (project SDLC 6.6 ahead of bundle 6.4).
