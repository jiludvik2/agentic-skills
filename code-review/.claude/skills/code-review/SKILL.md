---
name: code-review
description: Deterministic analyzer layer for the Reviewer sub-agent — runs Semgrep, Radon, and (later) more scanners against a diff and emits consolidated SARIF/metrics JSON. Invoked via the code_review CLI; configured by review scope (lite/standard/full).
---

# code-review

A deterministic code-analysis layer the Reviewer sub-agent shells out to. It runs one or more analyzers (s0: Semgrep + Radon; later stories add the rest) against a target or a diff range and returns a single consolidated JSON document — SARIF findings plus complexity/coupling metrics — that the LLM design-review step then reasons over.

## Status

This skill is being delivered across story s1; this document describes its full intended surface. As of s0 the following is **live**: the `code_review` CLI with `--analyzer`, `--target`, `--diff`, and `--output`, plus `--capabilities` (currently emitting only the registered analyzer-name list). **Landing in s1**: scope selection via `--review-scope` and the SDLC `review_scope` config (s1-t2/t4), the rich `--capabilities` merge of static declaration with runtime availability checks (s1-t2), the `capabilities.json` instance (s1-t1), and `scripts/setup.sh` (s1-t3). Features below that are not yet live are noted here rather than in each section.

## Invocation

```
python -m code_review.cli --analyzer semgrep --analyzer radon --target <path> [--diff HEAD~1..HEAD] [--output <path inside CWD>] [--review-scope standard]
```

- Without `--output`, the consolidated JSON is printed to stdout.
- With `--output`, the JSON is written atomically (`.tmp`-then-rename, sibling in the same directory) and stdout carries only a one-line summary: `analyzers: N | findings: M | duration: T s`.
- `--output` paths must resolve inside the current working directory; paths outside CWD are rejected for sandbox compatibility.
- `python -m code_review.cli --capabilities` prints the static capability declaration merged with runtime per-analyzer availability checks.

The request/response contracts and capability declaration are bundled inside the `code_review` package (`code_review/schemas/*.json`, `code_review/capabilities.json`) and travel with it on install — they are not separate files in the skill directory. To see the live capability declaration merged with runtime availability, run `python -m code_review.cli --capabilities`.

## Review scopes

The skill operates at one of three scopes, selected by the operator via the SDLC project config (`review_scope`). The default when unset is `lite`.

- **lite** — LLM design review only; the deterministic analyzer CLI is not invoked. Suits proof-of-concept and throwaway work where scan latency isn't worth it. This is the pre-installation behaviour of the Reviewer sub-agent.
- **standard** — runs the deterministic analyzer layer (Semgrep + Radon and any other registered analyzers) over the review diff, then feeds the consolidated findings into the LLM design review. Suits most production code.
- **full** — everything in `standard` plus contract-testing analyzers (Schemathesis/Pact, s4) that exercise live endpoints; needs additional `allowedDomains` for target hosts. Suits complex brownfield services with API contracts to defend.

## Install

Run the setup script once, outside the sandbox (it needs network access):

```
./scripts/setup.sh
```

It installs Python deps (`uv sync --frozen`), Node deps for JS analyzers (`npm ci`, **skipped until the JS toolchain lands in s3** — guarded on `package.json`/`package-lock.json` being present), prefetches offline caches (Trivy DB, Semgrep rule packs) into `cache/`, and copies the Reviewer sub-agent into the host project's `.claude/agents/reviewer.md`. The script is idempotent — re-running refreshes caches without redundant downloads and exits non-zero with a clear message if any step fails. After it has run, the skill is fully self-contained and runs inside the sandbox with no network egress.

## Configure

Set the review scope in the SDLC skill's project-level config:

```
review_scope = "standard"
```

Valid values: `"lite"`, `"standard"`, `"full"`. The change takes effect on the next Review dispatch; no other action is required. Setting it back to `"lite"` restores LLM-only review.

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

At `lite` and `standard` scope the analyzers need no network at runtime, so `allowedDomains` stays empty. At `full` scope, add the contract-testing target hosts (the base URLs Schemathesis/Pact exercise) to `allowedDomains` — and nothing else. Credential paths stay in `denyRead` so no analyzer subprocess can read them.

### Contract testing (story-level, full scope)

Story-level reviews at `full` scope invoke Schemathesis. It needs network access to the targets you configure in `code-review.toml`'s `[contract_testing]` section. Add only those specific hosts (e.g., `localhost`, your internal service hostname) to `sandbox.allowedDomains` — never widen to wildcards or public-internet hosts.

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
