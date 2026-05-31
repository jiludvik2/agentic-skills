from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

import pytest

from code_review.config import ConfigError, load_config

# ---------------------------------------------------------------------------
# Absent file → all defaults
# ---------------------------------------------------------------------------


def test_absent_file_returns_defaults(tmp_path: Path) -> None:
    config = load_config(tmp_path / "code-review.toml")
    assert config.dedup_line_tolerance == 3
    assert config.severity_overrides == {}
    assert isinstance(config.hotspot_weights, dict)
    assert "severity_weighted_findings" in config.hotspot_weights


# ---------------------------------------------------------------------------
# line_tolerance override
# ---------------------------------------------------------------------------


def test_line_tolerance_override(tmp_path: Path) -> None:
    (tmp_path / "code-review.toml").write_text(
        textwrap.dedent("""\
            [dedup]
            line_tolerance = 5
        """)
    )
    config = load_config(tmp_path / "code-review.toml")
    assert config.dedup_line_tolerance == 5


def test_line_tolerance_override_affects_aggregate(tmp_path: Path) -> None:
    """Aggregator uses config.dedup_line_tolerance when config is passed."""
    (tmp_path / "code-review.toml").write_text(
        textwrap.dedent("""\
            [dedup]
            line_tolerance = 5
        """)
    )
    config = load_config(tmp_path / "code-review.toml")

    from code_review.aggregator import aggregate
    from code_review.contracts import AnalyzerOutput

    def sarif(line: int, tool: str) -> dict[str, Any]:
        return {
            "version": "2.1.0",
            "runs": [{
                "tool": {"driver": {"name": tool}},
                "results": [{
                    "ruleId": "TEST001",
                    "level": "warning",
                    "locations": [{"physicalLocation": {
                        "artifactLocation": {"uri": "src/a.py"},
                        "region": {"startLine": line},
                    }}],
                    "taxa": [{"id": "CWE-89", "toolComponent": {"name": "CWE"}}],
                    "properties": {},
                }],
            }],
        }

    r1 = AnalyzerOutput(sarif=sarif(47, "semgrep"))
    r2 = AnalyzerOutput(sarif=sarif(51, "bandit"))  # distance 4: merges at tolerance=5, not at 3
    results = aggregate([r1, r2], line_tolerance=config.dedup_line_tolerance)["runs"][0]["results"]
    assert len(results) == 1, "Expected merge at tolerance=5 for distance-4 findings"


# ---------------------------------------------------------------------------
# severity override
# ---------------------------------------------------------------------------


def test_severity_override(tmp_path: Path) -> None:
    (tmp_path / "code-review.toml").write_text(
        textwrap.dedent("""\
            [severity]
            "warning+high" = "critical"
        """)
    )
    config = load_config(tmp_path / "code-review.toml")
    assert config.severity_overrides.get("warning+high") == "critical"


# ---------------------------------------------------------------------------
# hotspot_weights override
# ---------------------------------------------------------------------------


def test_hotspot_weights_override(tmp_path: Path) -> None:
    (tmp_path / "code-review.toml").write_text(
        textwrap.dedent("""\
            [hotspots.weights]
            cyclomatic_complexity = 2.0
        """)
    )
    config = load_config(tmp_path / "code-review.toml")
    assert config.hotspot_weights["cyclomatic_complexity"] == 2.0
    # other weights still have defaults
    assert "severity_weighted_findings" in config.hotspot_weights


def test_hotspot_weights_override_affects_score(tmp_path: Path) -> None:
    """Higher cyclomatic_complexity weight raises score for complex file."""
    (tmp_path / "code-review.toml").write_text(
        textwrap.dedent("""\
            [hotspots.weights]
            cyclomatic_complexity = 2.0
        """)
    )
    config = load_config(tmp_path / "code-review.toml")

    from code_review.contracts import MetricSet
    from code_review.hotspots import compute_hotspots

    sarif = {
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": "t"}}, "results": []}],
    }
    metrics = MetricSet(
        per_file={"src/complex.py": {"cyclomatic_complexity": 10}},
        per_class={},
        coupling={},
    )
    hotspots_default = compute_hotspots(sarif, metrics, diff_files=None)
    hotspots_override = compute_hotspots(
        sarif, metrics, diff_files=None,
        weights=config.hotspot_weights,
    )
    score_default = next(
        (h["composite_score"] for h in hotspots_default if h["file"] == "src/complex.py"), 0.0
    )
    score_override = next(
        (h["composite_score"] for h in hotspots_override if h["file"] == "src/complex.py"), 0.0
    )
    assert score_override > score_default, (
        f"Override weight=2.0 should raise score: "
        f"default={score_default}, override={score_override}"
    )


# ---------------------------------------------------------------------------
# disabled_analyzers
# ---------------------------------------------------------------------------


def test_load_config_reads_disabled_analyzers(tmp_path: Path) -> None:
    toml = tmp_path / "code-review.toml"
    toml.write_text('disabled_analyzers = ["trivy", "pydeps"]\n')
    from code_review.config import load_config

    cfg = load_config(tmp_path / "code-review.toml")
    assert cfg.disabled_analyzers == ["trivy", "pydeps"]


def test_load_config_disabled_analyzers_default_empty(tmp_path: Path) -> None:
    from code_review.config import load_config

    cfg = load_config(tmp_path / "code-review.toml")  # no toml file
    assert cfg.disabled_analyzers == []


# ---------------------------------------------------------------------------
# Malformed TOML → ConfigError
# ---------------------------------------------------------------------------


def test_malformed_toml_raises_config_error(tmp_path: Path) -> None:
    (tmp_path / "code-review.toml").write_text("this is [not valid toml !!!")
    with pytest.raises(ConfigError) as exc_info:
        load_config(tmp_path / "code-review.toml")
    assert str(tmp_path) in str(exc_info.value) or "code-review.toml" in str(exc_info.value)


# ---------------------------------------------------------------------------
# severity_overrides validation
# ---------------------------------------------------------------------------


def test_invalid_severity_override_value_raises_config_error(tmp_path: Path) -> None:
    (tmp_path / "code-review.toml").write_text(
        textwrap.dedent("""\
            [severity]
            "rule-x" = "blocker"
        """)
    )
    with pytest.raises(ConfigError, match="blocker"):
        load_config(tmp_path / "code-review.toml")



# ---------------------------------------------------------------------------
# semgrep_rules (root-level key; ADR-0016 #5)
# ---------------------------------------------------------------------------


def test_config_parses_semgrep_rules(tmp_path: Path) -> None:
    (tmp_path / "code-review.toml").write_text(
        textwrap.dedent("""\
            semgrep_rules = "/etc/polyreview/security.yaml"
        """)
    )
    config = load_config(tmp_path / "code-review.toml")
    assert config.semgrep_rules == "/etc/polyreview/security.yaml"


def test_semgrep_rules_absent_is_none(tmp_path: Path) -> None:
    config = load_config(tmp_path / "code-review.toml")
    assert config.semgrep_rules is None
