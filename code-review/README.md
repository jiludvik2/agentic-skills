# polyreview

Deterministic code-review skill: runs Semgrep, Radon, Bandit and friends across a diff and emits a **review bundle** of raw per-tool output (`review-bundle.v1.json`) — one capture per analyzer for an agent to interpret (ADR-0020).

## Status

Alpha. No API stability guarantees before `1.0`. Expect breaking changes to CLI flags, config schema, and the bundle contract. The canonical version lives in `pyproject.toml`; check the installed version with `polyreview --version` once the flag lands or `python -c "import code_review; print(code_review.__version__)"`.

**Renamed from `claude-code-review`.** Early development used the working name `claude-code-review`; the PyPI distribution is **`polyreview`** (it was renamed before its first release, so there is no `claude-code-review` package to migrate from). The rename drops the vendor prefix because the tool is agent-agnostic — its Agent Skill bundle is read by GitHub Copilot, Cursor, Codex, and other agents, not just Claude — and `polyreview` reads as a multi-language, multi-tool reviewer rather than an Anthropic-only one. The Python import name stays `code_review`.

## Install

```bash
pip install polyreview
pipx install polyreview
uv tool install polyreview
```

The PyPI distribution and console-script binary are both `polyreview`; the Python import name stays `code_review` (PEP-423 allows the distribution name to differ from the import name).

> **`0.1.0` is the first GA release** to PyPI. It was staged as `0.1.0rc1` on TestPyPI first; see `sdlc/docs/runbooks/release.md` for the release process.

### Analyzer prerequisites

`pip install polyreview` ships the **Python** analyzers — Semgrep, Bandit, Radon, Vulture, pydeps, cohesion — ready to run. The other analyzers depend on external tooling that pip can't bundle:

- **JavaScript/TypeScript** (ESLint, knip, jscpd, dependency-cruiser, jscomplexity) need a vendored `node_modules`.
- **Secret & dependency scanning** (gitleaks, Trivy) are standalone binaries that must be on your `PATH`.

Run `polyreview run --capabilities` and read `analyzers[]` to see which are active: each reports `status: available` or `unavailable` with the reason. To provision the full set from a source checkout, run `./scripts/setup.sh` (Node tooling + offline caches) and install gitleaks/Trivy via your package manager. Analyzers that aren't available are skipped silently — so a finding-free run on a stack you expected coverage for may just mean the analyzer wasn't installed.

## Use as an Agent Skill

`polyreview` is also an Agent Skill bundle: agents (Claude Code, Codex, GitHub Copilot, Gemini CLI, …) discover it from their user-level skills directory. After installing the package, place the bundle where your agents look — `polyreview install` is agent-independent, idempotent, and creates missing directories:

```bash
polyreview install                 # neutral ~/.agents/skills/ + every agent home present
polyreview install --agent claude  # one target: agents | claude | copilot | gemini
polyreview install --all           # every known agent location
polyreview install --force         # refresh an already-installed bundle in place
```

Install places the skill (`SKILL.md`, the config example, the vendored Semgrep rules) for *discovery*; it does **not** fetch the analyzer caches (`node_modules`, Trivy DB) — run `./scripts/setup.sh` for the full toolchain. Remove it with the same target scoping:

```bash
polyreview uninstall               # mirrors install's default + --agent/--all scoping
```

Uninstall is **marker-guarded**: it removes only a directory that is verifiably the polyreview bundle, and never touches a sibling skill, an agent's own files (e.g. Claude's `agents/reviewer.md`), or the skills directory itself.

## Quick start

```bash
polyreview run --review security --depth quick --diff HEAD~1..HEAD --output review.json
```

Writes a **review bundle** to `review.json` (`review-bundle.v1.json` schema): the request echo plus one entry per analyzer in the `security/quick` set, each carrying that tool's raw `stdout`/`stderr` verbatim and an ADR-0019 `status` (`ok` / `error` / `timeout` / `unavailable`). The bundle is for an agent to interpret — polyreview does not parse, rank, or merge findings.

## What it does

- Deterministic analyzer layer — Semgrep, Bandit, Radon, and other rule-based scanners.
- Emits a raw review bundle (one capture per tool) so the consuming agent reads each tool's native output directly, rather than a lossy normalised summary (ADR-0020).
- Runs under `/sandbox` — analyzers are isolated from the host filesystem and network.

## What it doesn't do

- LLM-based code review — that's the sibling `intent-review` project.
- Cross-tool aggregation, dedup, or severity ranking — it captures each tool raw; the agent interprets.
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
