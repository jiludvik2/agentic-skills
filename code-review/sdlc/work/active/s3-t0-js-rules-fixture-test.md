---
id: s3-t0-js-rules-fixture-test
kind: task
project: code-review
status: active
parent: s3-js-semgrep-rules
sources: [adr-0016-semgrep-rule-provenance.md, epic-analyzer-thin-runner.md]
created: 2026-05-31
updated: 2026-05-31
tags: [semgrep, javascript, security, rules, fixture, integration-test]
---

# Task s3-t0 — JS/TS semgrep rules + fixture + integration test

## Outcome

The vendored semgrep ruleset fires on planted JS security defects. The integration test proves
it end-to-end (provisioning → adapter → SARIF with findings). No adapter code is modified —
the extension is purely additive: one new rule file, one new fixture, one new test.

## Rules to add

New file: `.claude/skills/code-review/semgrep-rules/security-js.yaml`

Two rules, licensed MIT (same as polyreview), hand-authored:

1. **`js-eval`** — `eval(...)` in JS/TS (CWE-95). Pattern: `eval(...)`.
   Languages: `[javascript, typescript]`. Severity: `ERROR`.

2. **`js-innerhtml-xss`** — Direct `innerHTML` assignment (`X.innerHTML = ...`) (CWE-79).
   Pattern: `$X.innerHTML = $Y`. Languages: `[javascript, typescript]`. Severity: `WARNING`.

Provenance comment at the top: MIT, hand-authored for polyreview s3, same provenance policy as
`security.yaml`.

## Fixture to add

New file: `tests/fixtures/js-with-security-issues/vuln.js`

Plain JS file with one planted instance of each rule:

```javascript
function processInput(userInput) {
    eval(userInput);                         // js-eval: CWE-95
    document.body.innerHTML = userInput;     // js-innerhtml-xss: CWE-79
}
```

Use plain `.js` (not `.ts`) — semgrep handles JS natively without a TypeScript compiler.
The fixture is self-contained (no imports); semgrep pattern-matches syntactically.

## Acceptance criteria

- `security-js.yaml` exists with `js-eval` (ERROR, CWE-95) and `js-innerhtml-xss` (WARNING,
  CWE-79) rules targeting `[javascript, typescript]`.
- `tests/fixtures/js-with-security-issues/vuln.js` exists with one planted instance of each
  rule's pattern.
- The new integration test passes: provisioned JS rules + JS fixture → `status == "ok"` +
  SARIF `results[]` containing both `js-eval` and `js-innerhtml-xss` rule IDs.
- `test_prefetch_semgrep_rules.py` passes without modification (the provisioning test globs
  `*.y*ml` dynamically — `security-js.yaml` is auto-covered).
- No file under `code_review/` is modified (architecture validation).
- `uv run pytest` (+ integration), `uv run ruff check .`, `uv run mypy code_review` clean.

## Test specification (write first, confirm RED)

Add one new `@pytest.mark.integration` test to `tests/test_adapters/test_semgrep.py`:

```
async def test_semgrep_js_rules_fire_on_js_fixture(monkeypatch, tmp_path):
    """Vendored JS rules fire on a planted JS fixture end-to-end (s3 / G6)."""
    if shutil.which("semgrep") is None:
        pytest.skip("semgrep not on PATH")

    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(tmp_path))
    # Provision vendored rules (including the new security-js.yaml)
    prefetch = <load prefetch_caches.py>
    assert prefetch.main() == 0
    assert (tmp_path / "cache" / "semgrep" / "rules" / "security-js.yaml").exists()

    out = await SemgrepAdapter().run(_req((str(JS_FIXTURE_PATH),)))
    assert out.status == "ok", f"expected ok, got {out.status}: {out.error}"
    payload = json.loads(out.stdout)
    rule_ids = [r.get("ruleId", "") for r in payload.get("runs", [{}])[0].get("results", [])]
    assert any("js-eval" in rid for rid in rule_ids), f"js-eval not fired; got {rule_ids}"
    assert any("js-innerhtml-xss" in rid for rid in rule_ids), f"js-innerhtml-xss not fired; got {rule_ids}"
```

Define `JS_FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "js-with-security-issues"`.

**RED confirmation:** before adding `security-js.yaml`, the test must fail with `status ==
"unavailable"` (JS fixture has no Python files; the Python rules don't fire but the adapter
itself finds no matching targets OR returns ok with zero results) — or it must fail the
`rule_ids` assertions. Confirm the failure mode before implementing.

## Notes

- The existing Python e2e test (`test_semgrep_end_to_end_with_provisioned_cache`) is unaffected
  — it uses the Python fixture and checks for `subprocess-shell-true`.
- `provision_semgrep_rules()` globs `*.y*ml` idempotently. Adding `security-js.yaml` to the
  bundle is the only provisioning change needed.
- If semgrep does not match `eval(...)` with the simple `pattern:` form in JS, use
  `pattern-either` with `eval(...)` for both JS and TS explicitly, or use `patterns:` with a
  `metavariable-regex` guard. Validate against the fixture before writing the test.
