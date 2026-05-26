from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from code_review.contracts import MetricSet
from code_review.hotspots import compute_hotspots

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SKILL_DIR = Path(__file__).resolve().parent.parent / ".claude" / "skills" / "code-review"


def _sarif_with_results(findings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": "test"}}, "results": findings}],
    }


def _finding(uri: str, sdlc_severity: str = "minor") -> dict[str, Any]:
    return {
        "ruleId": "TEST001",
        "level": "warning",
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": uri},
                    "region": {"startLine": 1},
                }
            }
        ],
        "properties": {"sdlc_severity": sdlc_severity},
    }


def _metric_set(
    per_file: dict[str, dict[str, Any]] | None = None,
    coupling: dict[str, dict[str, Any]] | None = None,
) -> MetricSet:
    return MetricSet(
        per_file=per_file or {},
        per_class={},
        coupling=coupling or {},
    )


# ---------------------------------------------------------------------------
# Composite score golden-file test
# ---------------------------------------------------------------------------


def test_composite_score_golden() -> None:
    """Hotspot output matches expected golden fixture."""
    consolidated = _sarif_with_results([
        _finding("src/auth.py", "critical"),
        _finding("src/auth.py", "important"),
        _finding("src/utils.py", "minor"),
        _finding("src/views.py", "nit"),
    ])
    metrics = _metric_set(
        per_file={
            "src/auth.py": {"cyclomatic_complexity": 20},
            "src/utils.py": {"cyclomatic_complexity": 5},
        },
        coupling={
            "src/auth.py": {"fan_in": 3, "fan_out": 4},
        },
    )

    hotspots = compute_hotspots(consolidated, metrics, diff_files=None)

    assert isinstance(hotspots, list)
    assert len(hotspots) == 2  # src/views.py nit → score 0.0 → excluded

    # auth.py must be ranked first (highest score)
    assert hotspots[0]["file"] == "src/auth.py"

    # shape: each entry has file, composite_score, factors
    for entry in hotspots:
        assert "file" in entry
        assert "composite_score" in entry
        assert isinstance(entry["composite_score"], float)
        assert "factors" in entry
        factors = entry["factors"]
        assert "severity_weighted_findings" in factors

    # validate against golden fixture if it exists
    golden_path = Path(__file__).parent / "fixtures" / "hotspots_golden.json"
    if golden_path.exists():
        golden = json.loads(golden_path.read_text())
        assert hotspots == golden, (
            f"Hotspot output differs from golden.\nGot:\n{json.dumps(hotspots, indent=2)}"
        )


# ---------------------------------------------------------------------------
# Per-task scope restriction
# ---------------------------------------------------------------------------


def test_per_task_scope_restricts_to_diff_files() -> None:
    """With diff_files set, only those files appear in hotspots."""
    consolidated = _sarif_with_results([
        _finding("src/auth.py", "critical"),
        _finding("src/utils.py", "important"),
        _finding("src/views.py", "important"),
    ])
    metrics = _metric_set()

    hotspots = compute_hotspots(
        consolidated, metrics, diff_files={"src/auth.py"}
    )

    files = {h["file"] for h in hotspots}
    assert files == {"src/auth.py"}, (
        f"Expected only src/auth.py; got {files}"
    )


# ---------------------------------------------------------------------------
# Story-level scope
# ---------------------------------------------------------------------------


def test_story_level_scope_includes_all_files() -> None:
    """With diff_files=None, all files with non-zero score appear."""
    consolidated = _sarif_with_results([
        _finding("src/auth.py", "critical"),
        _finding("src/utils.py", "important"),
    ])
    metrics = _metric_set()

    hotspots = compute_hotspots(consolidated, metrics, diff_files=None)

    files = {h["file"] for h in hotspots}
    assert files == {"src/auth.py", "src/utils.py"}


def test_empty_diff_files_is_story_level_scope() -> None:
    """diff_files=set() (empty set) must behave identically to diff_files=None (story-level)."""
    consolidated = _sarif_with_results([
        _finding("src/auth.py", "critical"),
        _finding("src/utils.py", "important"),
    ])
    metrics = _metric_set()

    hotspots_none = compute_hotspots(consolidated, metrics, diff_files=None)
    hotspots_empty = compute_hotspots(consolidated, metrics, diff_files=set())

    assert hotspots_empty == hotspots_none, (
        f"empty-set scope should equal story-level (None): {hotspots_empty!r}"
    )


def test_story_level_scope_includes_metric_only_files() -> None:
    """Files that appear only in MetricSet (no SARIF findings) are included in story-level."""
    consolidated = _sarif_with_results([])
    metrics = _metric_set(per_file={"src/complex.py": {"cyclomatic_complexity": 10}})

    hotspots = compute_hotspots(consolidated, metrics, diff_files=None)

    files = {h["file"] for h in hotspots}
    assert "src/complex.py" in files, (
        f"MetricSet-only file should appear in story-level hotspots: {hotspots}"
    )


# ---------------------------------------------------------------------------
# Zero-score omission
# ---------------------------------------------------------------------------


def test_zero_score_files_omitted() -> None:
    """Files with composite_score == 0.0 do not appear in ranked hotspots."""
    # nit-only finding + no metrics → zero severity weight, zero complexity
    consolidated = _sarif_with_results([_finding("src/nit_file.py", "nit")])
    metrics = _metric_set()

    hotspots = compute_hotspots(
        consolidated, metrics, diff_files={"src/nit_file.py"}
    )

    assert all(h["file"] != "src/nit_file.py" for h in hotspots), (
        f"Zero-score file should be excluded: {hotspots}"
    )


# ---------------------------------------------------------------------------
# Default weights come from capabilities.json
# ---------------------------------------------------------------------------


def test_default_weights_from_capabilities_json() -> None:
    """capabilities.json must have a hotspots.weights section."""
    caps = json.loads((_SKILL_DIR / "capabilities.json").read_text())
    weights = caps.get("hotspots", {}).get("weights", {})
    assert "severity_weighted_findings" in weights, (
        f"capabilities.json missing hotspots.weights.severity_weighted_findings: {weights}"
    )
    assert "cyclomatic_complexity" in weights
    assert "coupling" in weights


# ---------------------------------------------------------------------------
# Sorted descending
# ---------------------------------------------------------------------------


def test_hotspots_sorted_descending() -> None:
    """Hotspots list is sorted by composite_score descending."""
    consolidated = _sarif_with_results([
        _finding("src/low.py", "minor"),
        _finding("src/high.py", "critical"),
        _finding("src/high.py", "critical"),
    ])
    metrics = _metric_set()

    hotspots = compute_hotspots(consolidated, metrics, diff_files=None)

    scores = [h["composite_score"] for h in hotspots]
    assert scores == sorted(scores, reverse=True), (
        f"Hotspots not sorted descending: {scores}"
    )


@pytest.mark.parametrize("diff_files", [set(), None])
def test_empty_sarif_returns_empty_list(diff_files: set[str] | None) -> None:
    """No findings + empty metrics → empty hotspots list."""
    consolidated = _sarif_with_results([])
    metrics = _metric_set()
    hotspots = compute_hotspots(consolidated, metrics, diff_files=diff_files)
    assert hotspots == []
