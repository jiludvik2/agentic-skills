# Dogfood test-drives 2026-06-01 — analyzer defects found

Ran polyreview against real public repos to exercise the shipped (0.1.0 GA)
analyzer layer. Targets:

- **pygoat** (vulnerable Django app) — security/quick: bandit 58 findings,
  semgrep 4 (eval/shell=True) after outside-sandbox run, gitleaks 10 leaks.
- **NodeGoat** (vulnerable Node app) — JS set: jscpd 5 clones, knip 31 unused,
  depcruiser 76 modules, eslint unavailable (no config), jscomplexity 1259
  findings, gitleaks 3 leaks, trivy 0 (no node_modules).
- **requests / flask / scrapy** — maintainability/full (Python coupling+cohesion):
  pydeps cycles detected (flask app↔ctx↔globals 14-SCC, scrapy 69-module SCC),
  cohesion + radon worked.
- **express / mocha / chalk / axios / webpack** — JS coupling (depcruiser):
  webpack lib = 1670 circular edges (serialization registry), others acyclic.

## Genuine product defects (file these)

1. **jscomplexity threshold-0 noise.** jscomplexity (s4, ADR-0022; reuses ESLint's
   `complexity` rule) flags EVERY function: "Function has a complexity of N.
   Maximum allowed is 0." NodeGoat 1259, mocha 732, express 109, chalk 45 — all
   noise, no signal. The complexity threshold is effectively 0; should be a sane
   default (radon-cc parity) or report metric without a 0 gate.

2. **eslint exits 2 (error) on legacy-config repos.** `_has_eslint_config`
   (eslint.py) accepts legacy `.eslintrc*`, but vendored ESLint v9.39.4 is
   flat-config-only and crashes exit-2 ("couldn't find an eslint.config file") on
   a legacy-only target (express). The adapter reports `error` where it should
   report `unavailable` (legacy config unsupported by v9). Confirmed: express/lib.

3. **gitleaks silent false-negative (already filed as fu-gitleaks-json-output-capture).**
   gitleaks writes findings to stderr in banner form; captured stdout is empty →
   bundle consumer sees "no secrets." Dogfooding adds 3 real-world repros: pygoat
   (10 real leaks), NodeGoat (3), in-sandbox pygoat. Strengthens severity from
   planted-fixture to real-repo false-negative. Promote fu → story; broaden to an
   output-capture audit of all adapters.

## Observations — NOT defects (do not file as defects)

- **No JS cohesion analyzer** — documented limitation (epic-analyzer-thin-runner s4
  + ADR-0022). cohesion is Python-only by design. Feature gap, not a defect.
- **TS complexity absent** — documented limitation (needs @typescript-eslint/parser).
- **semgrep exit-2 under sandbox** — known environment gotcha (--x- flag); not a
  product defect. Runs clean outside sandbox.
- **pydeps follows third-party deps + reports pkg↔pkg self-cycles** — raw output is
  faithful; precision/interpretation concern. Enhancement candidate, not a defect.
- **cohesion 0% for exception/ABC/namespace classes** — metric artifact (no methods
  sharing state); raw capture is correct. A SKILL.md interpretation-guidance item.
- **trivy 0 without node_modules installed** — expected.
- **Each tool's output is in its own native format (SARIF vs native JSON)** —
  by-design per ADR-0020 (thin runner does not normalize). Consumer concern.
