# State — last updated 2026-05-30

**Active focus:** **EPIC BOUNDARY — `epic-analyzer-polish`**. Its only story **`s0-analyzer-adapter-robustness` is DONE** (`c362c70`); all 6 children closed (t0 bandit, t1 eslint, t2 eslint/knip, t3 schemathesis, fix1 jscpd, fix2 e2e-coverage). Auto-progress halted at the epic boundary per SDLC — **operator decides next** (see Open questions). `polyreview 0.1.0` is GA on PyPI. Working tree clean; everything committed on `main` (not pushed — operator runs push).
**Last completed:** **story s0 CLOSED** (`c362c70`). The whole `unavailable`-vs-`error` contract (ADR-0019) shipped: bandit progress-bar tolerance; eslint no-flat-config → unavailable; eslint/knip/jscpd no-JS → unavailable (shared `js_base.has_js_files`/`js_unavailable`); schemathesis surfaces exec errors as `schemathesis.execution-error` findings (no more swallow); + characterization tests that `unavailable` threads benignly through aggregator/CLI. 418 tests pass, ruff+mypy clean.
**Next:** **operator decision at the epic boundary** — (a) close `epic-analyzer-polish` (move epic + co-located ADR-0019 to `/sdlc/docs/`; run `document`/`file`; consider a CHANGELOG/README note on the new `unavailable` analyzer status), or (b) open candidate story **s1 — semgrep ruleset breadth** (F5, an ADR-0016 revisit; still unscoped), or (c) leave the epic open and stop here.

## Open questions / follow-ups

- **s0 deferred follow-up candidates** (from closed task notes, none blocking): schemathesis `h_find` strategy-generation swallow (`except Exception: return []`) is the same B110 false-clean class t3 fixed for `call_and_validate` — surface exec errors there too; converge the project-wide `empty_sarif(tool)`-vs-`sarif={}` convention for non-ok outputs; hoist a shared `js_base.target_dir(paths)` (eslint uses commonpath+dirname, knip uses dirname); knip scans only `target_paths[0]` while eslint scans all.

- **`claude-code-review` redirect meta-package** (ADR-0014): now due — publish after the first GA publish (which just happened). Own task.
- **Merged branch `ccglass-traffic-analysis`** still exists on local + origin; delete it (operator authorises branch deletion) now that PR #1 is merged.
- **GA supply-chain gate (open since s3):** no dependency-audit gate (SDLC #26 skipped per "no gate ⇒ skip"). `npm audit` reports 5 pre-existing transitive vulns (picomatch/micromatch ReDoS, smol-toml DoS) — wheel-excluded, offline, local-only. Decide whether to wire an audit gate (ADR) / `npm audit fix`.
- **Diff-path resolution (open since s4):** `resolve_diff_paths` returns repo-relative paths, orchestrator `abspath`s against `Path.cwd()` (cli.py) — a `--diff` review from a subdir mis-resolves; affects all adapters. Resolve against repo root. Own task.
- **s7 deferred Minors:** install/uninstall refusal-message wording diverges; `cli.py` duplicates comma-split + `resolve_targets` + echo loop (hoist `_resolve_targets_or_exit`); all-no-op summary asymmetric vs install.
- **s6 deferred Minors:** `install --force` is `rmtree`-then-copy (harden to copy-to-temp + atomic rename); mixed `--all` refusal prints cache hint before `Exit(1)`; bundle `code-review.toml.example` cross-refs `python -m code_review.cli --help` (align to `run`).
- **Stale doc:** `stack-pins.md` references `scripts/license_audit.py` which doesn't exist; add the gate (ADR) or correct stack-pins. Open since s1.

## Recent shipped

- **(2026-05-30) story s0-analyzer-adapter-robustness CLOSED** (`c119617`, `67f8216`, `7771686`, `9844178`, `e5865b8`, `c362c70`) — ADR-0019 `unavailable`-vs-`error` contract across bandit/eslint/knip/jscpd/schemathesis; story-level Review found 2 Important (jscpd skip; e2e coverage), both remediated as `s0-fix1`/`s0-fix2`.
- **(2026-05-30) `polyreview 0.1.0` GA on PyPI** — PR #1 merged (`f8e2921`), tag `code-review-v0.1.0` → `release.yml` published wheel + sdist. Smoke-tested end-to-end on the real wheel.
- **(2026-05-30) epic-analyzer-ga-hardening CLOSED** — s0–s7: F3 semgrep, F5+F9 JS toolchain, F2 jscpd, F1 depcruiser, F8 eslint, F10 CLI errors, `polyreview install`/`uninstall` + CLI restructure to `polyreview run`.
- **(prior) `polyreview 0.1.0rc1`** on TestPyPI.
