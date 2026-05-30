# State — last updated 2026-05-30

**Active focus:** **EPIC BOUNDARY — `epic-analyzer-polish`** (story s0 DONE, `c362c70`), **+ post-s0 coverage dogfood complete**. Re-ran the full suite vs OWASP **PyGoat** (Python) and **NodeGoat** (JS); assessments filed at `sdlc/docs/qa/analyzer-coverage/results/2026-05-30-{pygoat-python,nodegoat-js}-coverage.md`, gaps captured to `sdlc/raw/post-coverage-eval-findings.md`. Auto-progress halted at the epic boundary — **operator decides next**. `polyreview 0.1.0` GA on PyPI. Tree clean; all on `main` (not pushed).
**Last completed:** **coverage dogfood** (`b9e8280`, `08294ad`). Validated s0 on real repos (bandit 58 SAST on PyGoat vs pre-fix crash; eslint/knip clean `unavailable` skips on both). Coverage verdict: **Python first-party SAST strong**; **JS first-party SAST effectively absent** (semgrep 0 JS rules + eslint unavailable); deps (trivy) + secrets (gitleaks) strong on both. New gaps G1/G2/G6/G7 (see Open questions).
**Next:** **operator decision** — (a) compile the coverage gaps into the next `epic-analyzer-polish` round (lead story **G6: no working JS SAST**; then G1 jscpd scope, G2/G7 dead-code FPs, F5 semgrep breadth), and/or (b) close the current epic (move epic + ADR-0019 to `/sdlc/docs/`, run `document`/`file`), and/or (c) the pending research question on a maintainability-scanner test oracle (see Open questions).

## Open questions / follow-ups

- **Coverage-eval gaps (next epic candidates)** — full detail in `sdlc/raw/post-coverage-eval-findings.md`: **G6 (strategic)** no working first-party JS SAST (semgrep 0 JS rules + eslint unavailable); **G1** jscpd scans HTML/CSS/Py despite documented JS-only scope; **G2/G7** dead-code FPs (vulture on Django, knip without config); **G3** duration telemetry always 0.00s; **G5** maintainability scanners (vulture/radon/cohesion/pydeps) have no documented oracle.
- **RESEARCH (pending, interrupted)** — best approach to test-drive the maintainability scanners (G5): public repos/labelled datasets as ground truth vs generating synthetic seeded fixtures, per issue type (dead-code, complexity, cohesion, coupling, duplication, unused-JS). Operator interrupted the deep-research run; revisit if/when prioritised.

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
