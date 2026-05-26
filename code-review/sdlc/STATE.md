# State — last updated 2026-05-26

**Active focus:** First compile complete. The `epic-reviewer-subagent` epic (reviewer sub-agent + deterministic analyzer layer, exposed as the `code-review` skill) and its six stories `s0`–`s5` are filed in `/sdlc/work/active/`, alongside the architecture doc and six ADRs (co-located per SDLC.md:84 while the epic is in flight). `stack-pins.md` is at `/sdlc/docs/architecture/`.

**Last completed:** Compiled the two `/sdlc/raw/` files into: epic + s0–s5 stories, `architecture-reviewer-subagent.md`, `stack-pins.md`, and `adr-0001-publication` … `adr-0006-sarif-canonical-format`. Re-tagged all artefacts `project: code-review`. Drained `/sdlc/raw/` (originals removed; recoverable in git). Not yet committed.

**Next:** Plan `s0-analyzer-facade-and-two-adapters` (the prerequisite story — Analyzer Protocol, SARIF/MetricSet types, Semgrep + Radon adapters, CLI). Decompose into `s0-t*` tasks per the Plan verb, then execute tests-first. Before any dependency install, rule #1b reconciles `stack-pins.md` against the (not-yet-created) project manifest.

## Open questions
- None. Compile commit pending operator go-ahead.
