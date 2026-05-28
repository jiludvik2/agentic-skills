---
name: code-review
description: Deterministic analyzer layer — runs Semgrep, Radon, and more scanners against a diff and emits consolidated SARIF/metrics JSON. Invoked via the code_review CLI; analyzer set selected by --review domain/subcategory and --depth quick|full.
---

# code-review

A deterministic code-analysis layer that runs one or more analyzers against a target or a diff range and returns a single consolidated JSON document — SARIF findings plus complexity/coupling metrics.

## Invocation

```
python -m code_review.cli [--review <domain|subcategory>] [--depth quick|full]
    [--analyzer <name>] [--target <path>] [--diff HEAD~1..HEAD]
    [--output <path inside CWD>] [--scope per-task|story-level]
```

- **`--review`** accepts a domain name or a subcategory name (repeat for multiple). See taxonomy table below.
- **`--depth quick|full`** selects the depth tier when `--review` names a domain. Ignored when `--review` names a subcategory. Default: `quick`.
- **`--analyzer`** overrides `--review`/`--depth` and runs exactly those analyzers.
- Without `--output`, the consolidated JSON is printed to stdout.
- With `--output`, the JSON is written atomically and stdout carries only a one-line summary: `analyzers: N | findings: M | duration: T s`.
- `--output` paths must resolve inside the current working directory (sandbox compatibility).
- `--capabilities` prints the static capability declaration merged with runtime per-analyzer availability checks.

The request/response contracts and capability declaration are bundled inside the `code_review` package (`code_review/schemas/*.json`, `code_review/capabilities.json`).

## Review taxonomy

### Domains and subcategories

The taxonomy is data-driven (`capabilities.json`) and enforced at parse time. Use `--capabilities` to see the live table.

| Domain | Subcategory | Tier | Languages | Timing |
|---|---|---|---|---|
| `security` | `vulnerabilities` | quick | py, js, ts | any |
| `security` | `secrets` | quick | py, js, ts | any |
| `security` | `dependencies` | full | py, js, ts | any |
| `maintainability` | `complexity` | quick | py | any |
| `maintainability` | `dead-code` | quick | py, js, ts | any |
| `maintainability` | `duplication` | quick | js, ts | any |
| `maintainability` | `quality` | quick | js, ts | any |
| `maintainability` | `coupling` | full | py, js, ts | any |
| `maintainability` | `cohesion` | full | py | any |
| `contracts` | `conformance` | full | API | story-level |

### Depth tier

`--depth quick` (default) runs every subcategory whose tier is `quick`. `--depth full` additionally runs `full`-tier subcategories. Subcategory selection (naming a subcategory directly with `--review`) is always depth-independent.

### Resolution precedence

1. `--analyzer X` (repeatable) — override; runs exactly those analyzers.
2. `--review <domain>` + `--depth` — union of that domain's subcategories at tier ≤ depth.
3. `--review <subcategory>` — exactly that subcategory's analyzers; `--depth` ignored.
4. `--depth quick|full` alone (no `--review`) — every analyzer at that tier, all domains.
5. No selection flags — defaults to `--depth quick`.
6. Multiple `--review` values — unioned. Redundant values emit a stderr warning; exit 0.

### Common examples

```bash
# Quick security review (semgrep, bandit, gitleaks)
python -m code_review.cli --review security --diff HEAD~1..HEAD

# Full security review (adds trivy)
python -m code_review.cli --review security --depth full --diff HEAD~1..HEAD

# Specific subcategory (coupling only; ignores --depth)
python -m code_review.cli --review coupling --scope story-level --target .

# Whole quick review (default)
python -m code_review.cli --target .

# Contract testing at story-level
python -m code_review.cli --review conformance --scope story-level --target .
```

### Warnings and errors

All warnings go to **stderr** only (never stdout, never the `--output` JSON). Exit code 0 for warnings; non-zero only for hard errors.

- **Redundant `--review`** — subcategory already covered by a domain at the active depth: warning + exit 0.
- **Duplicate `--review`** — same value twice: deduped + warning + exit 0.
- **Subcategory + explicit `--depth`** — depth is ignored: warning + exit 0.
- **Contradictory `--depth`** values — simpler (`quick`) wins: warning + exit 0.
- **Unknown `--review` value** — error listing valid domains and subcategories: exit 1.
- **`contracts --depth quick`** — domain has no quick-tier analyzers: exit 1 with message.
- **`conformance --scope per-task`** — story-level-only analyzer excluded: exit 1 with message.

## Install

Run the setup script once, outside the sandbox (it needs network access):

```
./scripts/setup.sh
```

It installs Python deps (`uv sync --frozen`), Node deps for JS analyzers (`npm ci`, guarded on `package.json`/`package-lock.json` being present), prefetches offline caches (Trivy DB, Semgrep rule packs) into `cache/`, reports the state of the host project's `.claude/agents/reviewer.md` (read-only — never written), and prints the path of the bundled starter config template. The script is idempotent — re-running refreshes caches without redundant downloads and exits non-zero with a clear message if any step fails. After it has run, the skill is fully self-contained and runs inside the sandbox with no network egress.

After install, copy `code-review.toml.example` (next to this `SKILL.md` in the skill bundle) to your project root and uncomment the keys you want to override. See the file's own comments for each tunable.

### Deployment layouts

The skill supports three on-disk shapes. The `code_review` Python package resolves its own bundled JSON contracts via `importlib.resources`, so all three work identically without code changes:

1. **Dev sibling layout** (repo-as-skill, what this repo is): `<repo>/code_review/` (the package) lives next to `<repo>/.claude/skills/code-review/` (the skill bundle). Used when developing the skill itself.
2. **Production nested layout**: `<host>/.claude/skills/code-review/code_review/` — the package is nested inside the skill directory. Used when copying the skill bundle into a host project as-is.
3. **Wheel-installed layout** (not yet shipped — see story `s1-package-publication`): `code_review/` lives under `site-packages/` (installed via `pip install claude-code-review`); the host's `<host>/.claude/skills/code-review/` carries only this `SKILL.md` and (optionally) a `code-review.toml`. Used in production deployments where the skill is installed from PyPI.

`code-review.toml` is always looked up CWD-relative — `<cwd>/code-review.toml` by default, or whatever `--config <path>` names. Run the CLI from the host project root.

### Reviewer sub-agent (host's responsibility)

`code-review` is a pure deterministic analyzer — it does not install or modify any sub-agent. The SDLC's Review verb dispatches `<host>/.claude/agents/reviewer.md`, whose lifecycle is owned by the SDLC skill (bootstrap step) or the operator. `setup.sh`'s final step reports the state it found:

- **Found** — left untouched. The host already has a reviewer sub-agent; `code-review` doesn't manage it.
- **Missing** — flagged with a hint to install via the SDLC skill (re-run its bootstrap) or copy your own. Without a reviewer.md the SDLC Review verb cannot dispatch.
- **No `.claude/` ancestor** — the skill appears to be the repo itself (developer layout) rather than installed under `<host>/.claude/skills/code-review/`; the check is skipped.

How a consumer (CI script, the `intent-review` sibling skill, a human at the terminal, or a custom reviewer.md) actually drives `code-review` is up to the consumer — invoke `python -m code_review.cli` with the `--review` / `--depth` flags documented above.

## Sandbox configuration

The skill is designed to run entirely inside Claude Code's OS sandbox after `setup.sh` has prefetched everything. Recommended strict defaults for the host project's `.claude/settings.json`:

```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "failIfUnavailable": true,
    "filesystem": {
      "allowWrite": ["~/.cache/uv"],
      "denyRead": ["~/.ssh", "~/.aws", "~/.gnupg", "~/.config/gh", "~/.config/gcloud", "~/.netrc"]
    },
    "network": {
      "allowedDomains": []
    }
  }
}
```

At `quick` or `full` scope the deterministic analyzers need no network at runtime, so `allowedDomains` stays empty. For contract testing (`--review conformance --scope story-level`), add the Schemathesis target hosts to `allowedDomains` — and nothing else.

```json
{
  "sandbox": {
    "network": {
      "allowedDomains": ["localhost", "api.internal.example.com"]
    }
  }
}
```

If Schemathesis cannot reach the configured target, the adapter returns `status: "error"` with an `error` field naming the unreachable host and reminding you to check `sandbox.allowedDomains`. Other analyzers' results are preserved in the consolidated output.
