# Specification — gsd-standards-guard (standards enforcement), redesigned

> **Status:** Draft (rev. 3) · **Date:** 2026-07-17 · **Supersedes:** the `gsd-standard-enforcement`
> patch-based installer (`from_version: 1.6.0`, backed up 2026-06-27).
> **Owner:** project (not GSD).
>
> **Rev. 2 change:** enforcement is now **selective and glob-keyed**. The ADR corpus was
> triaged into a standing-rule ledger with a machine-readable mirror
> (`docs/adr/index.yaml`); the hook injects only the rules whose file-globs match the diff,
> not the whole ADR set. Components **already built:** the ARCHITECTURE.md standing-rule
> ledger (§5.3) and `docs/adr/index.yaml` (§5.7).
>
> **Rev. 3 change:** a **single rule engine** (`gsd-standards-guard`) is now the sole authority for
> "given a file set, which rules apply and — where mechanically checkable — are they violated."
> Two **independent** callers feed it a file set: the per-change **hook** (`--scope=diff`, §5.1)
> and a **manually-invoked whole-codebase audit** (`--scope=all`, §5.8). This re-homes the old
> installer's `--audit` flag — previously a **patch to `code-review.md`** — into a project-owned
> command, so full-codebase compliance survives GSD upgrades like everything else. `index.yaml`
> gains an optional per-rule `check:` field (§5.7) for the deterministic tier. Still pending: the
> engine + hook, `/standards-audit`, `/write-adr`, CLAUDE.md block, installer, migration.
>
> **Rev. 4 change (reconciliation):** two layers are now separated explicitly (§5 intro, §7) — the
> **reusable package** (this repo: engine, hook, `/write-adr`, `/standards-audit`, `install.sh`, the
> `index.yaml` *schema* and the ARCHITECTURE.md *authoring contract* + lint) versus the **project
> instance** (per adopting project: the populated `index.yaml` rule corpus and ARCHITECTURE.md
> ledger). The "already built" ledger + `index.yaml` are the **reference instance** (the
> funding_data backend), included to illustrate the schema — **not** package contents; a fresh
> project starts from a seed and authors its own rows. And `/write-adr` numbering now **detects the
> existing ADR-prefix width** rather than hard-coding 3 digits — the earlier "4-digit defect" was a
> width *mismatch* against one project's files, not a universal error (§2, §5.2, AC3).

## 1. Problem

The current `gsd-standard-enforcement` "skill" is an installer that **content-patches
four vendor-owned GSD files** so GSD's own agents read this project's governance docs:

| Patched file | Injects |
|---|---|
| `agents/gsd-code-reviewer.md` | "read & enforce `docs/ARCHITECTURE.md` / `docs/STANDARDS.md` / non-superseded `docs/adr/*`" |
| `gsd-core/workflows/code-review.md` | wires the above into the review flow **and adds a `--audit` Tier-0 scope** (whole-codebase review via `git ls-files`) |
| `gsd-core/workflows/discuss-phase.md` | `workflow.adr_generation` gate (**patch-invented, not native**) |
| `gsd-core/workflows/discuss-phase/steps/write-adrs.md` | house Nygard ADR writer to `docs/adr/` (**net-new file**) |

Backups sit in `.claude/gsd-local-patches/` with a `backup-meta.json`
(`installer: "gsd-standard-enforcement"`).

**It is one `gsd-update` away from silent failure.** Verified fragilities:

1. **Manifest drift.** All four live files' SHA-256s differ from `.claude/gsd-file-manifest.json`.
   The next update treats them as conflicts — overwrites (killing enforcement) or blocks.
2. **Orphaned step.** `write-adrs.md` is net-new (absent from the manifest, no `pristine/`
   copy). On upgrade it *survives* but the reinstalled `discuss-phase.md` no longer *calls*
   it — ADR generation stops with **no error**. Worst failure mode: invisible.
3. **Broken reapply.** `pristine_hashes: {}` is empty, so GSD's `--reapply` three-way
   merge can't hash-validate.
4. **Dead installer.** The installer referenced by `CLAUDE.md`
   (`python3 ../gsd-api-first/install.py`) and the `gsd-standard-enforcement` installer are
   **not in the repo**. There is currently no working reapply or uninstall path.
5. **Version pin.** The patch is pinned to GSD 1.6.0 file structure; blind reapplication
   after an upstream restructure reintroduces stale text or fails.

## 2. Findings that shape the redesign (all verified against the installed tree)

- **The native GSD 1.6 code-reviewer already reads `./CLAUDE.md`** and is instructed to
  *"Follow all project-specific guidelines, security requirements, and coding conventions
  during review,"* and to check `.claude/skills/` **and `.agents/skills/`**. Enforcement can
  ride these native hooks instead of patching the agent.
- **GSD has no native ADR generation.** The pristine `discuss-phase.md` has zero
  `adr_generation` references and no write-adrs step. Upstream (v1.6.0+37) is building an ADR
  *parser/validation port for GSD's own SDK ADRs* — not a user-facing generator. ⇒ ADR
  generation is **load-bearing custom functionality** and must be preserved, not retired.
- **Planner / codebase-mapper / doc-writer already read the governance docs natively**
  (untouched vs manifest). ⇒ The planning path needs no custom enforcement.
- **Native Claude Code hooks are deterministic and upgrade-proof.** `gsd-read-guard.js`
  demonstrates the pattern: a `PreToolUse` hook injecting `additionalContext`, harness-executed
  regardless of model discretion — strictly more reliable than a CLAUDE.md line.
- **GSD's hooks/capability subsystem is internal** (`runtime-hooks-surface.cjs`,
  `capability-registry.cjs`): it manages GSD's own hooks across runtimes and exposes **no public
  "register my hook" API.** Hooking into it would be another vendor-internal patch. ⇒ Use Claude
  Code's *native* hook surface, not GSD's.
- **`.agents/skills/` is project-owned, git-tracked, and absent from GSD's manifest** — GSD never
  touches it. `.claude/settings.json` is **not a manifested artifact** either (the Claude capability
  manifests only commands, agents, and skills). GSD *does* write its own hook entries into
  `settings.json` (`writesSharedSettings: true`), but its writer **merges and preserves foreign hook
  entries** — it JSON-parses the file, keeps user/legacy entries, and strips only entries it
  classifies as GSD-managed (`gsd-managed` marker / command signature; verified in
  `src/runtime-hooks-surface.cts`, branch `next`). ⇒ Our PreToolUse entry survives `gsd-update`
  untouched — **no residual overwrite risk**, and no verify check required (§6).
- **ADR-prefix width is project-specific.** The reference instance is 3-digit zero-padded
  (`001`…`065`); the shipped `write-adrs.md` payload documents and greps a **4-digit** convention
  (`0001`…) — a *different* project's house style. Neither width is universally correct, so the real
  defect is that the port pins a **fixed** `^[0-9]{4}` grep, which silently mismatches any project
  not on 4 digits (against a 3-digit tree it finds nothing and restarts at `0001`, colliding). The
  fix is width **detection**, not a swap to a different hard-coded width (§5.2).
- **The ADR corpus triages cleanly.** Of 65 ADRs: **46 carry a standing code rule**, **15 are
  dead** (superseded/reversed — never read), **4 are historical/process** (no standing rule). A
  typical diff triggers **2–6 rules**, not the whole set. This is what makes selective,
  glob-keyed enforcement possible — "read every non-superseded ADR" was both expensive and
  wrong (it treated dead and historical ADRs as live). Built as §5.7.

## 3. Goals / non-goals

**Goals**
- Zero patches to vendor-owned GSD files. Vendor-patch surface goes **4 → 0**.
- Code-review enforcement that is **deterministic**, **selective** (only the rules a diff can
  violate), and survives arbitrary GSD upgrades.
- Preserve ADR generation as a project-owned capability.
- `docs/ARCHITECTURE.md` maintained as a **standing-rule ledger**, not decision prose, with a
  machine-readable mirror (`docs/adr/index.yaml`) the hook consumes.
- Idempotent install, clean uninstall, no silent failure on upgrade.

**Non-goals**
- Reimplementing or forking GSD.
- Changing ADR *content* or the house Nygard format.
- Guaranteeing review *verdict correctness* — the mechanism guarantees the rules are **in
  context** (and, in strict mode, gates the output); acting on them remains model judgment.
- Rewriting an existing `docs/STANDARDS.md` (separate task; it may carry similar drift — see §9).
  *(The installer does seed a STANDARDS.md **skeleton** when one is absent, so a fresh project's
  enforcement directive — which cites STANDARDS.md as binding — has a real target; it never
  overwrites an existing file.)*
- **Cross-agent portability.** This skill targets **Claude Code only** — native `PreToolUse`
  hooks wired through `.claude/settings.json`. Support for other agents (Copilot, Gemini, Cursor,
  …) is explicitly out of scope. Project-owned files still live under `.agents/` purely for
  **upgrade-safety** (that tree sits outside GSD's manifest — §2), not for cross-agent reach.

## 4. Design principles

1. **Own your files.** Enforcement lives in project-owned locations GSD cannot overwrite.
2. **Mechanism over guidance.** Prefer a deterministic hook to a discretionary CLAUDE.md line.
3. **Decisions live in ADRs, not prose.** ARCHITECTURE.md points; it does not restate.
4. **Fail loud, not silent.** Any degradation must surface, never disappear quietly.
5. **Idempotent & reversible.** Install/uninstall are surgical and re-runnable.

## 5. Components

The redesigned skill installs and owns these project-owned artifacts plus a docs contract:
a shared rule engine (`gsd-standards-guard`) called by a selective code-review hook (5.1) and a
manual whole-codebase audit (5.8), a `/write-adr` skill (5.2), the ARCHITECTURE.md + ADR
rule-index contract (5.3, 5.7), a CLAUDE.md backstop (5.4), and the installer (§6). Claude Code
only (§3).

**Two layers — package vs. project instance.** This spec describes a *reusable package* that ships
from the `agentic-skills` repo and installs into any adopting GSD project; the concrete rule corpus
is *per-project data* authored once per project. Keep them distinct:

- **Package (shipped by this repo, identical everywhere):** the rule engine (§5.1), the hook (§5.1),
  `/write-adr` (§5.2), `/standards-audit` (§5.8), `install.sh` (§6), the CLAUDE.md directive block
  (§5.4/§5.6), the **`index.yaml` schema** (§5.7), and the **ARCHITECTURE.md authoring contract +
  lint** (§5.3).
- **Project instance (authored per adopting project):** the populated `docs/adr/index.yaml` rule
  rows, the filled-in `docs/ARCHITECTURE.md` ledger, and the ADRs themselves. Globs, ADR numbers,
  and counts are project-specific.

Everything marked *(built)* / *(reference instance)* below — the 46/15/4 corpus, the migrated
ledger, the `backend/src/funding_data/**` globs, the specific ADR numbers (024, 042/043, 066) — is
the **reference instance** (the funding_data backend), included to illustrate the schema, **not**
part of what the package installs. A fresh project starts with a seed `index.yaml` and authors its
own rows against the schema.

**Code vs prompt.** The engine (`gsd-standards-guard`), the hook, and the installer (`install.sh`)
are **code** — plain scripts, not agent-run prompts. Only `/standards-audit` and `/write-adr` are
prompt-skills (they orchestrate subagents / generate prose). The engine lives under `.agents/` as an
executable the hook and the audit invoke; it is not a `SKILL.md`.

### 5.1 Code-review enforcement — native hook (primary mechanism)

**Shared engine.** The hook is a thin caller of a project-owned rule engine, `gsd-standards-guard`
(`.agents/skills/gsd-standards-guard/`). The engine is the **single authority** for: given a file
set, (a) which standing rules apply (glob-match against `docs/adr/index.yaml`, §5.7), and (b)
where a rule carries a `check:` assertion, whether the file set violates it (deterministic tier).
The engine takes a `--scope` (`diff` | `all`) that only selects *how the file set is obtained*.
**Two independent callers** feed it: this per-change hook (`--scope=diff`) and the manual
whole-codebase audit (`--scope=all`, §5.8). One rule table, one matcher, one code path — the two
callers **cannot drift** in what they enforce, and neither depends on the other.

- **Type:** Claude Code `PreToolUse` hook, project-owned.
- **Script:** `.agents/hooks/gsd-standards-guard.js` — **not** `.claude/hooks/` (20 GSD-managed,
  `{{GSD_VERSION}}`-templated scripts live there, and prune-migrations delete orphans).
- **Config:** a `hooks.PreToolUse` **JSON entry** in `.claude/settings.json`, referencing the script
  via `$CLAUDE_PROJECT_DIR` (added/replaced idempotently by command path; GSD's merge writer
  preserves it — §2).
- **Behavior (default "advisory" mode):** when the code-review flow runs, the hook (a) obtains the
  changed-file list (from the phase manifest or `git diff --name-only`), (b) calls
  `gsd-standards-guard --scope=diff` to resolve the **matching standing rules**, and (c) injects
  `additionalContext` carrying the enforcement directive (§5.6) plus only those rules (each a
  one-line `rule` + `adr` pointer). It never injects the superseded or historical ADRs, and never
  the whole corpus. Mirrors `gsd-read-guard.js`'s injection shape. Where a matched rule carries a
  `check:` assertion (§5.7), the engine also evaluates it against the diff; in **strict mode**
  (below) a deterministic violation blocks, and in advisory mode it is surfaced as a pre-noted
  finding in the injected context.
- **Why glob-keyed:** a frontend charting change injects rules 042/043/044 (~3 short lines), not
  46 rules or 65 ADR bodies — deterministic *and* minimal-token. If `index.yaml` is missing, the
  hook degrades to injecting the directive + a "consult `docs/ARCHITECTURE.md` decision index"
  pointer (fail-loud, not silent-skip).
- **Scoping (settled — see AC5).** Signal (1) is confirmed viable: the `PreToolUse` hook stdin
  carries a top-level **`agent_type`** field equal to the subagent type (`gsd-code-reviewer`),
  and it is **absent on main-loop calls**. So the hook scopes to the reviewer with a one-line
  guard — `if (input.agent_type === "gsd-code-reviewer")` — no heuristic needed. Fallback signals,
  should the agent type ever be renamed: (2) the tool target is the phase `REVIEW.md`; (3) a marker
  the `/gsd-code-review` workflow sets in the environment. **Default:** `agent_type`-scoped (1).
  Broadening to "any structural edit" is a config toggle (`scope: review | structural`) for teams
  that want enforcement on hand-written code too — at higher token cost.
- **Fire-once discipline.** The hook fires on *every* matching tool call; inside the reviewer that
  means many `Read`s. Inject on the first matching call per `agent_id` and no-op after (a
  per-`agent_id` sentinel), so the directive lands once and does not re-inject on every read.
- **Strict mode (optional):** a blocking check on `REVIEW.md` — deny completion unless it
  cites at least the governing docs. Deterministic hard gate; carries false-positive-block
  risk, so **off by default**.
- **~~Open dependency~~ — RESOLVED (2026-07-17, probe + source):** a `PreToolUse` hook **does** fire
  inside a Task subagent, its stdin carries `agent_type`/`agent_id` (so the subagent is
  identifiable), and its `hookSpecificOutput.additionalContext` **does** reach the subagent's model
  (the subagent acted on an injected directive). Tested with a `general-purpose` subagent on Claude
  Code 2.1.212; `agent_type` equals the spawn's `subagent_type`. The reviewer's exact string is
  **`gsd-code-reviewer`**, confirmed against source (`agents/gsd-code-reviewer.md` frontmatter
  `name: gsd-code-reviewer`; `code-review.md` spawns `subagent_type="gsd-code-reviewer"`, branch
  `next`). See §8-AC5.

### 5.2 ADR generation — project-owned `/write-adr` skill

- **Location:** `.agents/skills/write-adr/SKILL.md` (+ `rules/` if the template grows).
- **Content:** the house Nygard format and section headings ported **verbatim** from the
  current patched `write-adrs.md` — ADR output does not change.
- **Numbering (width-detecting):** read the existing prefix width from `docs/adr/` (the digit-count
  of the current highest-numbered ADR), then next = `max(existing numeric prefix) + 1`, zero-padded
  to **that same width** — `066` in the 3-digit reference instance, `0067` in a `0001`-style project.
  This replaces the old fixed `^[0-9]{4}` grep, which silently mismatches any project not on 4
  digits (§2). Skip-if-`docs/adr/`-absent guard retained; when `docs/adr/` is present but empty, fall
  back to a documented default width (3) starting at `001`.
- **Invocation:** manual, at discuss/ship time (`/write-adr`), reading the phase
  `CONTEXT.md`/decision log. Trade-off vs the old auto-fire inside `/gsd-discuss-phase`: an
  explicit-but-reliable step replaces an auto step that silently dies on upgrade — net positive.
- **Optional convenience:** a `SessionStart`/CLAUDE.md reminder to run `/write-adr` when a
  phase logged load-bearing decisions.

### 5.3 ARCHITECTURE.md authoring contract — standing-rule ledger  *(contract = package; reference ledger built)*

The package defines and lints the shape of `docs/ARCHITECTURE.md`; each project authors its own
content to that shape (the reference instance is already migrated to this form):

- **Sections, and only these:** (a) governance banner (authority order + drift discipline),
  (b) context/pipeline sketch, (c) repo layout, (d) serving-layer boundary table,
  (e) invariants ("we never do X"), (f) **decision index — the standing-rule ledger** (see below),
  (g) further reading.
- **The decision index is a three-tier ledger, not a topic map:**
  1. **Standing rules** — a table, one row per live rule: `ADR · binding rule (one line) ·
     Applies to (path globs)`. The reader checks the rule without opening the ADR; opens
     `docs/adr/<NNN>-*.md` only for rationale/edge detail.
  2. **Superseded — do not read** — a collapsed line of `NNN→successor` arrows; steers readers
     away from reversed decisions.
  3. **Historical / process** — number + title only, "context, no rule."
- **Prohibited:** prose that restates a decision an ADR owns; `[TARGET]`/`[CURRENT]` scaffolding
  once the component is built; version numbers; topic→ADR-number rows without a binding rule + globs.
- **Authority order (stated in the file):** `docs/adr/*` (binding, append-only) > `docs/STANDARDS.md`
  > this file. If this file disagrees with an ADR, the ADR wins — fix this file.
- **Drift discipline:** reconcile the ledger **and its `index.yaml` mirror** at every `/gsd-ship`,
  not "~2×/year." A new ADR is unindexed (⇒ unenforced) until it gets a rule row + globs; a
  superseded ADR moves from the standing table to the superseded line in the same change.
- **Lint (advisory, part of the skill):** flag `[TARGET]`/`[CURRENT]` markers, decision-shaped
  prose, standing-table references to a superseded ADR, **and drift between the MD ledger and
  `index.yaml`** (every standing row ↔ one YAML `rules` entry; full 1..N ADR coverage across the
  three buckets, no ADR in two buckets).

### 5.4 CLAUDE.md backstop

A single marked block for the main-agent path (near-zero cost; belt-and-suspenders behind the hook):

- An explicit **review** directive (not the current "before any structural work" framing, which a
  reviewer subagent may not map to "review").
- A pointer to the ADR + STANDARDS authority order.

### 5.5 Governance docs — layout (unchanged, already correct)

`docs/ARCHITECTURE.md` (index) · `docs/STANDARDS.md` · `docs/adr/*.md`. Project-owned,
upgrade-proof. **No relocation.** The ADRs are the binding decision record; glob them.

### 5.6 The enforcement directive (canonical text, used by 5.1 and 5.4)

> **Standards enforcement (code review):** Treat `docs/ARCHITECTURE.md` (invariants +
> standing-rule ledger), `docs/STANDARDS.md`, and the standing rules injected below as
> **binding**. The injected rules are the ones whose file-globs match the changed files — apply
> those; you need not read the full ADR corpus. Any code that contradicts a rule is a finding —
> cite the source (e.g. "violates ADR-024 — view DDL must run at the composition root, not in a
> repository"). Open `docs/adr/<NNN>-*.md` only when a rule is ambiguous for this change. Do not
> infer rules beyond these documents; they define the standard.

*(In the CLAUDE.md backstop, "injected below" becomes "the rules in `docs/adr/index.yaml` whose
globs match the files you are changing.")*

### 5.7 ADR rule index — `docs/adr/index.yaml`  *(schema = package; reference index built)*

The machine-readable mirror of the §5.3 ledger and the selector the §5.1 hook consumes. The package
ships the **schema and validator**; each project authors the **content** (rows/globs/checks).

- **Location:** `docs/adr/index.yaml` (project-owned, upgrade-proof).
- **Schema:** `version`, `adr_dir`, then three buckets:
  - `rules[]` — `{adr, area, rule, globs[], check?}`. `rule` is the enforceable one-liner; `globs`
    are repo-root-relative selectors (backend paths under `backend/src/funding_data/`, spelled
    out). `check` is **optional** — the deterministic tier (below).
  - `superseded{}` — `adr → "→ successor (why)"`. Never read.
  - `historical{}` — `adr → "one-line reason"`. Context only.
- **Two-tier rules (the `check:` field).** A rule with no `check` is **semantic** — the engine
  only injects it into the reviewer's context (model judges compliance). A rule with a `check` is
  **deterministic** — the engine mechanically verifies it and emits a hard pass/fail. `check` is a
  small declarative assertion the engine can evaluate without a model, e.g.
  `{forbid_pattern: "CREATE VIEW", in_globs: ["**/repositories/**"]}` or
  `{require_absent: "import requests", in_globs: ["**/adapters/**"]}`. Keep the vocabulary small
  and declarative (forbid/require a pattern within a path set); anything needing real semantic
  judgment stays a semantic rule. Both tiers run at **both scopes** — the hook evaluates them over
  the diff (§5.1), the audit over the whole tree (§5.8).
- **Invariants (enforced by the §5.3 lint):** every ADR `001..N` appears in **exactly one**
  bucket; every `rules` entry has ≥1 glob that resolves to a real path; the MD ledger and this
  file agree row-for-row.
- **Consumers:** the enforcement hook (§5.1, selective injection) and humans via the rendered
  ledger in ARCHITECTURE.md. Single source, two renderings.
- **Reference instance (funding_data), for illustration — not shipped by the package:** 46 standing
  rules, 15 superseded, 4 historical (full 65-ADR coverage, validated). The answer-harness rows
  (026/027/031/037-039) involved supersession-chain judgment calls, placed by where current code
  points — flagged for spot-check (§9). A fresh adopting project ships a seed `index.yaml` (schema
  header + empty buckets) and authors its own rows against this schema.

### 5.8 Whole-codebase audit — manual `/standards-audit` command

The second caller of the §5.1 engine, for periodic full-codebase compliance sweeps (pre-release,
scheduled, or CI). It **re-homes the old installer's `--audit` flag** — which was a patch to
`code-review.md` — into a project-owned command with **zero vendor surface**.

- **Location:** `.agents/skills/standards-audit/SKILL.md`.
- **Trigger:** manual only (`/standards-audit`). Not automatic, not wired into the hook or the
  phase workflow — it owns its whole invocation. (Manual invocation is an accepted design point:
  audits are periodic, not per-change.)
- **File set:** `gsd-standards-guard --scope=all` = `git ls-files`, minus vendored/generated paths
  (same exclusions as the review workflow's post-processing).
- **Behavior:**
  1. **Deterministic tier** — run every `check:` rule (§5.7) whose globs match a tracked file over
     the whole tree; emit hard violations directly (no model). This is the CI-gateable core: the
     command **exits non-zero** if any deterministic check fails.
  2. **Semantic tier** — for the matching semantic rules, spawn the native `gsd-code-reviewer`
     subagent per area (chunked by `index.yaml` area, so each pass gets only its own rules injected
     — selective and token-minimal, exactly like the hook). Collect findings into a rollup report
     (e.g. `docs/reviews/audit-<date>.md` or per-area files).
- **Why not the hook / `--files`:** because the audit is manual and standalone, it needs no marker
  threaded into the hook and no routing through GSD's phase-centric `--files` tier. It calls the
  engine directly and spawns the reviewer directly — no fake phase, no vendor patch. The reviewer
  is a native GSD agent; invoking it is not a patch.
- **Relationship to the hook:** same engine, same `index.yaml`, same rules — different `--scope`
  and different file-set source. The hook and the audit **cannot drift** in what they enforce, and
  neither depends on the other (§5.1).

## 6. Install / uninstall / upgrade

- **Skill-first, thin shell installer** (mirrors the `gsd-api-first` layout: `skills/`,
  `templates/`, a small `install.sh`). The skills **are** the deliverable — the engine, `/write-adr`,
  and `/standards-audit` are ordinary project-owned files under `.agents/skills/`, and the hook is
  a plain script under `.agents/hooks/`; once present in the project they need no "activation"
  (Claude Code discovers the skills; the hook is referenced by path). The installer exists only for
  the two things that are *not* self-contained files — editing shared config. It is a small,
  idempotent **`install.sh`** (Bash, no Python) that:
  1. copies the package's `skills/` + hook into the target project's `.agents/`;
  2. adds/replaces our `hooks.PreToolUse` **JSON entry** in `.claude/settings.json` — a proper JSON
     entry keyed by the hook command (settings.json is strict JSON, so no comment markers; GSD's own
     merge writer preserves it);
  3. inserts the marked directive block into `CLAUDE.md`;
  4. verifies `docs/adr/index.yaml` exists and parses (fail loud otherwise);
  5. seeds `docs/ARCHITECTURE.md` + `docs/STANDARDS.md` skeletons **only if absent** (never
     overwrites authored docs), so the enforcement directive's cited files always resolve;
  6. never touches any file under `.claude/gsd-core/` or `.claude/agents/`.
  All the patch/backup/pristine/`--reapply` machinery of the old `install.py` is **deleted** —
  with zero vendor patches there is nothing to back up or reapply.
- **Idempotency:** the `CLAUDE.md` edit is delimited by `# >>> gsd-standards-guard >>>` /
  `# <<< gsd-standards-guard <<<` comment markers; re-running replaces the block in place. The
  `settings.json` edit is a JSON hook entry matched by its command path (add-or-replace, preserving
  every other entry — the same merge discipline GSD uses). Copied skill files overwrite in place.
- **Uninstall:** removes only the marked blocks and the project-owned files. Leaves vendor files
  untouched (they were never patched).
- **Upgrade behavior:** because nothing patches vendor files, `gsd-update` is a **no-op** for
  enforcement — no `--reapply`, nothing to merge, nothing to orphan.
- **No ongoing verify check (dropped).** An earlier draft shipped a `SessionStart`/`--verify` probe
  to detect our hook block being removed from `settings.json`. It is unnecessary: (a) GSD's writer
  merges and **preserves** foreign hook entries (§2), so `gsd-update` cannot silently remove ours;
  and (b) a missing/malformed `index.yaml` is already handled **inline** by the hook, which
  self-degrades to a fail-loud pointer (§5.1). The installer still validates `index.yaml` **once at
  install time** (step 4) — a one-shot check, not a per-session hook.

### Migration from the current patched state

1. **Revert vendor patches to pristine:** restore `code-review.md`, `discuss-phase.md`, and
   `gsd-code-reviewer.md` from `.claude/gsd-local-patches/pristine/`; **delete** the orphaned
   `write-adrs.md`. (Restoring `code-review.md` drops the `--audit` flag — its replacement,
   `/standards-audit` (§5.8), is installed in step 3, so the capability is preserved, not lost.)
2. **Retire the local-patch record:** remove the `gsd-standard-enforcement` entry from
   `backup-meta.json` (and the patch/pristine copies) so `--reapply` no longer targets it.
3. **Install the new components** (§6 installer).
4. **Verify** (§8).

## 7. File layout & ownership

Split by layer (§5 intro). Every row is project-owned at rest and upgrade-safe (none sit in GSD's
manifest); the split is about *who authors the content*, not who owns the file.

**Package — installed identically into every adopting project (this repo is the single source):**

| Path | Layer | Role |
|---|---|---|
| `.agents/skills/gsd-standards-guard/` | package | **shared rule engine** — glob-match + deterministic `check:` tier; sole authority (§5.1) |
| `.agents/hooks/gsd-standards-guard.js` | package | thin `PreToolUse` caller → engine `--scope=diff` |
| `.agents/skills/standards-audit/` | package | manual whole-codebase audit → engine `--scope=all` (§5.8) |
| `.agents/skills/write-adr/` | package | ADR generator (Nygard, **width-detecting** — §5.2) |
| `.claude/settings.json` → PreToolUse JSON entry | package (installer-written) | wires the hook; GSD merges & preserves foreign hooks |
| `CLAUDE.md` → marked block | package (installer-written) | main-agent backstop directive (fixed text, §5.6) |
| `install.sh` + `skills/` + `templates/` | package (repo) | thin shell installer + this spec |

**Instance — authored once per adopting project (the package ships the schema/contract, not the content):**

| Path | Layer | Role |
|---|---|---|
| `docs/adr/index.yaml` | instance content · package schema (§5.7) | machine-readable rule index — hook/audit selector |
| `docs/ARCHITECTURE.md` | instance content · package contract + lint (§5.3) | standing-rule ledger |
| `docs/STANDARDS.md`, `docs/adr/*` | instance | binding standards + decisions |

The reference instance (funding_data) has the two authored artifacts **built**; a fresh project
authors its own from the seed.

~~`.claude/gsd-core/**`, `.claude/agents/gsd-code-reviewer.md`~~ — GSD-owned, **no longer patched**.

## 8. Acceptance criteria

- **AC1 — survives upgrade:** after simulating an update (overwrite the three previously-patched
  gsd-core files with their pristine copies), a `/gsd-code-review` run still receives the
  enforcement directive in context.
- **AC2 — enforces:** seed a change that violates a specific ADR *whose globs match the changed
  file*; the review surfaces it, citing the ADR.
- **AC2b — selective injection:** a change under one area (e.g. `frontend/components/answer-types/
  chart-answer.tsx`) injects only that area's rules (042/043), **not** unrelated rules
  (extraction/FX) and **not** any superseded/historical ADR.
- **AC2c — index integrity:** `index.yaml` parses; all `001..N` ADRs appear in exactly one bucket;
  every `rules` glob resolves to a real path; the MD ledger and `index.yaml` agree row-for-row.
  *(Currently passing: 46/15/4, 65-ADR coverage.)*
- **AC3 — ADRs generate (width-preserving):** `/write-adr` produces the next ADR matching the
  existing house format and **preserving the project's prefix width** — `docs/adr/066-*.md` in the
  3-digit reference instance, `docs/adr/0067-*.md` in a 4-digit project. A single hard-coded width
  fails this AC against one of the two.
- **AC4 — clean uninstall:** after uninstall, `git diff` of `.claude/gsd-core/` and
  `.claude/agents/` against the GSD manifest is empty, and no `gsd-standards-guard` markers
  remain in `settings.json`/`CLAUDE.md`.
- **AC5 — subagent reach validated ✅ (2026-07-17):** probe confirmed on Claude Code 2.1.212 that
  a `PreToolUse` hook (a) fires inside a Task subagent, (b) receives `agent_type`/`agent_id` in its
  stdin (main-loop calls omit `agent_type`), and (c) delivers `additionalContext` into the
  subagent's model, which acts on it. ⇒ scope signal (1) via `agent_type === "gsd-code-reviewer"`
  (exact string confirmed against gsd-core source, branch `next`). No residual.
- **AC6 — ledger lint:** `docs/ARCHITECTURE.md` passes the ledger lint (no `[TARGET]`/`[CURRENT]`,
  no decision-restating prose, no standing-table reference to a superseded ADR, MD↔`index.yaml`
  in sync).
- **AC7 — whole-codebase audit:** `/standards-audit` enumerates the tree (`git ls-files`), runs the
  deterministic `check:` rules over it, and produces a rollup report. Seeding a deterministic-check
  violation anywhere in the repo makes the command **exit non-zero** and name the rule + file; the
  semantic tier spawns `gsd-code-reviewer` per area with only that area's rules injected.
- **AC8 — single-engine parity (no drift):** for the same file, the hook (`--scope=diff`) and the
  audit (`--scope=all`) resolve the **same** applicable rule set — both call `gsd-standards-guard`
  against the same `index.yaml`; there is no second rule path to diverge.

## 9. Risks & open questions

- **~~Subagent hook semantics~~ — RESOLVED (2026-07-17).** Probe confirmed `PreToolUse` fires
  inside a Task subagent, exposes `agent_type`/`agent_id`, and delivers `additionalContext` to the
  subagent's model. Signal (1) is viable via an `agent_type` match; fallbacks (2)/(3) retained only
  against a future rename of the reviewer agent type. Exact string **`gsd-code-reviewer`** confirmed
  against gsd-core source (branch `next`) — no residual.
- **~~`settings.json` overwrite risk~~ — RESOLVED.** settings.json is not a manifested artifact, and
  GSD's hook writer merges/preserves foreign entries (verified in `src/runtime-hooks-surface.cts`,
  branch `next`). Our entry survives `gsd-update`; no verify check needed. (Corrects an earlier draft
  that assumed manifest membership.)
- **Advisory vs strict.** `additionalContext` guarantees *presence*, not *action*. Teams wanting
  a hard guarantee enable strict mode (blocking `REVIEW.md` gate), accepting false-block risk.
- **Manual ADR generation.** Loses auto-fire inside discuss-phase. Accepted: reliability >
  automation, given the auto path currently dies silently on upgrade. A reminder (§5.2) softens it.
- **Index maintenance drift.** A new ADR is unenforced until someone adds its rule row + globs.
  Mitigated by the §5.3 lint (coverage check flags any ADR absent from all three buckets) run at
  `/gsd-ship` — but the lint must actually run to catch it.
- **Dual-source sync.** The MD ledger and `index.yaml` are two renderings of one truth; they can
  diverge. Mitigated by the row-for-row lint (AC2c/AC6). Longer term, consider generating the MD
  table *from* `index.yaml` so there is one authored source.
- **Answer-harness tier judgment.** 026/027/031/037-039 sit in a heavy supersession/reversal
  chain; their bucket placement reflects current code, not an explicit ADR status field. Spot-check
  on first use; correcting a placement is a one-line move between buckets.
- **Deterministic-check scope creep.** `check:` is a deliberately tiny declarative vocabulary
  (forbid/require a pattern within a path set). Resist growing it into a general linter — a
  too-clever check that hard-blocks on a false positive is worse than a missed semantic finding.
  When a rule needs real judgment, leave it semantic; default to semantic when unsure.
- **Audit semantic-tier scope.** The whole-tree *reviewer* coverage still relies on spawning the
  native `gsd-code-reviewer` per area; a very large area can exceed one subagent's useful context
  (the same limit the old `--audit` had — it warned and downgraded depth). Chunk finer by glob if
  an area is too big. The *deterministic* tier has no such limit (it is script-evaluated).
- **Claude-only scope (deliberate).** Targeting Claude Code alone (§3) departs from the project's
  usual agent-independence. Accepted: the enforcement mechanism *is* a Claude-native hook, with no
  cross-agent equivalent. If cross-agent enforcement is later wanted, the `gsd-standards-guard` engine
  is reusable, but the hook + `settings.json` wiring would need a per-agent port.
- **STANDARDS.md drift.** Out of scope here, but likely carries the same rot ARCHITECTURE.md did;
  recommend a follow-up audit.
- **Naming.** The capability is no longer "gsd-standard-enforcement" (the old patch-based installer).
  **Renamed to `gsd-standards-guard`** (after the rule engine, §5.1); repo folder and spec renamed to
  match. Keep a note in `backup-meta` cleanup for traceability.
```
