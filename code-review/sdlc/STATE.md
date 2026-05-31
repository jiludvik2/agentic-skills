---
NOTE: session 2026-05-31 PM had SEVERE intermittent tool-I/O failure (Bash/Read
returned empty for long stretches while Write/Edit kept working). The last two
operations below could NOT be confirmed on-screen. Trust ONLY git + a fresh run.
---

# State — last updated 2026-05-31

**Active focus:** **EPIC `epic-analyzer-thin-runner`** (ADR-0020), **story s5** (G5 maintainability oracle — the epic's LAST story). s0–s4 DONE+pushed.
**s5-t0, s5-t1, s5-t2 all DONE; s5-t2 passed Verify (PASS) + Review (MINOR-ONLY).** Story s5 is functionally complete — only its close + the epic boundary remain.
**Next (fresh session):** confirm the last two git ops, story-level review, then the epic boundary (Document/File/Publish) — pauses for operator.

## ⚠️ FIRST on resume — confirm what the I/O failure hid
Run and read:
```
git -C /Users/jiri/Code/2026/agentic-skills --no-pager log -6 --format='%h %s'
git -C /Users/jiri/Code/2026/agentic-skills status --porcelain
ls code-review/sdlc/work/active code-review/sdlc/work/done | grep s5-t2
```
**Confirmed commits (read on-screen):** `9ee69ce s5-t2: regenerate bundle captures…`, `d3cffe4 s5-t1`, `e2687c9 s5-t0`, `aa7a82f wrap: STATE handoff`.
**UNCONFIRMED (issued, returned empty — verify):**
1. Edit setting `s5-t2-regenerate-captures-and-docs.md` → `status: done` + close-notes (Edit didn't error, so likely applied — check the file's frontmatter).
2. `git mv` of that file active/→done/ + a close commit `s5-t2 close: verifier PASS, reviewer MINOR-ONLY…`.
- **If the close commit landed:** s5-t2 file is in `work/done/` with `status: done`; proceed to story-level review.
- **If NOT:** the file may be in active/ (possibly already edited to done) or mid-rename. Set `status: done` if needed, `git mv` to `done/`, commit. Then proceed.
- Remove untracked `code-review/.claude/scheduled_tasks.lock` if present (don't commit). Cancel any leftover ScheduleWakeup timers.
- Everything since `0051d34` is LOCAL — nothing pushed.

## Story s5 — final state (all verified by real runs + fresh-context gates)
- **s5-t0** (`e2687c9`): pure `bundle_oracle.py` + 24 unit tests. Verifier PASS, reviewer MINOR-ONLY.
- **s5-t1** (`d3cffe4`): coupling fixtures (cyclepkg, js/__mocks__) + run_smoke.py migration + pydeps integration test. Verifier PASS, reviewer MINOR-ONLY.
- **s5-t2** (`9ee69ce`): full provisioned harness run + capture regen + README/FINDINGS reconcile + harness/fixture bug fixes the first real run exposed (F11–F15). Verifier PASS, reviewer MINOR-ONLY.
- **Harness result:** RC=0, **13/14 pass, 1 xfail (gitleaks), 0 real failures**. Both G5 precision oracles PASS on real binaries (pydeps-cycles a↔b back-edge; depcruiser-mocks prod→__mocks__ edge) — the reviewer independently re-ran the depcruiser oracle against the committed bundle = True. All 14 `results/raw/*.json` schema-valid. 391-test suite + ruff + mypy clean.
- **G5 architecture-validation: CONFIRMED.** Adding the two precision oracles needed zero adapter change — the thin-runner "near-trivial to add an oracle" criterion holds (third of three validations: s3 ruleset, s4 analyzer, s5 oracle).

## Minor findings parked for opportunistic cleanup (NOT blockers; in s5-t2 notes)
1. `bundle_oracle.py` `count_trivy` + `count_schemathesis` are now dead code (trivy switched to count_sarif_results; schemathesis removed). `count_trivy`'s presence invites the F12 mistake again — annotate-as-unused or remove on next QA touch.
2. `run_smoke.py` `_run_cli` could `try/finally` unlink the per-case `.qa_<label>.json` temp.
3. FINDINGS.md H1 title still "— 2026-05-29" (frontmatter + new section correctly 2026-05-31).
4. README "native JSON for …" one-liner slightly overstates gitleaks (xfail).

## REMAINING — story close + ⚠️ EPIC BOUNDARY (s5 is the LAST story → PAUSE for operator after)
1. **Confirm/finish s5-t2 close** (above).
2. **STORY-LEVEL review** of the cumulative s5 diff (t0+t1+t2): bundle-contract consistency, no normalization creep (ADR-0020), oracle/harness/README coherence across tasks. Remediate any Critical/Important. Then set story `s5-maintainability-oracle` → `status: done` + close-notes, `git mv` active/→done/.
3. **EPIC CLOSE** (the epic boundary — operator pauses here):
   - **Document:** reconcile root `README.md` with the whole thin-runner epic (s0–s5): the analyzer layer is now a thin invocation runner emitting `review-bundle.v1.json` (raw per-tool output), not a SARIF-normalizing facade.
   - **File:** `git mv` `epic-analyzer-thin-runner.md` + all s0–s5 stories/tasks from `sdlc/work/active/` → `sdlc/work/done/`; set epic `status: done`. Relocate the co-located ADRs **0020, 0021, 0022** from `sdlc/work/active/` → `sdlc/docs/decisions/`. Decide where `fu-gitleaks-json-output-capture.md` lives (parked follow-up — likely stays in active/, operator call).
   - **Publish (rule #18):** `git push origin main` — everything since `0051d34` is local (plan + s5-t0/t1/t2 + wraps + close). Confirm `git log @{u}..HEAD` empty after. Propose a release tag (semver).
   - **PAUSE for operator** — do not auto-start the next epic.

## Memory / index TODO
- `code-review-uv-run-sandbox-panic.md` memory file exists but its **MEMORY.md index line is missing** — add a pointer near `feedback-uv-run-for-tooling`.
- Write a feedback memory: **harness/integration code needs one REAL end-to-end run before its task closes** — s5-t1 was marked "migrated" on unit-tests-only; 5 real bugs (F11–F15) only surfaced on the first actual run. Unit-green ≠ harness-works.

## Session gotchas (recurring — caused most churn)
- **`uv run` panics under the sandbox** (macOS system-configuration probe) → `.venv/bin/python|ruff|mypy`.
- **`timeout` NOT on macOS** → rc 127, wrapped cmd never runs. Use the Bash tool's own `timeout` param.
- **A failing Bash call cascade-cancels the rest of a tool batch** → ONE tool call per turn when I/O is flaky.
- **Bash/Read intermittently returned empty** (Write/Edit fine) — treat "no output" as UNKNOWN, re-read from files/git next session.
- Harness runs **outside the sandbox** are operator-approved (this session) for `run_smoke.py`; toolchain fully provisioned (vendored node bins, semgrep rules cache, Trivy DB cached, gitleaks+trivy on /opt/homebrew/bin). Runs in-sandbox too EXCEPT semgrep (the `--x-` warning trips exit-2 under sandbox).

## Open questions / follow-ups
- **gitleaks JSON output-capture** + broader adapter output-capture audit — filed (`fu-gitleaks-json-output-capture`), post-epic.
- **TS complexity** (post-epic): vendor `typescript-eslint`, widen `jscomplexity` capabilities (ADR-0022) — no adapter rewrite.
- **Stale doc (not s5 scope):** stack-pins.md §License floor cites `scripts/license_audit.py` (absent); no dependency-audit gate wired (rule #26 n/a).
