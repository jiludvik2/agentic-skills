"""Unit tests for the QA analyzer-coverage bundle oracle (s5-t0).

The oracle (`sdlc/docs/qa/analyzer-coverage/bundle_oracle.py`) is pure: it reads a
`review-bundle.v1.json` dict and extracts each tool's signal from its raw *native* stdout.
These tests feed hand-authored snippets — no third-party binaries — so they run in-sandbox.

The module lives outside the `code_review` package (in the QA dir), so we load it by path
via importlib rather than importing it as a package member.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

_ORACLE_PATH = (
    Path(__file__).resolve().parents[1]
    / "sdlc"
    / "docs"
    / "qa"
    / "analyzer-coverage"
    / "bundle_oracle.py"
)


def _load_oracle() -> ModuleType:
    spec = importlib.util.spec_from_file_location("qa_bundle_oracle", _ORACLE_PATH)
    assert spec and spec.loader, f"cannot load oracle from {_ORACLE_PATH}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def oracle() -> ModuleType:
    return _load_oracle()


# --------------------------------------------------------------------------- #
# Accessors
# --------------------------------------------------------------------------- #


def _bundle(*outputs: dict) -> dict:
    return {
        "schema": "polyreview/review-bundle/v1",
        "request": {
            "scope": "diff",
            "diff_range": None,
            "target_paths": ["x"],
            "languages": ["python"],
        },
        "outputs": list(outputs),
    }


def test_output_for_finds_tool(oracle: ModuleType) -> None:
    b = _bundle(
        {"tool": "bandit", "status": "ok", "stdout": "{}"},
        {"tool": "semgrep", "status": "ok", "stdout": "{}"},
    )
    assert oracle.output_for(b, "semgrep")["tool"] == "semgrep"
    assert oracle.output_for(b, "bandit")["tool"] == "bandit"


def test_output_for_absent_is_none(oracle: ModuleType) -> None:
    b = _bundle({"tool": "bandit", "status": "ok", "stdout": "{}"})
    assert oracle.output_for(b, "trivy") is None


def test_status_of(oracle: ModuleType) -> None:
    b = _bundle(
        {"tool": "bandit", "status": "ok", "stdout": "{}"},
        {"tool": "radon", "status": "unavailable", "stdout": ""},
    )
    assert oracle.status_of(b, "bandit") == "ok"
    assert oracle.status_of(b, "radon") == "unavailable"
    assert oracle.status_of(b, "trivy") == "missing"


# --------------------------------------------------------------------------- #
# SARIF counter (semgrep / eslint / jscomplexity)
# --------------------------------------------------------------------------- #


def test_count_sarif_results(oracle: ModuleType) -> None:
    sarif = json.dumps(
        {"runs": [{"results": [{"ruleId": "a"}, {"ruleId": "b"}]}, {"results": []}]}
    )
    assert oracle.count_sarif_results(sarif) == 2


def test_count_sarif_empty_and_garbage(oracle: ModuleType) -> None:
    assert oracle.count_sarif_results(json.dumps({"runs": [{"results": []}]})) == 0
    assert oracle.count_sarif_results("") == 0
    assert oracle.count_sarif_results("not json") == 0


# --------------------------------------------------------------------------- #
# Native finding counters
# --------------------------------------------------------------------------- #


def test_count_bandit(oracle: ModuleType) -> None:
    out = json.dumps({"results": [{"issue": 1}, {"issue": 2}, {"issue": 3}]})
    assert oracle.count_bandit(out) == 3
    assert oracle.count_bandit(json.dumps({"results": []})) == 0
    assert oracle.count_bandit("") == 0


def test_count_gitleaks(oracle: ModuleType) -> None:
    out = json.dumps([{"RuleID": "aws"}, {"RuleID": "gh"}])
    assert oracle.count_gitleaks(out) == 2
    assert oracle.count_gitleaks("[]") == 0
    assert oracle.count_gitleaks("") == 0


def test_count_trivy(oracle: ModuleType) -> None:
    out = json.dumps(
        {
            "Results": [
                {"Vulnerabilities": [{"VulnerabilityID": "CVE-1"}, {"VulnerabilityID": "CVE-2"}]},
                {"Vulnerabilities": None},
                {},
            ]
        }
    )
    assert oracle.count_trivy(out) == 2
    assert oracle.count_trivy(json.dumps({"Results": []})) == 0
    assert oracle.count_trivy("") == 0


def test_count_knip(oracle: ModuleType) -> None:
    # knip --reporter json: {"files": [...], "issues": [...]}; count unused files+issues.
    out = json.dumps({"files": ["a.ts", "b.ts"], "issues": []})
    assert oracle.count_knip(out) >= 1
    assert oracle.count_knip(json.dumps({"files": [], "issues": []})) == 0
    assert oracle.count_knip("") == 0


def test_count_jscpd(oracle: ModuleType) -> None:
    out = json.dumps({"duplicates": [{"firstFile": {}, "secondFile": {}}]})
    assert oracle.count_jscpd(out) == 1
    assert oracle.count_jscpd(json.dumps({"duplicates": []})) == 0
    assert oracle.count_jscpd("") == 0


# --------------------------------------------------------------------------- #
# schemathesis (loose; documented shape — reconciled against real output in s5-t2)
# --------------------------------------------------------------------------- #


def test_count_schemathesis(oracle: ModuleType) -> None:
    out = json.dumps({"failures": [{"check": "status_code_conformance"}]})
    assert oracle.count_schemathesis(out) == 1
    assert oracle.count_schemathesis(json.dumps({"failures": []})) == 0
    assert oracle.count_schemathesis("") == 0


# --------------------------------------------------------------------------- #
# radon max_cc
# --------------------------------------------------------------------------- #


def test_max_cc(oracle: ModuleType) -> None:
    # radon cc --json: {path: [ {complexity: N, ...}, ... ]}
    out = json.dumps(
        {
            "a.py": [{"name": "f", "complexity": 3}, {"name": "g", "complexity": 12}],
            "b.py": [{"name": "h", "complexity": 1}],
        }
    )
    assert oracle.max_cc(out) == 12
    assert oracle.max_cc(json.dumps({})) == 0
    assert oracle.max_cc("") == 0


# --------------------------------------------------------------------------- #
# Text emitters (vulture / cohesion)
# --------------------------------------------------------------------------- #


def test_count_text_lines(oracle: ModuleType) -> None:
    out = "a.py:1: unused import 'os'\na.py:5: unused function 'foo'\n\n"
    assert oracle.count_text_lines(out) == 2
    assert oracle.count_text_lines("") == 0
    assert oracle.count_text_lines("\n  \n") == 0


# --------------------------------------------------------------------------- #
# pydeps cycle (precision oracle)
# --------------------------------------------------------------------------- #


def test_pydeps_has_cycle_true(oracle: ModuleType) -> None:
    graph = json.dumps(
        {
            "cyclepkg.a": {"imports": ["cyclepkg", "cyclepkg.b"]},
            "cyclepkg.b": {"imports": ["cyclepkg", "cyclepkg.a"]},
        }
    )
    assert oracle.pydeps_has_cycle(graph, "cyclepkg.a", "cyclepkg.b") is True


def test_pydeps_has_cycle_false_when_back_edge_missing(oracle: ModuleType) -> None:
    graph = json.dumps(
        {
            "cyclepkg.a": {"imports": ["cyclepkg", "cyclepkg.b"]},
            "cyclepkg.b": {"imports": ["cyclepkg"]},  # no back-edge to a
        }
    )
    assert oracle.pydeps_has_cycle(graph, "cyclepkg.a", "cyclepkg.b") is False


def test_pydeps_has_cycle_false_when_forward_edge_missing(oracle: ModuleType) -> None:
    # Symmetric to the back-edge case: a does NOT import b, b imports a. AC says False
    # "when *either* direction is missing".
    graph = json.dumps(
        {
            "cyclepkg.a": {"imports": ["cyclepkg"]},  # no forward edge to b
            "cyclepkg.b": {"imports": ["cyclepkg", "cyclepkg.a"]},
        }
    )
    assert oracle.pydeps_has_cycle(graph, "cyclepkg.a", "cyclepkg.b") is False


def test_pydeps_has_cycle_garbage(oracle: ModuleType) -> None:
    assert oracle.pydeps_has_cycle("", "a", "b") is False
    assert oracle.pydeps_has_cycle("not json", "a", "b") is False


def test_pydeps_max_fanout(oracle: ModuleType) -> None:
    graph = json.dumps(
        {
            "hub": {"imports": ["m0", "m1", "m2"]},
            "leaf": {"imports": []},
            "pkg": {"imported_by": ["hub"]},  # no imports key
        }
    )
    assert oracle.pydeps_max_fanout(graph) == 3
    assert oracle.pydeps_max_fanout(json.dumps({})) == 0
    assert oracle.pydeps_max_fanout("") == 0


# --------------------------------------------------------------------------- #
# depcruiser edge-into / circular (precision oracle)
# --------------------------------------------------------------------------- #


def test_depcruiser_edge_into_mocks_true(oracle: ModuleType) -> None:
    graph = json.dumps(
        {
            "modules": [
                {
                    "source": "src/app.js",
                    "dependencies": [
                        {"resolved": "__mocks__/service.js", "circular": False}
                    ],
                }
            ]
        }
    )
    assert oracle.depcruiser_has_edge_into(graph, "__mocks__") is True


def test_depcruiser_edge_into_segment_not_substring(oracle: ModuleType) -> None:
    # A dir named "x__mocks__y" must NOT match needle "__mocks__" — the oracle matches
    # full path segments, not substrings (this is what makes the precision oracle precise).
    graph = json.dumps(
        {
            "modules": [
                {
                    "source": "src/app.js",
                    "dependencies": [
                        {"resolved": "x__mocks__y/service.js", "circular": False}
                    ],
                }
            ]
        }
    )
    assert oracle.depcruiser_has_edge_into(graph, "__mocks__") is False


def test_depcruiser_edge_into_false_when_source_inside_needle(oracle: ModuleType) -> None:
    # The only edge touching __mocks__ originates *inside* __mocks__ → no prod→mock smell.
    graph = json.dumps(
        {
            "modules": [
                {
                    "source": "__mocks__/a.js",
                    "dependencies": [
                        {"resolved": "__mocks__/b.js", "circular": False}
                    ],
                }
            ]
        }
    )
    assert oracle.depcruiser_has_edge_into(graph, "__mocks__") is False


def test_depcruiser_edge_into_false_when_no_mock_edge(oracle: ModuleType) -> None:
    # Outside source, but no dependency resolves into the needle → False.
    graph = json.dumps(
        {
            "modules": [
                {
                    "source": "src/app.js",
                    "dependencies": [{"resolved": "src/lib.js", "circular": False}],
                }
            ]
        }
    )
    assert oracle.depcruiser_has_edge_into(graph, "__mocks__") is False


def test_depcruiser_edge_into_from_outside_false_counts_intra_mock(
    oracle: ModuleType,
) -> None:
    # With from_outside=False the source filter is dropped, so an intra-mock edge counts.
    graph = json.dumps(
        {
            "modules": [
                {
                    "source": "__mocks__/a.js",
                    "dependencies": [{"resolved": "__mocks__/b.js", "circular": False}],
                }
            ]
        }
    )
    assert oracle.depcruiser_has_edge_into(graph, "__mocks__", from_outside=False) is True


def test_depcruiser_has_circular(oracle: ModuleType) -> None:
    graph = json.dumps(
        {
            "modules": [
                {
                    "source": "src/cycle_a.ts",
                    "dependencies": [{"resolved": "src/cycle_b.ts", "circular": True}],
                }
            ]
        }
    )
    assert oracle.depcruiser_has_circular(graph) is True
    no_cyc = json.dumps(
        {
            "modules": [
                {
                    "source": "src/x.ts",
                    "dependencies": [{"resolved": "src/y.ts", "circular": False}],
                }
            ]
        }
    )
    assert oracle.depcruiser_has_circular(no_cyc) is False
    assert oracle.depcruiser_has_circular("") is False
