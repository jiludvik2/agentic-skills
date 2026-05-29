from __future__ import annotations

from typing import Any

from code_review.aggregator import aggregate
from code_review.contracts import AnalyzerOutput

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sarif(results: list[dict[str, Any]], tool_name: str = "tool") -> dict[str, Any]:
    """Minimal SARIF document with a single run."""
    return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {"driver": {"name": tool_name, "rules": []}},
                "results": results,
            }
        ],
    }


def _result(
    uri: str,
    line: int,
    rule_id: str = "TEST001",
    level: str = "warning",
    cwe: str | None = None,
    props_severity: str | None = None,
    tool: str = "tool",
) -> dict[str, Any]:
    """Build a minimal SARIF result dict."""
    r: dict[str, Any] = {
        "ruleId": rule_id,
        "level": level,
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": uri},
                    "region": {"startLine": line},
                }
            }
        ],
        "properties": {},
    }
    if props_severity:
        r["properties"]["severity"] = props_severity
    if cwe:
        r["taxa"] = [{"id": cwe, "toolComponent": {"name": "CWE"}}]
    return r


def _output(
    results: list[dict[str, Any]], tool_name: str = "tool", **kwargs: Any
) -> AnalyzerOutput:
    return AnalyzerOutput(sarif=_sarif(results, tool_name), **kwargs)


def _consolidated_results(outputs: list[AnalyzerOutput], **kwargs: Any) -> list[dict[str, Any]]:
    consolidated = aggregate(outputs, **kwargs)
    runs = consolidated.get("runs", [])
    if not runs:
        return []
    results: list[dict[str, Any]] = runs[0].get("results", [])
    return results


# ---------------------------------------------------------------------------
# Dedup correctness suite
# ---------------------------------------------------------------------------


def test_same_line_same_cwe_merges() -> None:
    """Two findings at same file+line with same CWE → one consolidated result."""
    r1 = _result("src/auth.py", 47, cwe="CWE-89", level="warning")
    r2 = _result("src/auth.py", 47, cwe="CWE-89", level="error")

    results = _consolidated_results(
        [_output([r1], "semgrep"), _output([r2], "bandit")]
    )

    assert len(results) == 1
    props = results[0].get("properties", {})
    assert set(props.get("sources", [])) == {"semgrep", "bandit"}
    # higher level (error → critical) is preserved
    assert results[0]["level"] == "error"


def test_near_line_same_cwe_merges() -> None:
    """Findings within line_tolerance and same CWE → merged; lower line wins."""
    r1 = _result("src/auth.py", 47, cwe="CWE-89")
    r2 = _result("src/auth.py", 49, cwe="CWE-89")

    results = _consolidated_results(
        [_output([r1], "semgrep"), _output([r2], "bandit")]
    )

    assert len(results) == 1
    props = results[0].get("properties", {})
    assert results[0]["locations"][0]["physicalLocation"]["region"]["startLine"] == 47
    orig = props.get("original_locations", {})
    assert set(orig.keys()) == {"semgrep", "bandit"}
    assert orig["semgrep"] == 47
    assert orig["bandit"] == 49


def test_different_cwe_same_line_does_not_merge() -> None:
    """Same file+line but different CWEs → two separate results."""
    r1 = _result("src/auth.py", 47, cwe="CWE-89")
    r2 = _result("src/auth.py", 47, cwe="CWE-79")

    results = _consolidated_results(
        [_output([r1], "semgrep"), _output([r2], "bandit")]
    )

    assert len(results) == 2


def test_no_cwe_never_merges() -> None:
    """Findings without a CWE tag are never merged even at the same line."""
    r1 = _result("src/auth.py", 47)  # no cwe
    r2 = _result("src/auth.py", 47)  # no cwe

    results = _consolidated_results(
        [_output([r1], "semgrep"), _output([r2], "bandit")]
    )

    assert len(results) == 2


def test_near_line_beyond_tolerance_does_not_merge() -> None:
    """Findings outside line_tolerance are not merged even with same CWE."""
    r1 = _result("src/auth.py", 47, cwe="CWE-89")
    r2 = _result("src/auth.py", 55, cwe="CWE-89")  # distance 8 > default 3

    results = _consolidated_results(
        [_output([r1], "semgrep"), _output([r2], "bandit")]
    )

    assert len(results) == 2


# ---------------------------------------------------------------------------
# CWE taxonomy reference test
# ---------------------------------------------------------------------------


def test_cwe_appears_in_taxa_not_tags() -> None:
    """A CWE-tagged finding: taxa declared; no CWE duplicate in tags."""
    r = _result("src/auth.py", 47, cwe="CWE-89", level="warning")
    consolidated = aggregate([_output([r], "semgrep")])

    runs = consolidated.get("runs", [])
    assert runs, "Expected at least one run"
    run = runs[0]

    # tool.driver.supportedTaxonomies declares CWE
    supported = run.get("tool", {}).get("driver", {}).get("supportedTaxonomies", [])
    assert any(t.get("name") == "CWE" for t in supported), (
        f"supportedTaxonomies missing CWE entry: {supported}"
    )

    # result's taxa references CWE; no free-form CWE tag
    results = run.get("results", [])
    assert results
    result = results[0]
    taxa = result.get("taxa", [])
    assert any(t.get("id", "").startswith("CWE") for t in taxa), (
        f"Expected CWE in taxa: {taxa}"
    )
    tags = result.get("properties", {}).get("tags", [])
    assert not any(str(t).startswith("CWE") for t in tags), (
        f"CWE should not appear as free-form tag: {tags}"
    )


# ---------------------------------------------------------------------------
# sdlc_severity tagging test
# ---------------------------------------------------------------------------


def test_sdlc_severity_tagged_on_all_results() -> None:
    """Every consolidated result gains properties.sdlc_severity."""
    results_in = [
        _result("a.py", 1, level="error"),
        _result("b.py", 2, level="warning"),
        _result("c.py", 3, level="note"),
    ]
    results_out = _consolidated_results([_output(results_in, "tool")])

    assert len(results_out) == 3
    severities = {r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]:
                  r.get("properties", {}).get("sdlc_severity")
                  for r in results_out}
    assert severities["a.py"] == "critical"
    assert severities["b.py"] == "minor"
    assert severities["c.py"] == "nit"


# ---------------------------------------------------------------------------
# Empty input test
# ---------------------------------------------------------------------------


def test_aggregate_empty_input() -> None:
    """aggregate([]) returns a valid SARIF document with no exception."""
    consolidated = aggregate([])
    assert "runs" in consolidated
    assert isinstance(consolidated["runs"], list)


# ---------------------------------------------------------------------------
# Error passthrough test
# ---------------------------------------------------------------------------


def test_error_status_passthrough() -> None:
    """Error-status analyzer is skipped for findings but error is recorded."""
    good = _output([_result("src/ok.py", 1)], "good_tool")
    bad = AnalyzerOutput(sarif={}, status="error", error="tool crashed")

    consolidated = aggregate([good, bad])
    results = consolidated.get("runs", [{}])[0].get("results", [])
    assert len(results) == 1  # only good_tool's finding

    errors = consolidated.get("properties", {}).get("analyzer_errors", [])
    assert len(errors) == 1
    assert errors[0]["error"] == "tool crashed"


def test_missing_level_does_not_raise() -> None:
    """A result with no 'level' key is handled without KeyError."""
    r = _result("src/a.py", 1, cwe="CWE-89")
    del r["level"]
    r2 = _result("src/a.py", 2, cwe="CWE-89", level="warning")
    # near-line merge exercises the merged[i]["level"] path
    aggregate([_output([r], "tool_a"), _output([r2], "tool_b")])  # must not raise


def test_aggregate_does_not_mutate_inputs() -> None:
    """aggregate() must not corrupt original AnalyzerOutput.sarif data."""
    r1 = _result("src/auth.py", 47, cwe="CWE-89")
    r2 = _result("src/auth.py", 45, cwe="CWE-89")  # lower line; near-line merge fires
    outputs = [_output([r1], "semgrep"), _output([r2], "bandit")]

    aggregate(outputs)

    # r1's original line must be unchanged after aggregation
    original_line = (
        outputs[0].sarif["runs"][0]["results"][0]
        ["locations"][0]["physicalLocation"]["region"]["startLine"]
    )
    assert original_line == 47, (
        f"aggregate() mutated input sarif: startLine changed from 47 to {original_line}"
    )


def test_ruleid_cwe_moved_to_taxa() -> None:
    """A finding whose ruleId is a CWE id has that CWE appear in taxa."""
    r: dict[str, Any] = {
        "ruleId": "CWE-89",
        "level": "warning",
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": "src/auth.py"},
                    "region": {"startLine": 10},
                }
            }
        ],
        "properties": {},
    }
    consolidated = aggregate([_output([r], "semgrep")])
    results = consolidated["runs"][0]["results"]
    assert results
    taxa = results[0].get("taxa", [])
    assert any(t.get("id", "").startswith("CWE") for t in taxa), (
        f"Expected CWE in taxa after ruleId normalisation: {taxa}"
    )
