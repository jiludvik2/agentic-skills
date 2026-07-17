# gsd-standards-guard

A project-owned addon that makes GSD's code review **enforce this project's standards** —
`docs/ARCHITECTURE.md`, `docs/STANDARDS.md`, and the binding `docs/adr/*` decisions — and that
generates and audits those decisions. Enforcement is **deterministic** (a native Claude Code hook,
not a discretionary instruction), **selective** (only the rules a given diff can violate), and
**survives arbitrary GSD upgrades** because it patches **zero** vendor files.

> **Status — redesign (rev. 4), built.** This replaces the old **patch-based installer** that
> content-patched four GSD-owned files. The full design is specified in
> [`gsd-standards-guard-redesign.md`](./gsd-standards-guard-redesign.md) — that document is the
> source of truth. The package is implemented: engine, hook, `/write-adr`, `/standards-audit`,
> `install.sh`, and templates, with a test suite (`node --test tests/*.test.js`). Deploy into a project with
> `./install.sh`; migrate an already-patched project per *Migrating from the patched installer*.

> **Two layers — package vs. project instance.** This repo ships the **reusable package** (the
> engine, hook, skills, `install.sh`, the `index.yaml` *schema*, and the ARCHITECTURE.md *authoring
> contract*). The **rule corpus** (the populated `docs/adr/index.yaml` and `docs/ARCHITECTURE.md`
> ledger) is *per-project data* — each adopting project authors its own rows against the schema.
> `install.sh` seeds an empty `index.yaml` + a contract skeleton; `/write-adr` grows them.

> **Claude Code only.** This addon targets Claude Code — native `PreToolUse` hooks wired through
> `.claude/settings.json`. Support for other agents is out of scope. (Project-owned files live under
> `.agents/` purely for upgrade-safety — that tree sits outside GSD's file manifest — not for
> cross-agent reach.)

## Why the redesign

The old installer patched four vendor-owned GSD files (`gsd-code-reviewer.md`, `code-review.md`,
`discuss-phase.md`, and a net-new `write-adrs.md`) and backed them up for `/gsd-update --reapply`.
That is **one `gsd-update` away from silent failure** — manifest drift, an orphaned ADR step that
survives but is no longer called, an empty `pristine_hashes`, and a dead installer reference. The
redesign moves every moving part into **project-owned locations GSD never touches**, so an upgrade
is a no-op for enforcement.

## How it works

A single project-owned rule engine, **`gsd-standards-guard`**, is the sole authority for: *given a file
set, which standing rules apply, and — where a rule is mechanically checkable — are they violated.*
Two **independent** callers feed it a file set:

| Caller | Scope | Trigger | Purpose |
|---|---|---|---|
| **PreToolUse hook** | `--scope=diff` | automatic, in the code-review subagent | inject the matching standing rules into the reviewer's context on every review |
| **`/standards-audit`** | `--scope=all` | manual (`git ls-files`) | whole-codebase compliance sweep (pre-release / CI) |

One rule table (`docs/adr/index.yaml`), one matcher, one code path — the hook and the audit
**cannot drift** in what they enforce, and neither depends on the other.

### Deterministic vs semantic rules

Each rule in `docs/adr/index.yaml` is either:

- **Semantic** — the engine only *injects* it into the reviewer's context; the model judges
  compliance.
- **Deterministic** — the rule carries a small declarative `check:` (forbid/require a pattern within
  a path set); the engine *verifies* it and emits a hard pass/fail. `/standards-audit` **exits
  non-zero** in CI on any deterministic violation.

Both tiers run at both scopes.

## Components

| Path | Role |
|---|---|
| `.agents/skills/gsd-standards-guard/` | shared rule engine — glob-match + deterministic `check:` tier |
| `.agents/hooks/gsd-standards-guard.js` | thin `PreToolUse` caller → engine `--scope=diff` |
| `.agents/skills/standards-audit/` | manual whole-codebase audit → engine `--scope=all` |
| `.agents/skills/write-adr/` | ADR generator (house Nygard format, width-detecting numbering) |
| `.claude/settings.json` → PreToolUse JSON entry | wires the hook |
| `CLAUDE.md` → marked block | main-agent backstop directive |
| `docs/ARCHITECTURE.md` | standing-rule ledger (authored) |
| `docs/adr/index.yaml` | machine-readable rule index — the hook/audit selector |
| `docs/STANDARDS.md`, `docs/adr/*` | binding standards + decisions |

Nothing under `.claude/gsd-core/**` or `.claude/agents/` is patched.

### Review-context scoping (validated)

The hook must fire only in the review context. It scopes to the reviewer subagent with a one-line
guard on the `PreToolUse` stdin:

```js
if (input.agent_type === "gsd-code-reviewer") { /* inject directive + matched rules */ }
```

This is confirmed working: a `PreToolUse` hook **fires inside** a Task subagent, its stdin carries
`agent_type`/`agent_id` (**absent** on main-loop calls), and its `additionalContext` **reaches** the
subagent's model. The `agent_type` string `gsd-code-reviewer` is confirmed against gsd-core source
(branch `next`). The hook injects **once per `agent_id`** (a reviewer issues many reads) to avoid
re-injecting on every file read.

## Installation

Skill-first, thin shell installer (mirrors `gsd-api-first`). The skills and hook are ordinary
project-owned files; the installer only performs the edits that touch shared config.

```bash
./install.sh                 # install into the current project
./install.sh --project PATH  # install into another project
./install.sh --uninstall     # remove marked blocks + project-owned files
```

`install.sh` (idempotent):

1. copies the skills + hook into the project's `.agents/`;
2. adds/replaces our `hooks.PreToolUse` **JSON entry** in `.claude/settings.json` (keyed by the hook
   command — strict JSON, so no comment markers; GSD's own merge writer preserves it);
3. inserts the marked directive block into `CLAUDE.md`;
4. verifies `docs/adr/index.yaml` exists and parses (fail loud otherwise);
5. never touches any file under `.claude/gsd-core/` or `.claude/agents/`.

The `CLAUDE.md` edit is delimited by `# >>> gsd-standards-guard >>>` / `# <<< gsd-standards-guard <<<`
comment markers; the `settings.json` edit is a JSON entry matched by command path. Both are
add-or-replace, so re-running is idempotent.

## Usage

- **Automatic** — every `/gsd:code-review` run: the hook injects the standing rules whose file-globs
  match the changed files, plus the enforcement directive. Findings cite the source
  (e.g. *"violates ADR-024 — view DDL must run at the composition root, not in a repository"*).
- **`/standards-audit`** — manual whole-codebase compliance sweep. Runs the deterministic checks over
  the tree (hard pass/fail, CI-gateable) and spawns the reviewer per area for the semantic rules.
- **`/write-adr`** — generate an ADR in `docs/adr/` (house Nygard format, next number with the
  project's existing prefix width auto-detected) from the current phase's decision log.

## Upgrade safety

Because nothing patches vendor files, **`gsd-update` is a no-op** for enforcement — no `--reapply`,
nothing to merge, nothing to orphan. The one shared file we touch, `.claude/settings.json`, is safe
too: it is **not** a GSD-manifested artifact, and GSD's hook writer **merges and preserves** foreign
hook entries (verified in `runtime-hooks-surface.cts`), so our PreToolUse entry survives upgrades
untouched. No ongoing verify check is needed (an earlier draft had one — dropped); the installer
validates `index.yaml` once at install time, and the hook self-degrades loudly if it later goes
missing.

## Migrating from the patched installer

If the old patch-based installer was applied to a project:

1. Restore `code-review.md`, `discuss-phase.md`, and `gsd-code-reviewer.md` from
   `.claude/gsd-local-patches/pristine/`; delete the orphaned `write-adrs.md`. (Restoring
   `code-review.md` drops the old `--audit` flag — its replacement is `/standards-audit`.)
2. Remove the `gsd-standard-enforcement` entry from `gsd-local-patches/backup-meta.json` so
   `--reapply` no longer targets it.
3. Run `./install.sh`.
4. Verify (see the acceptance criteria in the spec).

## Developing this package

```
gsd-standards-guard/
  install.sh                         # thin Bash installer (+ --uninstall)
  skills/gsd-standards-guard/        # the rule engine (engine.js) — code, not a prompt-skill
  skills/write-adr/                  # /write-adr prompt-skill
  skills/standards-audit/            # /standards-audit prompt-skill
  hooks/gsd-standards-guard.js       # PreToolUse hook (thin engine caller)
  templates/                         # index.yaml seed, ARCHITECTURE.md + STANDARDS.md skeletons, CLAUDE.md block, merge-settings.js
  tests/engine.test.js               # engine regression suite (AC2/AC2b/AC2c/AC8 + degrade)
  gsd-standards-guard-redesign.md    # the source-of-truth spec
```

`install.sh` maps `skills/*` and `hooks/*` into the target project's `.agents/`, wires the
PreToolUse entry via `templates/merge-settings.js`, and seeds the docs contract. Run the tests with:

```bash
node --test tests/*.test.js
```

## See also

- [`gsd-standards-guard-redesign.md`](./gsd-standards-guard-redesign.md) — the full specification
  (components, acceptance criteria, risks, migration).
