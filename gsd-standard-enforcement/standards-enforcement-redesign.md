# Specification — Standards Enforcement, redesigned

> **Status:** Draft (rev. 2) · **Date:** 2026-07-17 · **Supersedes:** the `gsd-standard-enforcement`
> patch-based installer (`from_version: 1.6.0`, backed up 2026-06-27).
> **Owner:** project (not GSD).
>
> **Rev. 2 change:** enforcement is now **selective and glob-keyed**. The ADR corpus was
> triaged into a standing-rule ledger with a machine-readable mirror
> (`docs/adr/index.yaml`); the hook injects only the rules whose file-globs match the diff,
> not the whole ADR set. Components **already built:** the ARCHITECTURE.md standing-rule
> ledger (§5.3) and `docs/adr/index.yaml` (§5.7). Still pending: the hook, `/write-adr`,
> CLAUDE.md block, installer, migration.

## 1. Problem

The current `gsd-standard-enforcement` "skill" is an installer that **content-patches
four vendor-owned GSD files** so GSD's own agents read this project's governance docs:

| Patched file | Injects |
|---|---|
| `agents/gsd-code-reviewer.md` | "read & enforce `docs/ARCHITECTURE.md` / `docs/STANDARDS.md` / non-superseded `docs/adr/*`" |
| `gsd-core/workflows/code-review.md` | wires the above into the review flow |
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
  touches it. `.claude/settings.json` is git-tracked and left empty by GSD (GSD writes its Claude
  hooks to the gitignored `settings.local.json`); Claude Code merges both hook sets. (`settings.json`
  *is* in GSD's manifest — a low residual-risk surface, addressed in §6.)
- **ADR numbering is 3-digit zero-padded** (`001`…`065`). The patched `write-adrs.md` greps
  `^[0-9]{4}` (4-digit) — a latent defect to fix in the port.
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
- Rewriting `docs/STANDARDS.md` (separate task; it may carry similar drift — see §9).

## 4. Design principles

1. **Own your files.** Enforcement lives in project-owned locations GSD cannot overwrite.
2. **Mechanism over guidance.** Prefer a deterministic hook to a discretionary CLAUDE.md line.
3. **Decisions live in ADRs, not prose.** ARCHITECTURE.md points; it does not restate.
4. **Fail loud, not silent.** Any degradation must surface, never disappear quietly.
5. **Idempotent & reversible.** Install/uninstall are surgical and re-runnable.

## 5. Components

The redesigned skill installs and owns these project-owned artifacts plus a docs contract:
a selective code-review hook (5.1), a `/write-adr` skill (5.2), the ARCHITECTURE.md + ADR
rule-index contract (5.3, 5.7), a CLAUDE.md backstop (5.4), and the installer (§6).

### 5.1 Code-review enforcement — native hook (primary mechanism)

- **Type:** Claude Code `PreToolUse` hook, project-owned.
- **Script:** `.agents/hooks/standards-guard.js` — **not** `.claude/hooks/` (20 GSD-managed,
  `{{GSD_VERSION}}`-templated scripts live there, and prune-migrations delete orphans).
- **Config:** a marked block in `.claude/settings.json` (`hooks.PreToolUse`), referencing the
  script via `$CLAUDE_PROJECT_DIR`.
- **Behavior (default "advisory" mode):** when the code-review flow runs, the hook (a) reads the
  changed-file list, (b) matches each path against the `globs` in `docs/adr/index.yaml` (§5.7),
  and (c) injects `additionalContext` carrying the enforcement directive (§5.6) plus **only the
  matching standing rules** (each is a one-line `rule` + `adr` pointer). It never injects the
  superseded or historical ADRs, and never the whole corpus. Mirrors `gsd-read-guard.js`'s
  injection shape; the diff is obtained from the phase manifest or `git diff --name-only`.
- **Why glob-keyed:** a frontend charting change injects rules 042/043/044 (~3 short lines), not
  46 rules or 65 ADR bodies — deterministic *and* minimal-token. If `index.yaml` is missing, the
  hook degrades to injecting the directive + a "consult `docs/ARCHITECTURE.md` decision index"
  pointer (fail-loud, not silent-skip).
- **Scoping (the real design work):** must fire only in the review context, not on every
  project edit. Candidate signals, in preference order:
  1. the `gsd-code-reviewer` **subagent** is active (tightest — pure review scope);
  2. the tool target is the phase `REVIEW.md`;
  3. a marker the `/gsd-code-review` workflow sets in the environment.
  **Default:** subagent-scoped (1), falling back to (2). Broadening to "any structural edit"
  is a config toggle (`scope: review | structural`) for teams that want enforcement on
  hand-written code too — at higher token cost.
- **Strict mode (optional):** a blocking check on `REVIEW.md` — deny completion unless it
  cites at least the governing docs. Deterministic hard gate; carries false-positive-block
  risk, so **off by default**.
- **Open dependency:** whether a `PreToolUse` hook fires *inside* a subagent and its
  `additionalContext` reaches the subagent's model must be validated before relying on signal
  (1). See §9 / §8-AC5.

### 5.2 ADR generation — project-owned `/write-adr` skill

- **Location:** `.agents/skills/write-adr/SKILL.md` (+ `rules/` if the template grows).
- **Content:** the house Nygard format and section headings ported **verbatim** from the
  current patched `write-adrs.md` — ADR output does not change.
- **Numbering:** next = `max(existing 3-digit prefix) + 1`, zero-padded to **3 digits**
  (fix the 4-digit `^[0-9]{4}` defect). Skip-if-`docs/adr/`-absent guard retained.
- **Invocation:** manual, at discuss/ship time (`/write-adr`), reading the phase
  `CONTEXT.md`/decision log. Trade-off vs the old auto-fire inside `/gsd-discuss-phase`: an
  explicit-but-reliable step replaces an auto step that silently dies on upgrade — net positive.
- **Optional convenience:** a `SessionStart`/CLAUDE.md reminder to run `/write-adr` when a
  phase logged load-bearing decisions.

### 5.3 ARCHITECTURE.md authoring contract — standing-rule ledger  *(built)*

The skill defines and lints the shape of `docs/ARCHITECTURE.md` (already migrated to this form):

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

### 5.7 ADR rule index — `docs/adr/index.yaml`  *(built)*

The machine-readable mirror of the §5.3 ledger and the selector the §5.1 hook consumes.

- **Location:** `docs/adr/index.yaml` (project-owned, upgrade-proof).
- **Schema:** `version`, `adr_dir`, then three buckets:
  - `rules[]` — `{adr, area, rule, globs[]}`. `rule` is the enforceable one-liner; `globs` are
    repo-root-relative selectors (backend paths under `backend/src/funding_data/`, spelled out).
  - `superseded{}` — `adr → "→ successor (why)"`. Never read.
  - `historical{}` — `adr → "one-line reason"`. Context only.
- **Invariants (enforced by the §5.3 lint):** every ADR `001..N` appears in **exactly one**
  bucket; every `rules` entry has ≥1 glob that resolves to a real path; the MD ledger and this
  file agree row-for-row.
- **Consumers:** the enforcement hook (§5.1, selective injection) and humans via the rendered
  ledger in ARCHITECTURE.md. Single source, two renderings.
- **Current contents:** 46 standing rules, 15 superseded, 4 historical (full 65-ADR coverage,
  validated). The answer-harness rows (026/027/031/037-039) involved supersession-chain judgment
  calls, placed by where current code points — flagged for spot-check (§9).

## 6. Install / uninstall / upgrade

- **Installer:** a committed, idempotent script (`.agents/skills/standards-enforcement/install.*`;
  language to match repo tooling). It:
  1. writes `.agents/hooks/standards-guard.js`;
  2. inserts the marked `hooks.PreToolUse` block into `.claude/settings.json`;
  3. inserts the marked directive block into `CLAUDE.md`;
  4. ensures `.agents/skills/write-adr/` is present;
  5. never touches any file under `.claude/gsd-core/` or `.claude/agents/`.
- **Idempotency:** all edits are delimited by `# >>> standards-enforcement >>>` /
  `# <<< standards-enforcement <<<` markers; re-running replaces the block in place.
- **Uninstall:** removes only the marked blocks and the project-owned files. Leaves vendor files
  untouched (they were never patched).
- **Upgrade behavior:** because nothing patches vendor files, `gsd-update` is a **no-op** for
  enforcement — no `--reapply`, nothing to merge, nothing to orphan.
- **Residual risk mitigation (settings.json ∈ GSD manifest):** ship a lightweight
  **verification check** (a `SessionStart` hook or an `install --verify` mode) that asserts (a)
  the marked hook block is still present in `settings.json`, and (b) `docs/adr/index.yaml` exists
  and parses; if a GSD migration removed the hook block or the index is missing/malformed, **fail
  loud** with a one-line reinstall/reconcile instruction. This converts the residual overwrite
  surface and any index breakage from silent to noisy.

### Migration from the current patched state

1. **Revert vendor patches to pristine:** restore `code-review.md`, `discuss-phase.md`, and
   `gsd-code-reviewer.md` from `.claude/gsd-local-patches/pristine/`; **delete** the orphaned
   `write-adrs.md`.
2. **Retire the local-patch record:** remove the `gsd-standard-enforcement` entry from
   `backup-meta.json` (and the patch/pristine copies) so `--reapply` no longer targets it.
3. **Install the new components** (§6 installer).
4. **Verify** (§8).

## 7. File layout & ownership

| Path | Owner | Upgrade-safe | Role |
|---|---|---|---|
| `.agents/hooks/standards-guard.js` | project | ✅ (not in manifest) | deterministic review-context injector |
| `.claude/settings.json` → marked hook block | project | ⚠️ in manifest → §6 verify check | wires the hook |
| `.agents/skills/write-adr/` | project | ✅ | ADR generator (Nygard, 3-digit) |
| `.agents/skills/standards-enforcement/` | project | ✅ | installer + this spec |
| `CLAUDE.md` → marked block | project | ✅ | main-agent backstop directive |
| `docs/ARCHITECTURE.md` | project | ✅ | standing-rule ledger (**built**) |
| `docs/adr/index.yaml` | project | ✅ | machine-readable rule index — hook selector (**built**) |
| `docs/STANDARDS.md`, `docs/adr/*` | project | ✅ | binding standards + decisions |
| ~~`.claude/gsd-core/**`, `.claude/agents/gsd-code-reviewer.md`~~ | GSD | n/a | **no longer patched** |

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
- **AC3 — ADRs generate:** `/write-adr` produces `docs/adr/066-*.md` matching the existing house
  format, correctly numbered (3-digit, `066`).
- **AC4 — clean uninstall:** after uninstall, `git diff` of `.claude/gsd-core/` and
  `.claude/agents/` against the GSD manifest is empty, and no `standards-enforcement` markers
  remain in `settings.json`/`CLAUDE.md`.
- **AC5 — subagent reach validated:** a probe confirms the `PreToolUse` hook fires within the
  `gsd-code-reviewer` subagent and its `additionalContext` reaches that agent (else fall back to
  scope signal 2/3 or the `structural` scope).
- **AC6 — ledger lint:** `docs/ARCHITECTURE.md` passes the ledger lint (no `[TARGET]`/`[CURRENT]`,
  no decision-restating prose, no standing-table reference to a superseded ADR, MD↔`index.yaml`
  in sync).

## 9. Risks & open questions

- **Subagent hook semantics (blocking unknown).** The reliability case for signal (1) assumes
  `PreToolUse` fires inside subagents and injects into their context. **Must be validated (AC5)**
  before build; if false, default to REVIEW.md-target scoping (2) or the `structural` scope.
- **`settings.json` manifest membership.** Low residual overwrite risk; mitigated by the §6
  verify check, not eliminated.
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
- **STANDARDS.md drift.** Out of scope here, but likely carries the same rot ARCHITECTURE.md did;
  recommend a follow-up audit.
- **Naming.** The capability is no longer "gsd-standard-enforcement" (it no longer patches GSD).
  Rename to `standards-enforcement`; keep a note in `backup-meta` cleanup for traceability.
```
