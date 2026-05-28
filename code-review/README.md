# claude-code-review

Deterministic code-review skill: runs Semgrep, Radon, Bandit and friends across a diff and emits consolidated SARIF + per-finding `sdlc_severity`.

## Status

Alpha — `0.1.0`. No API stability guarantees before `1.0`. Expect breaking changes to CLI flags, config schema, and SARIF property names.

## Install

```bash
pip install claude-code-review
pipx install claude-code-review
uv tool install claude-code-review
```

The PyPI distribution is `claude-code-review` (the shorter `code-review` is taken). The console-script binary is `claude-code-review`; the Python import name stays `code_review`.

## Quick start

```bash
claude-code-review --review security --depth quick --diff HEAD~1..HEAD --output review.json
```

Returns a SARIF document at `review.json` containing findings from every analyzer in the `security/quick` set, each annotated with an `sdlc_severity` reflecting how the SDLC treats it (Critical / Important / Minor / Nit).

## What it does

- Deterministic analyzer layer — Semgrep, Bandit, Radon, and other rule-based scanners.
- Emits SARIF with an `sdlc_severity` extension so downstream tools can gate on real severity, not analyzer-native rankings.
- Runs under `/sandbox` — analyzers are isolated from the host filesystem and network.

## What it doesn't do

- LLM-based code review — that's the sibling `intent-review` project.
- Cross-skill aggregation — one diff, one analyzer set, one SARIF.
- CI orchestration — invoke it from your existing pipeline; it doesn't replace one.

## Full reference

Complete review-set taxonomy, CLI resolution rules, and configuration knobs: [`.claude/skills/code-review/SKILL.md`](https://github.com/jiludvik2/agentic-skills/blob/main/code-review/.claude/skills/code-review/SKILL.md).

## Development

```bash
git clone https://github.com/jiludvik2/agentic-skills
cd agentic-skills/code-review
./scripts/setup.sh
uv run pytest
```

## License

MIT.
