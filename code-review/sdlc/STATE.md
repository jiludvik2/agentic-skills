---
NOTE: session 2026-05-31 PM had severe intermittent tool-I/O failure (Bash/Read
returned empty while Write/Edit worked). Some in-chat claims this session were
written on empty reads and were WRONG. Trust ONLY git + a fresh real run.
---

# State — last updated 2026-05-31

**Active focus:** **EPIC `epic-analyzer-thin-runner`** (ADR-0020), **story s5** (G5 maintainability oracle — the epic's LAST story). s0–s4 DONE+pushed.
**s5-t0 + s5-t1 DONE+committed (`e2687c9`, `d3cffe4`). s5-t2 work COMPLETE; a commit was ATTEMPTED at session end but could NOT be confirmed (I/O died). s5-t2 NOT yet Verify/Review-signed-off or closed.**
**Next:** Fresh session — confirm the s5-t2 commit, then Verify + Review + close s5-t2, story-level review, epic boundary.

## ⚠️ FIRST on resume — establish ground truth (chat history this session is unreliable)
```
git -C /Users/jiri/Code/2026/agentic-skills --no-pager log -4 --format='%h %s'
git -C /Users/jiri/Code/2026/agentic-skills status --porcelain
```
- **Expected if the final commit landed:** HEAD = a `s5-t2: regenerate bundle captures + reconcile QA docs…` commit, parent `d3cffe4 s5-t1`, then `e2687c9 s5-t0`. Working tree clean except maybe `sdlc/STATE.md`.
- **If that commit is NOT there:** the s5-t2 changes are staged/working-tree only (QA dir: run_smoke.py, bundle_oracle.py, scaffold_fixtures.sh, README.md, FINDINGS.md, results/**, fixtures/**, deletions of contract-testing.toml + fixtures/api/ + results/raw/schemathesis.json, new fu-gitleaks file). Re-commit them (message body below).
- Remove untracked `code-review/.claude/scheduled_tasks.lock` (don't commit). Two ScheduleWakeup timers were set during I/O stalls — ignore/cancel; they just re-prompt.
- Everything since `0051d34` is LOCAL — nothing pushed yet.

## s5-t2 — VERIFIED state (real runs I could read before I/O died; RE-RUN to confirm)
`.venv/bin/python sdlc/docs/qa/analyzer-coverage/run_smoke.py` → **RC=0, 13/14 pass, 1 xfail (gitleaks), 0 real failures**, stable across repeated runs. Both G5 precision oracles PASS on real binaries (pydeps-cycles a↔b; depcruiser-mocks prod→__mocks__). All 14 results/raw/*.json schema-valid. `pytest -m "not integration and not slow"` → 391 passed; mypy clean. ruff: re-confirm `.venv/bin/ruff check .` (last unread; an E501 was fixed earlier — should be clean).

## s5-t2 — what was done (all on disk)
Bug fixes the FIRST real end-to-end run exposed (harness had been unit-tested only — brief verifier/reviewer this is IN-SCOPE: the task is "make the QA harness work against the bundle"; the s1-t3 CLI change had left it silently broken):
1. `run_smoke.py`: invoke CLI **`run` subcommand** (was flat → 0/15 `No such command`).
2. trivy case → `count_sarif_results` (adapter runs `--format sarif`, not native JSON).
3. Removed **schemathesis** (dropped from registry by ADR-0021): the case, `run_schemathesis()`, `fixtures/api/`, `contract-testing.toml`, orphan imports.
4. `scaffold_fixtures.sh`: couplingpkg `VALUE_0N=0N` SyntaxError → `$((10#${i}))` (crashed cohesion).
5. `KNOWN_DEFERRED`/xfail: gitleaks reported visibly but doesn't fail the run.
6. README reconciled (bundle contract, bundle_oracle.py, 14-case map w/ 2 precision rows + gitleaks xfail, schemathesis removed, dates→2026-05-31). FINDINGS.md F11–F15 added (dates→2026-05-31). Follow-up filed: `sdlc/work/active/fu-gitleaks-json-output-capture.md` (out-of-scope adapter bug + recommended adapter output-capture audit).

Commit message body (if re-committing): see the attempted commit — summary: "s5-t2: regenerate bundle captures + reconcile QA docs; fix harness/fixture bugs".

## s5-t2 — REMAINING to close
1. Confirm commit (above) + re-run gate (`.venv/bin/...`; NOT `uv run` — panics under sandbox; NOT `timeout` — absent on macOS).
2. Set `sdlc/work/active/s5-t2-regenerate-captures-and-docs.md` → `status: done` + close-notes; `git mv` to `done/`. (Its earlier draft may already say done — check; if the close commit didn't run, do it.)
3. Pre-dispatch self-check → **verifier → reviewer** on the s5-t2 diff (brief: scope-growth is in-scope; gitleaks xfail is a filed follow-up). Remediate any Critical/Important.

## Then: STORY-LEVEL review (s5) → ⚠️ EPIC BOUNDARY (LAST story — pause for operator)
- Story-level review of cumulative s5 diff (t0+t1+t2): bundle-contract consistency, no normalization creep (ADR-0020), oracle/harness/README coherence. Close story `s5-maintainability-oracle` (status done, `git mv` to done/).
- **Epic close:** **Document** root `README.md` for the whole thin-runner epic (s0–s5). **File:** `git mv` `epic-analyzer-thin-runner.md` + all s0–s5 stories/tasks → `sdlc/work/done/`; relocate ADRs **0020, 0021, 0022** from `sdlc/work/active/` → `sdlc/docs/decisions/`; epic `status: done`. Decide where `fu-gitleaks-json-output-capture.md` lives (likely stays in active/ as parked follow-up, or moves with the epic — operator call). **Publish (rule #18):** `git push origin main` (all local since `0051d34`), confirm `git log @{u}..HEAD` empty; propose a release tag. **Pause for operator.**

## Memory / index TODO
- `code-review-uv-run-sandbox-panic.md` memory file exists but its **MEMORY.md index line is missing** — add a pointer near `feedback-uv-run-for-tooling`.
- New feedback memory worth writing: **harness/integration code must get one REAL end-to-end run before its task closes** (s5-t1 was marked "migrated" on unit-tests-only; 5 real bugs only surfaced on the first actual run — F11–F15).

## Session gotchas (recurring — caused most of the churn)
- **`uv run` panics under the sandbox** (macOS system-configuration probe) → `.venv/bin/python|ruff|mypy`.
- **`timeout` NOT on macOS** → rc 127, wrapped cmd never runs. Use the Bash tool's own `timeout` param.
- **A failing Bash call cascade-cancels the rest of a tool batch** → ONE tool call per turn when I/O is flaky.
- **Bash/Read intermittently returned empty** while Write/Edit worked — treat "no output" as UNKNOWN, re-read from files/git; never assume success.
- Harness runs outside the sandbox are **operator-approved** (this session) for `run_smoke.py`; toolchain is fully provisioned (vendored node bins, semgrep rules cache, Trivy DB cached, gitleaks+trivy on /opt/homebrew/bin). Runs in-sandbox too EXCEPT semgrep (the `--x-` warning trips exit-2 under sandbox).

## Open questions / follow-ups
- **gitleaks JSON output-capture** + broader adapter output-capture audit — filed (`fu-gitleaks-json-output-capture`), post-epic.
- **TS complexity** (post-epic): vendor `typescript-eslint`, widen `jscomplexity` capabilities (ADR-0022) — no adapter rewrite.
- **Stale doc (not s5 scope):** stack-pins.md §License floor cites `scripts/license_audit.py` (absent); no dependency-audit gate wired (rule #26 n/a).
