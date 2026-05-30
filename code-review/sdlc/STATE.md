# State — last updated 2026-05-30

**Active focus:** **`epic-analyzer-polish` / story `s0-analyzer-adapter-robustness`** (4 tasks, tests-first). **ADR-0019 ACCEPTED** (operator-ratified: introduce `unavailable` status as a clean skip distinct from `error`; eslint graceful-skip, not default-config). **s0-t0 CLOSED** (bandit progress-bar fix). **t1–t3 still active.** Halted at the t0 clean boundary per the SDLC context-pressure rule (very long session). Resume with `/clear` → "resume s0-t1". `polyreview 0.1.0` is **GA on PyPI** (epic-analyzer-ga-hardening shipped, on `main`).
**Last completed:** **s0-t0-bandit-stdout-progress-bar** (`c119617`) — `--quiet` + strip-to-first-`{` before json.loads; bandit no longer crashes on its Rich progress-bar stdout. Verify PASS, Review MINOR-ONLY. 3 mocked tests. ADR-0019 ratification committed alongside.
**Next:** **s0-t1-eslint-no-flat-config** (F4, Important). Per ADR-0019: when no `eslint.config.*` is discoverable upward from the target anchor, return `status: unavailable` (reason names missing flat config), NOT a bare `eslint exited 2`. **Implementation prereq — thread the new `unavailable` status:** check `code_review/contracts.py` `AnalyzerOutput.status` type (add `unavailable` if it's a Literal); check `code_review/schemas/review-response.json` for a status enum (add it); CLI `has_error` keys on `=="error"` so `unavailable` is already benign there; confirm the aggregator treats an empty-sarif unavailable output benignly. Then t2 (JS analyzers `unavailable` on no-JS targets) reuses the same plumbing; t3 (schemathesis surface-exec-error) is independent.

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
