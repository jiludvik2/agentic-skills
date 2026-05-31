# State — last updated 2026-05-31

**Active focus:** **EPIC `epic-analyzer-thin-runner`** (ADR-0020, stories s0–s5). s0–s4 DONE and pushed to origin/main @ 0051d34. **s5 PLANNED (committed @ 89602f3, local), awaiting operator approval to execute.** Working tree clean.
**Last completed:** **Story s4** (`s4-js-complexity-analyzer`, G8) — shipped `jscomplexity` (vendored-ESLint complexity rule, radon-cc parity, JS-only). 393 tests green.
**Next:** **Execute s5-t0** once the plan is approved. s5 is the **last story of the epic**; closing it hits the epic boundary.

## s5 plan summary (awaiting approval)
**Story `s5-maintainability-oracle` (G5).** The analyzer-coverage QA harness is **broken** post-ADR-0020: every oracle reads the deleted consolidated schema while the CLI now emits `review-bundle.v1.json`. s5 re-points the whole oracle at the bundle + adds two **precision** coupling oracles. Three tasks:
- **s5-t0** — pure `bundle_oracle.py` module + pytest unit tests (incl. both precision oracles), in-sandbox, tests-first.
- **s5-t1** — labelled coupling fixtures (`python/cyclepkg` a→b→a; `js/__mocks__` prod→mock edge) + `run_smoke.py` migration onto the bundle + in-sandbox pydeps integration test.
- **s5-t2** — provisioned full-harness run: regenerate `results/raw/*.json` to bundle shape + reconcile README (heavy-toolchain task; may be operator-run outside sandbox).

Operator-approved design decisions: **pure oracle module + pytest**; **assert the specific cycle** (precision) for the two new coupling oracles. pydeps cycle visibility in raw output verified via live probe — zero adapter change, G5 "near-trivial" holds.

## Open questions / follow-ups
- **s5-t1 interpretive call:** depcruiser `__mocks__` planned as a **prod→`__mocks__` coupling smell** (distinct from the existing `cycle_a/cycle_b` circular case). The raw G5 source is gone; flip one s5-t1 AC if `__mocks__` was meant as a second circular fixture instead.
- **s5-t2 heavy env:** the full harness run needs the provisioned toolchain (Node vendoring, Trivy DB, gitleaks/trivy, fastapi) and runs outside the sandbox — may be operator-driven. In-sandbox proofs (s5-t0 unit tests, s5-t1 pydeps integration) hold regardless.
- **TS complexity follow-up** (post-epic, if demanded): vendor `typescript-eslint` + widen `jscomplexity` capabilities — no adapter rewrite (ADR-0022).
- **Stale doc (not s5 scope):** stack-pins.md §License floor cites `scripts/license_audit.py` (does not exist); no dependency-audit gate is wired (rule #26 n/a).

## Epic boundary (after s5)
Last story of the epic. On clean close: **Document** (README reconcile for the whole thin-runner epic), **File** (epic → `done/`; relocate ADRs 0020/0021/0022 → `docs/decisions/`), publication check (rule #18).
