# Raw capture — G8: no JS complexity or cohesion scanning

**Captured:** 2026-05-30
**Origin:** follow-on from the coverage dogfood (NodeGoat JS). Sibling to **G6** (no JS first-party
SAST) but on the *maintainability* axis rather than security. Surfaced while verifying the
language→analyzer partition in `code_review/lang_select.py`.

## The thought

For JavaScript/TypeScript, the suite provides **no complexity scanning and no cohesion scanning**.
Both capabilities exist for Python only and have no JS analyzer wired in.

## Verified (2026-05-30) — the hard partition

`code_review/lang_select.py:3-4`:
```python
_PYTHON_ADAPTERS = {bandit, vulture, pydeps, cohesion, radon, semgrep}
_JS_ADAPTERS     = {eslint, jscpd, knip, depcruiser}
```
- **radon** (complexity) and **cohesion** (class cohesion) are in the Python-only set.
- The JS set has no complexity analyzer and no cohesion analyzer.

## Capability-by-language gap

| Capability | Python | JS/TS | JS covered? |
|---|---|---|---|
| Duplication | jscpd | jscpd | ✅ |
| Dead code | vulture | knip | ✅ (noisy, G7) |
| Coupling / cycles | pydeps | depcruiser | ✅ |
| **Complexity** | **radon** | **— none —** | ❌ |
| **Cohesion** | **cohesion** | **— none —** | ❌ |

So on the maintainability axis, JS is covered for duplication / dead-code / coupling, but **blank
for complexity and cohesion**. (Distinct from G6, which is the security-SAST asymmetry.)

## Why (root cause)

- `cohesion` (`code_review/adapters/cohesion_.py`) is the `cohesion` PyPI package — Python-AST,
  per-class attribute/method cohesion. Architecturally Python-specific; no JS counterpart wired in.
- `radon` is a Python-only metrics tool (cyclomatic complexity / maintainability index over Python
  source).

## Closable? (unlike bandit's Python lock-in)

- **JS complexity — likely closable.** eslint already ships a built-in `complexity` rule; dedicated
  tools exist (`typhonjs-escomplex`, `es6-plato`, `complexity-report`). Options: (a) enable/configure
  eslint's `complexity` rule — but inherits eslint's "unavailable without flat config" problem and is
  a lint-pass, not a metrics channel; (b) add a dedicated JS complexity analyzer reporting via the
  metrics channel (parity with how radon reports for Python).
- **JS cohesion — possibly not closable.** Class-cohesion tooling for JS is thin/immature. May be a
  genuine "no good tool" case worth *documenting* as out-of-scope rather than building.

## Open questions for compile

- Story vs note: JS complexity could be a real analyzer story; JS cohesion may resolve to a
  documented-limitation decision. Split them.
- Pairs with **G5** (maintainability oracle): if a JS complexity analyzer is added, it needs a
  labelled complexity-hotspot fixture in the analyzer-coverage QA harness to be assessable — same
  oracle-gap problem. Also pairs with the eslint-availability story (G7-adjacent) if the complexity
  rule route is chosen.
- Decide whether "JS maintainability parity" is a product goal at all, or whether duplication +
  dead-code + coupling is deemed sufficient JS maintainability coverage by design (analogous to the
  jscpd JS-only scoping decision). Decide intent before building.

**Verification confidence:** language partition confirmed directly in `lang_select.py`; the
radon/cohesion Python-only nature confirmed via the adapter sources. The "closable" tool options
(escomplex etc.) are from general knowledge, not yet evaluated against the project's vendoring/
offline + `--metrics off` constraints.
