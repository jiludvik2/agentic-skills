---
id: s0-t3-production-layout-smoke
kind: task
project: code-review
status: active
parent: s0-deployment-layout-fixup
created: 2026-05-28
updated: 2026-05-28
---

# s0-t3 — Production-layout end-to-end smoke test

## Outcome

A new test stages the production deployment layout in `tmp_path` and exercises the CLI end-to-end, proving the package + config + invocation chain works when the Python package is nested inside `.claude/skills/code-review/code_review/` (rather than as a sibling of the skill dir).

## Acceptance criteria

- A new `tests/test_production_layout.py` test stages the nested layout under `tmp_path`:
  - `<tmp>/.claude/skills/code-review/SKILL.md` (copied from the source tree)
  - `<tmp>/.claude/skills/code-review/code_review/` containing every `.py` file from `code_review/` plus `capabilities.json` and `schemas/*.json` (copied or installed as a real package — see Notes)
  - `<tmp>/code-review.toml` with a small override, e.g. `dedup_line_tolerance = 5`
  - A tiny fixture under `<tmp>/` with at least one Python file that Semgrep / Bandit can scan
- The test runs `python -m code_review.cli --capabilities` with CWD = `<tmp>` and asserts the output is valid JSON containing the analyzer registry.
- The test runs `python -m code_review.cli --review security --target .` with CWD = `<tmp>` and asserts: exit code 0; the resulting SARIF references the fixture file; the `Config` used during the run reflects `dedup_line_tolerance = 5` (verify via aggregator behaviour or via a debug-output check).
- Test is marked appropriately (`@pytest.mark.slow` if needed) but runs in default `pytest` invocations — not skipped behind a flag.

## Test specification

This task IS a test addition; the test itself satisfies the AC. No additional test infra needed.

Implementation pattern:

```python
def test_production_layout(tmp_path: Path) -> None:
    # 1. Stage the nested layout
    skill_root = tmp_path / ".claude" / "skills" / "code-review"
    pkg_root = skill_root / "code_review"
    pkg_root.mkdir(parents=True)
    # ... copy source files + JSON + schemas ...

    # 2. Drop a code-review.toml override
    (tmp_path / "code-review.toml").write_text('dedup_line_tolerance = 5\n')

    # 3. Run CLI with PYTHONPATH pointing at skill_root (so `code_review` resolves)
    env = {**os.environ, "PYTHONPATH": str(skill_root)}
    r = subprocess.run(
        [sys.executable, "-m", "code_review.cli", "--capabilities"],
        cwd=tmp_path, env=env, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout)  # valid JSON

    # 4. Run a real review against a fixture
    # ...
```

## Notes

- Depends on `s0-t0` (importlib.resources) and `s0-t2` (CWD-relative TOML) — without them, the nested layout won't work regardless of how the test is staged.
- "Copy or install" trade-off: copying source files into the nested layout is faster and isolates from the actual `code_review/` package state; installing via `pip install -e <tmp>` is closer to a real install but slower and tangles with pytest's import cache. **Recommendation: copy + `PYTHONPATH`** — clearer, no install needed.
- The test does *not* need a real Semgrep/Bandit run; mocking the adapters via the existing `FakeAnalyzer` harness is acceptable if the analyzer fan-out is slow. The point is to verify the CLI / config / package-data plumbing, not analyzer correctness.
- Existing `test_sandbox_compatibility.py` covers some adjacent ground (no writes outside CWD, no network) — keep those assertions separate; this test is about layout, not sandbox.
