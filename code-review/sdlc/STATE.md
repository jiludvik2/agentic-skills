# State — last updated 2026-05-30

**Active focus:** `epic-analyzer-ga-hardening` (**8 stories, s0–s7**) → **ALL CLOSED**. **s7-uninstall-skill-bundle CLOSED 2026-05-30** (single task s7-t0; Verify PASS, per-task + story-level Review both MINOR-ONLY). **Epic boundary reached** — the epic file is still in `active/` pending **epic close** (Document + File verbs, version bump, GA tag). On branch `ccglass-traffic-analysis` — **16 commits ahead of origin, all UNPUSHED** (operator commits/pushes per AGENTS.md no-push policy). This session = **execution**: built + closed s7 (`polyreview uninstall`).
**Last completed:** **s7 story CLOSED** (`e4f1371`). `polyreview uninstall` removes `<skills-dir>/code-review/` from the s6 registry targets, **marker-gated** (`is_our_bundle`, reused — never `rmtree` a dir failing the marker), scoped by `--agent`/`--all`, idempotent no-op when absent, refusal reported + non-zero exit, siblings/`reviewer.md`/skills-dir/homes untouched. New `uninstall()` in `install.py` + `uninstall` Typer command mirroring `install`. SKILL.md gained an Uninstall section. Suite **413 passed**; ruff + mypy clean.
**Next:** **EPIC CLOSE for `epic-analyzer-ga-hardening`** (operator-gated — paused at epic boundary). Steps: (1) **Document** — reconcile `README.md` (currently documents neither the `install` nor `uninstall` subcommand; operator approves README content); (2) **File** — move `adr-0016/0017/0018` → `sdlc/docs/decisions/`, move the epic file → `done/`; (3) bump `pyproject.toml` → **0.1.0** (release-significant, operator call); (4) operator commits + cuts/pushes GA tag **`code-review-v0.1.0`** (standalone push event). Runbook: `sdlc/docs/runbooks/release.md`.

## Open questions / follow-ups

- **GA supply-chain follow-up (open since s3):** no dependency-audit gate defined (SDLC #26 skipped per "no gate ⇒ skip"). `npm audit` reports **5 pre-existing** transitive vulns (picomatch/micromatch ReDoS, smol-toml DoS) — wheel-excluded, offline, local-only. Decide before GA whether to wire an audit gate (ADR) / `npm audit fix`.
- **Diff-path resolution (open since s4):** `resolve_diff_paths` returns repo-relative paths, orchestrator `abspath`s against `Path.cwd()` (cli.py:142) — a `--diff` review from a subdir mis-resolves; affects all adapters. Resolve against repo root. Own task.
- **s7 deferred Minors (opportunistic):** install/uninstall refusal-message wording diverges; `cli.py` duplicates comma-split + `resolve_targets` + echo loop (hoist `_resolve_targets_or_exit` helper); all-no-op summary handled asymmetrically vs install.
- **s6 deferred Minors:** `install --force` is `rmtree`-then-copy (harden to copy-to-temp + atomic rename); mixed `--all` refusal prints cache hint before `Exit(1)`; bundle `code-review.toml.example` cross-refs `python -m code_review.cli --help` (align to `run`).
- **Stale doc:** `scripts/license_audit.py` referenced by `stack-pins.md` but the file doesn't exist; add the gate (ADR) or correct stack-pins. Open since s1.
- **`claude-code-review` redirect meta-package** (ADR-0014): publish after first GA publish.
- **`analyze_ccglass.py`** carries 22 ruff errors on this branch (pre-existing, out of epic scope).

## Recent shipped

- **(2026-05-30) s7-uninstall-skill-bundle CLOSED** (`e4f1371`, `4ec9936`) — `polyreview uninstall`, marker-gated agent-independent removal (ADR-0018 §5). 9 tests; 413 passed. **Unpushed. Epic boundary.**
- **(2026-05-30) s6-install-skill-bundle CLOSED** (`86badb3`) — `bundle.py` SSOT + `install.py` + `polyreview install` + CLI restructure to `polyreview run`. **Unpushed.**
- **(2026-05-30) s3/s4/s5 CLOSED** — F1 depcruiser, F8 eslint, F10 CLI error branches. **Unpushed.**
- **s0/s1/s2 CLOSED** (F3 semgrep, F5+F9 JS toolchain, F2 jscpd). **Pushed.** `polyreview 0.1.0rc1` on TestPyPI (`main`, e575b37).
