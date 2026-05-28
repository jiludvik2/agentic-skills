---
id: s1-t4-install-smoke-test
kind: task
project: code-review
status: active
parent: s1-package-publication
created: 2026-05-28
updated: 2026-05-28
---

# s1-t4 — Console-script install smoke test

## Outcome

A new test builds the wheel, installs it into a clean tmpdir venv via `pip`, and exercises the `code-review` console-script entry point. Catches `[project.scripts]` regressions before tagging.

## Acceptance criteria

- New: `tests/test_console_script_install.py`. The test:
  1. Runs `uv build` (or `python -m build`) in the project tree.
  2. Locates the produced wheel under `dist/`.
  3. Creates a fresh venv via `venv.create(tmp_path / "venv", with_pip=True)`.
  4. `pip install`s the wheel into that venv via `subprocess.run([venv_python, "-m", "pip", "install", wheel_path])`.
  5. Runs `<venv>/bin/claude-code-review --capabilities` (the bare console-script, not `python -m`) via `subprocess.run`.
  6. Asserts: exit code 0; stdout is valid JSON; the JSON structure matches the source-tree `python -m code_review.cli --capabilities` output (same `analyzers` list, same `review_kinds`, same `stack_coverage`).
- The test is allowed to take 30–60 seconds; mark with a pytest marker if needed but don't skip-by-default.
- Cleans up the tmpdir venv on test exit (pytest's `tmp_path` fixture handles this).

## Test specification

This task IS a test addition; the test itself satisfies the AC.

Implementation skeleton:

```python
import json
import subprocess
import sys
import venv
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent  # adjust to actual layout

@pytest.mark.slow
def test_console_script_install(tmp_path: Path) -> None:
    # 1. Build wheel
    subprocess.run(
        ["uv", "build", "--wheel"],
        cwd=REPO_ROOT, check=True, capture_output=True,
    )
    wheels = list((REPO_ROOT / "dist").glob("claude_code_review-*.whl"))
    assert wheels, "no wheel produced"
    wheel = wheels[-1]  # latest

    # 2. Fresh venv
    venv_dir = tmp_path / "venv"
    venv.create(venv_dir, with_pip=True)
    venv_python = venv_dir / "bin" / "python"

    # 3. Install
    subprocess.run(
        [str(venv_python), "-m", "pip", "install", str(wheel)],
        check=True, capture_output=True,
    )

    # 4. Run console-script
    console_script = venv_dir / "bin" / "claude-code-review"
    assert console_script.exists(), "claude-code-review entry point missing"
    r = subprocess.run(
        [str(console_script), "--capabilities"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    parsed = json.loads(r.stdout)
    assert "analyzers" in parsed
    # Compare against source-tree invocation
    source_r = subprocess.run(
        [sys.executable, "-m", "code_review.cli", "--capabilities"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    source_parsed = json.loads(source_r.stdout)
    assert parsed["analyzers"] == source_parsed["analyzers"]
```

## Notes

- Depends on `s0-t1` (`pyproject.toml` package-data declarations) being done — without that, the installed package wouldn't have `capabilities.json` to print.
- Depends on `s0-t0` (`importlib.resources`) — without that, the installed package's `Path(__file__).parent` reads would fail.
- Skipped by default if `uv` isn't available on PATH; document the marker.
- This test is the s1 counterpart to `s0-t1`'s `tests/test_wheel_packaging.py`. They overlap: s0's test proves the wheel contains the JSON; s1's test proves the console-script entry point resolves and runs.
- Keep this test in `tests/`, not in a separate `tests/integration/` directory — the project doesn't currently maintain that split.
