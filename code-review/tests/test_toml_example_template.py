"""s0-t5: the bundled code-review.toml.example starter parses cleanly after
uncommenting, and produces the expected Config when loaded."""
from __future__ import annotations

import re
import shutil
import tomllib
from pathlib import Path

from code_review.config import load_config

SUBPROJECT_ROOT = Path(__file__).parent.parent
EXAMPLE_PATH = (
    SUBPROJECT_ROOT / ".claude" / "skills" / "code-review" / "code-review.toml.example"
)

# A line is an "uncomment-target" if it starts with `# ` followed by `[` (section
# header), a TOML bare-key character (A-Za-z 0-9 _ -), or a quoted-key delimiter
# (" or '). Pure narrative comments use `## ` and are kept.
_UNCOMMENT_RE = re.compile(r"^# (?=[A-Za-z0-9_\-\[\"'])")


def _uncomment(source: str) -> str:
    return "\n".join(_UNCOMMENT_RE.sub("", line) for line in source.splitlines()) + "\n"


def test_example_file_exists() -> None:
    assert EXAMPLE_PATH.is_file(), f"missing {EXAMPLE_PATH}"


def test_example_uncomments_to_valid_toml() -> None:
    uncommented = _uncomment(EXAMPLE_PATH.read_text(encoding="utf-8"))
    data = tomllib.loads(uncommented)
    # Spot-check all top-level sections / keys are represented.
    assert "dedup" in data and data["dedup"]["line_tolerance"] == 3
    assert "severity" in data and data["severity"]
    assert "hotspots" in data and "weights" in data["hotspots"]
    assert "disabled_analyzers" in data and data["disabled_analyzers"] == ["trivy"]


def test_uncommented_example_load_config_roundtrip(tmp_path: Path) -> None:
    dst = tmp_path / "code-review.toml"
    dst.write_text(_uncomment(EXAMPLE_PATH.read_text(encoding="utf-8")), encoding="utf-8")
    cfg = load_config(dst)
    assert cfg.dedup_line_tolerance == 3
    assert "semgrep:python.lang.security.audit.weak-crypto" in cfg.severity_overrides
    assert cfg.severity_overrides["semgrep:python.lang.security.audit.weak-crypto"] == "important"
    assert cfg.hotspot_weights["severity_weighted_findings"] == 1.0
    assert cfg.disabled_analyzers == ["trivy"]


def test_shipped_example_parses_as_is() -> None:
    """The shipped (commented) form is also valid TOML — every line is either a
    comment or blank, so tomllib parses it to an empty document."""
    data = tomllib.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    assert data == {}


def test_example_copied_to_cwd_is_honored_by_load_config(tmp_path: Path) -> None:
    """End-to-end: drop the uncommented example as CWD's code-review.toml,
    and load_config resolves overrides from it."""
    cwd_toml = tmp_path / "code-review.toml"
    shutil.copy2(EXAMPLE_PATH, cwd_toml)
    cwd_toml.write_text(
        _uncomment(cwd_toml.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    cfg = load_config(cwd_toml)
    assert cfg.dedup_line_tolerance == 3  # explicit value from example
