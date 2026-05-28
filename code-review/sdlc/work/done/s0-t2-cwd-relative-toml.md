---
id: s0-t2-cwd-relative-toml
kind: task
project: code-review
status: done
parent: s0-deployment-layout-fixup
created: 2026-05-28
updated: 2026-05-28
---

# s0-t2 — CWD-relative `code-review.toml` + `--config` flag

## Outcome

`code-review.toml` is found at `Path.cwd() / "code-review.toml"` by default; the CLI's new `--config <path>` flag overrides. The hard-coded `_SKILL_DIR` arithmetic in `cli.py:24` is deleted. The skill no longer assumes any particular layout for the operator's config file.

## Acceptance criteria

- `code_review/config.py:load_config` signature changes to take an explicit `Path | None` (the config file path) rather than a skill-dir argument. If `None` is passed, returns defaults (or reads from `Path.cwd() / "code-review.toml"` if it exists — pick the call-site that resolves CWD; see Notes).
- `code_review/cli.py` adds a `--config <PATH>` option to the main command via Typer. The default is `None`. When `None`, the CLI computes `Path.cwd() / "code-review.toml"` and passes it to `load_config` only if the path exists; otherwise passes `None`.
- When `--config <path>` is explicitly given and the path does not exist, the CLI exits non-zero with: `Error: --config path does not exist: <path>` (or close to it). No silent fall-through to defaults.
- The `_SKILL_DIR = Path(__file__).resolve().parent.parent / ".claude" / "skills" / "code-review"` line in `cli.py:24` is removed.
- Any other reference to `_SKILL_DIR` in `code_review/` is removed (per `grep -rn '_SKILL_DIR' code_review/` returning empty). Specifically: `adapters/trivy.py:11` and `adapters/js_base.py:7` (operator-runtime cache paths) are migrated to `Path.cwd() / ".claude" / "skills" / "code-review" / "<cache subpath>"` — same CWD-relative idiom as `code-review.toml`. No env var override; operator runs CLI from project root. (Scope-expansion approved 2026-05-28 per operator escalation.)

## Test specification

- **New: `tests/test_config_lookup.py`** — table-driven:
  - **CWD has `code-review.toml`**, no `--config`: `load_config(...)` reads CWD's TOML; returned `Config` reflects its overrides.
  - **CWD has no TOML**, no `--config`: returns defaults (current behaviour); no warning.
  - **`--config <existing>`**: named path is read; returned `Config` reflects its overrides; CWD TOML (if any) is ignored.
  - **`--config <missing>`**: CLI exits non-zero; stderr contains the missing path.
  - **`--config <existing>` and CWD also has a TOML**: the `--config` value wins; CWD TOML is not read.
- Use `monkeypatch.chdir(tmp_path)` to control CWD without affecting other tests.
- Use Typer's `CliRunner(capture="fd")` per the project convention (memory: `feedback-typer-runner-capture-fd`).

## Notes

- Decide one call-site convention and stick to it: either (a) `cli.py` resolves the path (CWD lookup + `--config` precedence) and passes a concrete `Path | None` to `load_config`, or (b) `load_config(path=None)` does the CWD lookup internally. **(a) is recommended** — it keeps `load_config` a pure function and concentrates resolution policy in one place.
- After this task, `_SKILL_DIR` is gone — that frees up `cli.py:24` and removes the deferred ADR-0007 question.
- The `--config` flag belongs in the main command's options, alongside `--review`, `--depth`, `--scope`, `--diff`, `--output`, `--analyzer`. Don't subcommand it.
- Document `--config` in `--help` output: "Path to code-review.toml. Default: ./code-review.toml in CWD if present, else built-in defaults."

## Notes (post-review)

### Important finding deferred as architectural follow-up

Reviewer flagged a producer/consumer cache-path divergence in `adapters/trivy.py` and `adapters/js_base.py`: the path my change reads (`<cwd>/.claude/skills/code-review/cache/...`) does not align with the path `scripts/setup.sh` + `scripts/prefetch_caches.py` write to (`${SKILL_ROOT}/cache/...`) outside the production-nested layout with CLI run from `<host>/`.

**Status: pre-existing, not a regression.** Investigation showed the OLD `_SKILL_DIR`-walked consumer path had the same divergence in dev sibling layout (`<repo>/code-review/.claude/skills/code-review/cache/trivy-db` — directory doesn't exist; producer wrote to `<repo>/code-review/cache/` instead). Tests patch the helpers, so the divergence has been latent. Story s0's AC8 smoke test passes because it uses the one layout where producer and consumer happen to align.

**Deferred to** `s0-t6-cache-path-unification` (new task filed in this session). The fix needs an architectural decision on the cache contract across all three layouts including the wheel-installed-no-producer case — outside this task's spec even after the scope expansion.

### Minor fixes applied inline (during close)

- `config.py:load_config` — collapsed the two `Config(...)` default branches into one; tightened the docstring to be honest about the defensive existence check.
- `cli.py` — renamed the Typer `config: Path | None` parameter to `config_path` to remove the local-variable shadow with the loaded `Config` object downstream; downstream `loaded_config.*` references reverted to `config.*`.

### Nit (dropped, per §review)

- N/A — the rename Nit was applied as part of the Minor cleanup above.
