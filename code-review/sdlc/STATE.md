# State — last updated 2026-05-30

**Active focus:** **None — `polyreview 0.1.0` is GA on PyPI.** `epic-analyzer-ga-hardening` (s0–s7) is shipped and closed; the epic merged to `main` via PR #1 (`f8e2921`) and the `code-review-v0.1.0` tag drove `release.yml` → **published `0.1.0` (wheel + sdist) to real PyPI** (verified live). Local `main` == `origin/main` (clean). Operator decides the next epic.
**Last completed:** **GA release `polyreview 0.1.0`** — PR #1 (`ccglass-traffic-analysis`→`main`) merged after green CI + a full manual smoke test (real wheel: `uv build`→`pip install`→`install`→`run`→`uninstall`, all passed). Epic-close done: README gained a "Use as an Agent Skill" section (install/uninstall); `adr-0016/0017/0018` filed to `docs/decisions/`; epic → `work/done/`; version `0.1.0rc1`→`0.1.0`. Release workflow build→smoke→publish all green.
**Next:** No active SDLC work. Post-GA follow-ups below are unplanned — operator picks what to compile/plan next.

## Open questions / follow-ups

- **`claude-code-review` redirect meta-package** (ADR-0014): now due — publish after the first GA publish (which just happened). Own task.
- **Merged branch `ccglass-traffic-analysis`** still exists on local + origin; delete it (operator authorises branch deletion) now that PR #1 is merged.
- **GA supply-chain gate (open since s3):** no dependency-audit gate (SDLC #26 skipped per "no gate ⇒ skip"). `npm audit` reports 5 pre-existing transitive vulns (picomatch/micromatch ReDoS, smol-toml DoS) — wheel-excluded, offline, local-only. Decide whether to wire an audit gate (ADR) / `npm audit fix`.
- **Diff-path resolution (open since s4):** `resolve_diff_paths` returns repo-relative paths, orchestrator `abspath`s against `Path.cwd()` (cli.py) — a `--diff` review from a subdir mis-resolves; affects all adapters. Resolve against repo root. Own task.
- **s7 deferred Minors:** install/uninstall refusal-message wording diverges; `cli.py` duplicates comma-split + `resolve_targets` + echo loop (hoist `_resolve_targets_or_exit`); all-no-op summary asymmetric vs install.
- **s6 deferred Minors:** `install --force` is `rmtree`-then-copy (harden to copy-to-temp + atomic rename); mixed `--all` refusal prints cache hint before `Exit(1)`; bundle `code-review.toml.example` cross-refs `python -m code_review.cli --help` (align to `run`).
- **Stale doc:** `stack-pins.md` references `scripts/license_audit.py` which doesn't exist; add the gate (ADR) or correct stack-pins. Open since s1.

## Recent shipped

- **(2026-05-30) `polyreview 0.1.0` GA on PyPI** — PR #1 merged (`f8e2921`), tag `code-review-v0.1.0` → `release.yml` published wheel + sdist. Smoke-tested end-to-end on the real wheel.
- **(2026-05-30) epic-analyzer-ga-hardening CLOSED** — s0–s7: F3 semgrep, F5+F9 JS toolchain, F2 jscpd, F1 depcruiser, F8 eslint, F10 CLI errors, `polyreview install`/`uninstall` + CLI restructure to `polyreview run`.
- **(prior) `polyreview 0.1.0rc1`** on TestPyPI.
