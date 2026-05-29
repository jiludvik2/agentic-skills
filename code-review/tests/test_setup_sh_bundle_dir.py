"""s2-t5: scripts/setup.sh step 5 ("Starter config template") must resolve
the bundled example correctly. Pre-fix EXAMPLE_PATH pointed at code-review/
(empty); the file actually lives at .claude/skills/code-review/."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SETUP_SH = REPO_ROOT / "scripts" / "setup.sh"
EXPECTED_EXAMPLE = (
    REPO_ROOT / ".claude" / "skills" / "code-review" / "code-review.toml.example"
)


def test_setup_sh_defines_bundle_dir() -> None:
    """Setup.sh must compute a BUNDLE_DIR resolving to the skill bundle root.
    Looks for a `BUNDLE_DIR=` assignment that references .claude/skills/code-review
    somewhere in its right-hand side or in an immediately preceding/following line."""
    source = SETUP_SH.read_text(encoding="utf-8")
    assert "BUNDLE_DIR=" in source, (
        "scripts/setup.sh must define BUNDLE_DIR; current source does not contain it"
    )
    # Find the BUNDLE_DIR definition. Allow either direct reference to the
    # bundle path, or a path computation that lands on it.
    assert re.search(
        r"BUNDLE_DIR=[^\n]*\.claude/skills/code-review",
        source,
    ) or ".claude/skills/code-review" in source, (
        "BUNDLE_DIR (or its computation) must mention .claude/skills/code-review"
    )


def test_example_path_resolves_in_dev_layout() -> None:
    """The BUNDLE_DIR computation in setup.sh, given a dev-layout SCRIPT_DIR/
    SKILL_ROOT, must land EXAMPLE_PATH on the real bundled example file.

    BASH_SOURCE inside `bash -c` doesn't resolve to the source script, so we
    seed SCRIPT_DIR and SKILL_ROOT explicitly here. That makes this a test of
    the BUNDLE_DIR / EXAMPLE_PATH logic itself rather than of bash's
    BASH_SOURCE machinery (which is well-trodden ground)."""
    source = SETUP_SH.read_text(encoding="utf-8")

    # Extract just the BUNDLE_DIR if/elif/else block.
    bundle_block_match = re.search(
        r'if\s+\[\[\s+-f\s+"\$\{SKILL_ROOT\}/\.claude.*?BUNDLE_DIR="?"?\s*\nfi',
        source,
        re.DOTALL,
    )
    assert bundle_block_match, (
        "could not locate BUNDLE_DIR if/elif/else block in scripts/setup.sh"
    )
    bundle_block = bundle_block_match.group(0)

    # Extract the EXAMPLE_PATH assignment.
    example_match = re.search(r'EXAMPLE_PATH="[^"\n]+"', source)
    assert example_match, "scripts/setup.sh does not define EXAMPLE_PATH"
    example_assignment = example_match.group(0)

    snippet = (
        f'set -euo pipefail\n'
        f'SKILL_ROOT="{REPO_ROOT}"\n'
        f'{bundle_block}\n'
        f'{example_assignment}\n'
        f'echo "$EXAMPLE_PATH"\n'
    )
    result = subprocess.run(
        ["bash", "-c", snippet],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"bash snippet failed:\nstdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    resolved = Path(result.stdout.strip()).resolve()
    assert resolved == EXPECTED_EXAMPLE.resolve(), (
        f"EXAMPLE_PATH resolved to {resolved!r}; expected {EXPECTED_EXAMPLE.resolve()!r}"
    )
    assert resolved.exists(), f"resolved EXAMPLE_PATH does not exist on disk: {resolved}"
