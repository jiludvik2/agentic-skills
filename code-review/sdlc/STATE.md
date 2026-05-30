# State — last updated 2026-05-30

**Active focus:** **EPIC `epic-analyzer-thin-runner`** (ADR-0020) — re-architect the analyzer layer from the output-normalizing facade to a **thin invocation runner**: couple to each tool's *invocation contract* (flags/exit codes), not its *output schema*; emit raw bundles; the agent interprets. Compiled this session (ADR-0020 + epic + G1–G8 fold-in). Tree clean on `main` (not pushed).
**Last completed:** **Compile** — wrote ADR-0020 + `epic-analyzer-thin-runner`; **closed `epic-analyzer-polish`** (s0 shipped ADR-0019; coverage gaps reframed under the new epic, not dropped); graduated ADR-0019 → `docs/decisions/`; absorbed 4 raw notes as `sources:`.
**Next:** **Plan `s0` — contract inversion + bundle format** (redefine `AnalyzerOutput` raw-capture-first; define the bundle schema; retain selection + the ADR-0019 availability contract). Then s1 migrates adapters and deletes the normalisation layer.

## Open questions / follow-ups

- **Gap dispositions** now live in `epic-analyzer-thin-runner.md`: G3 retired (deleted layer); G1→s1; G2/G7→s2; G6→s3; G8→s4; G5→s5. Validation criterion: s3–s5 must each be near-trivial on the new design.
- **Design decision recorded** — ADR-0020 supersedes ADR-0006 (SARIF canonical) and amends ADR-0010's shared-format invariant (future consumer is an LLM that dedups by judgment; no shared mechanical schema).
- **`claude-code-review` redirect meta-package** (ADR-0014): due now (first GA published). Own task.
- **Diff-path resolution** (open since s4): `resolve_diff_paths` repo-relative vs `cli.py` cwd-abspath — `--diff` from a subdir mis-resolves; affects all adapters. Survives the redesign (invocation layer); fix during s1/s2.
- **GA supply-chain gate** (open since s3): no audit gate (SDLC #26 skipped); `npm audit` 5 pre-existing transitive vulns (offline/local-only). Decide whether to wire a gate (ADR).
- **Stale doc:** `stack-pins.md` references non-existent `scripts/license_audit.py` — correct or add the gate (ADR).
- **Merged branch `ccglass-traffic-analysis`** still on local + origin; delete (operator authorises) now PR #1 merged.
- **Deferred Minors** (s0/s6/s7 close notes): schemathesis `h_find` error-swallow, `empty_sarif`-vs-`sarif={}` convention, `cli.py` target-resolution duplication, install/uninstall wording, `install --force` atomicity. Most touch code the redesign rewrites — re-triage against the new architecture rather than fixing on the facade.
