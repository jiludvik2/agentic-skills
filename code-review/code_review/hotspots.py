from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from code_review.contracts import MetricSet

_DEFAULT_WEIGHTS = {
    "severity_weighted_findings": 1.0,
    "cyclomatic_complexity": 0.5,
    "coupling": 0.3,
}
_DEFAULT_SEVERITY_SCORES: dict[str, float] = {
    "critical": 4.0,
    "important": 2.0,
    "minor": 1.0,
    "nit": 0.0,
}


def _load_defaults() -> tuple[dict[str, float], dict[str, float]]:
    caps_path = Path(__file__).resolve().parent / "capabilities.json"
    if not caps_path.exists():
        return _DEFAULT_WEIGHTS, _DEFAULT_SEVERITY_SCORES
    caps = json.loads(caps_path.read_text(encoding="utf-8"))
    hotspots_cfg = caps.get("hotspots", {})
    weights = {k: float(v) for k, v in hotspots_cfg.get("weights", _DEFAULT_WEIGHTS).items()}
    sev_scores = {
        k: float(v)
        for k, v in hotspots_cfg.get("severity_finding_scores", _DEFAULT_SEVERITY_SCORES).items()
    }
    return weights, sev_scores


def _get_file_uri(result: dict[str, Any]) -> str | None:
    locs = result.get("locations", [])
    if not locs:
        return None
    uri: str | None = (
        locs[0]
        .get("physicalLocation", {})
        .get("artifactLocation", {})
        .get("uri")
    )
    return uri


def compute_hotspots(
    consolidated_sarif: dict[str, Any],
    metrics: MetricSet | None,
    diff_files: set[str] | None,
    weights: dict[str, float] | None = None,
    severity_scores: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Compute ranked per-file hotspot scores from consolidated SARIF + MetricSet.

    diff_files=None or set() → story-level scope (all files).
    diff_files=<non-empty set> → per-task scope (restrict to files in the set).
    Weights fall back to capabilities.json defaults when not provided.
    """
    default_weights, default_sev_scores = _load_defaults()
    w = weights if weights is not None else default_weights
    sev = severity_scores if severity_scores is not None else default_sev_scores

    severity_sums: dict[str, float] = {}
    for sarif_run in consolidated_sarif.get("runs", []):
        for result in sarif_run.get("results", []):
            uri = _get_file_uri(result)
            if uri is None:
                continue
            if diff_files and uri not in diff_files:
                continue
            sdlc_sev = result.get("properties", {}).get("sdlc_severity", "minor")
            severity_sums[uri] = severity_sums.get(uri, 0.0) + sev.get(sdlc_sev, 0.0)

    # collect all candidate files
    candidate_files: set[str] = set(severity_sums.keys())
    if diff_files:
        candidate_files = candidate_files & diff_files
    elif metrics is not None:
        candidate_files |= set(metrics.per_file.keys())
        candidate_files |= set(metrics.coupling.keys())

    hotspots: list[dict[str, Any]] = []
    for uri in candidate_files:
        sev_weight = severity_sums.get(uri, 0.0)
        sev_contribution = sev_weight * w.get("severity_weighted_findings", 1.0)

        cc_val = 0.0
        if metrics is not None:
            cc_val = float(metrics.per_file.get(uri, {}).get("cyclomatic_complexity", 0))
        cc_contribution = cc_val * w.get("cyclomatic_complexity", 0.5)

        coupling_val = 0.0
        if metrics is not None:
            c = metrics.coupling.get(uri, {})
            coupling_val = float(c.get("fan_in", 0)) + float(c.get("fan_out", 0))
        coupling_contribution = coupling_val * w.get("coupling", 0.3)

        composite = sev_contribution + cc_contribution + coupling_contribution
        if composite == 0.0:
            continue

        hotspots.append({
            "file": uri,
            "composite_score": round(composite, 6),
            "factors": {
                "severity_weighted_findings": round(sev_contribution, 6),
                "cyclomatic_complexity": round(cc_contribution, 6),
                "coupling": round(coupling_contribution, 6),
            },
        })

    hotspots.sort(key=lambda h: h["composite_score"], reverse=True)
    return hotspots
