"""Tests for CLI aggregation wiring: s2-t4."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, ClassVar

import jsonschema
import pytest
from typer.testing import CliRunner

import code_review.adapters as adapters_mod
from code_review.cli import app
from code_review.contracts import AnalyzerOutput, ReviewRequest

_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent
    / ".claude" / "skills" / "code-review" / "schemas" / "review-response.json"
)

runner = CliRunner()


def _sarif(findings: list[dict[str, Any]], tool: str = "test") -> dict[str, Any]:
    return {
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": tool}}, "results": findings}],
    }


def _finding(uri: str, line: int, cwe: str, level: str = "warning") -> dict[str, Any]:
    return {
        "ruleId": "TEST001",
        "level": level,
        "locations": [{"physicalLocation": {
            "artifactLocation": {"uri": uri},
            "region": {"startLine": line},
        }}],
        "taxa": [{"id": cwe, "toolComponent": {"name": "CWE"}}],
        "properties": {},
    }


class _FakeA:
    name: ClassVar[str] = "fake_a"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 30
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        return AnalyzerOutput(
            sarif=_sarif([_finding("src/auth.py", 10, "CWE-89", "error")], "fake_a"),
            status="ok",
        )


class _FakeB:
    name: ClassVar[str] = "fake_b"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 30
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        return AnalyzerOutput(
            sarif=_sarif([_finding("src/utils.py", 5, "CWE-79", "warning")], "fake_b"),
            status="ok",
        )


# ---------------------------------------------------------------------------
# End-to-end shape test
# ---------------------------------------------------------------------------


def test_output_has_required_top_level_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(adapters_mod.REGISTRY, "fake_a", _FakeA)
    monkeypatch.setitem(adapters_mod.REGISTRY, "fake_b", _FakeB)

    result = runner.invoke(
        app, ["--analyzer", "fake_a", "--analyzer", "fake_b", "--target", "."]
    )

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "sarif" in data, f"missing 'sarif' key: {list(data)}"
    assert "metrics" in data, f"missing 'metrics' key: {list(data)}"
    assert "ranked_hotspots" in data, f"missing 'ranked_hotspots' key: {list(data)}"
    assert "analyzers" in data, f"missing 'analyzers' key: {list(data)}"
    assert isinstance(data["sarif"]["runs"], list)
    assert isinstance(data["ranked_hotspots"], list)


# ---------------------------------------------------------------------------
# Aggregation dedup test
# ---------------------------------------------------------------------------


def test_aggregation_deduplicates_overlapping_findings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two analyzers returning same file/line/CWE → one result after dedup."""

    class _DupA:
        name: ClassVar[str] = "dup_a"
        kind: ClassVar[str] = "deterministic"
        default_timeout_s: ClassVar[int] = 30
        scope_restrictions: ClassVar[frozenset[str]] = frozenset()

        async def run(self, request: ReviewRequest) -> AnalyzerOutput:
            return AnalyzerOutput(
                sarif=_sarif([_finding("src/auth.py", 10, "CWE-89", "error")], "dup_a"),
                status="ok",
            )

    class _DupB:
        name: ClassVar[str] = "dup_b"
        kind: ClassVar[str] = "deterministic"
        default_timeout_s: ClassVar[int] = 30
        scope_restrictions: ClassVar[frozenset[str]] = frozenset()

        async def run(self, request: ReviewRequest) -> AnalyzerOutput:
            return AnalyzerOutput(
                sarif=_sarif([_finding("src/auth.py", 10, "CWE-89", "error")], "dup_b"),
                status="ok",
            )

    monkeypatch.setitem(adapters_mod.REGISTRY, "dup_a", _DupA)
    monkeypatch.setitem(adapters_mod.REGISTRY, "dup_b", _DupB)

    result = runner.invoke(
        app, ["--analyzer", "dup_a", "--analyzer", "dup_b", "--target", "."]
    )

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    results = data["sarif"]["runs"][0]["results"]
    assert len(results) == 1, (
        f"Expected 1 deduplicated result, got {len(results)}: {results}"
    )


# ---------------------------------------------------------------------------
# Per-task vs story-level hotspot scope
# ---------------------------------------------------------------------------


async def _mock_resolve(repo_root: object, diff_range: object) -> tuple[str, ...]:
    return ("src/auth.py",)


def test_per_task_hotspots_restricted_to_diff(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(adapters_mod.REGISTRY, "fake_a", _FakeA)
    monkeypatch.setitem(adapters_mod.REGISTRY, "fake_b", _FakeB)
    monkeypatch.setattr("code_review.cli.resolve_diff_paths", _mock_resolve)

    result = runner.invoke(
        app, ["--analyzer", "fake_a", "--analyzer", "fake_b", "--diff", "HEAD~1..HEAD"]
    )

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    hotspot_files = {h["file"] for h in data["ranked_hotspots"]}
    assert hotspot_files <= {"src/auth.py"}, (
        f"Per-task hotspots should be restricted to diff files; got {hotspot_files}"
    )


def test_story_level_hotspots_include_all_files(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(adapters_mod.REGISTRY, "fake_a", _FakeA)
    monkeypatch.setitem(adapters_mod.REGISTRY, "fake_b", _FakeB)

    result = runner.invoke(
        app, ["--analyzer", "fake_a", "--analyzer", "fake_b", "--target", "."]
    )

    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    hotspot_files = {h["file"] for h in data["ranked_hotspots"]}
    assert "src/auth.py" in hotspot_files or "src/utils.py" in hotspot_files, (
        f"Story-level hotspots should include all files; got {hotspot_files}"
    )


# ---------------------------------------------------------------------------
# Schema validation round-trip
# ---------------------------------------------------------------------------


def test_output_validates_against_review_response_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(adapters_mod.REGISTRY, "fake_a", _FakeA)
    monkeypatch.setitem(adapters_mod.REGISTRY, "fake_b", _FakeB)

    result = runner.invoke(
        app, ["--analyzer", "fake_a", "--analyzer", "fake_b", "--target", "."]
    )

    assert result.exit_code == 0, result.output
    schema = json.loads(_SCHEMA_PATH.read_text())
    data = json.loads(result.output)
    jsonschema.validate(instance=data, schema=schema)  # raises ValidationError if invalid


# ---------------------------------------------------------------------------
# Schema warning non-fatal
# ---------------------------------------------------------------------------


def test_schema_validation_failure_is_non_fatal(monkeypatch: pytest.MonkeyPatch) -> None:
    import jsonschema as _jsonschema
    monkeypatch.setitem(adapters_mod.REGISTRY, "fake_a", _FakeA)

    def _raise(*args: Any, **kwargs: Any) -> None:
        raise _jsonschema.ValidationError("injected failure")

    monkeypatch.setattr("code_review.cli.jsonschema.validate", _raise)

    # Typer's CliRunner mixes stderr into result.output; the warning lands there.
    result = runner.invoke(app, ["--analyzer", "fake_a", "--target", "."])

    assert result.exit_code == 0, f"Schema validation failure must not crash CLI: {result.output}"
    assert "schema" in result.output.lower(), "Expected schema warning in output"


def test_missing_schema_file_skipped_silently(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setitem(adapters_mod.REGISTRY, "fake_a", _FakeA)
    nonexistent = tmp_path / "no-such-schema.json"
    monkeypatch.setattr("code_review.cli._SCHEMA_PATH", nonexistent)

    result = runner.invoke(app, ["--analyzer", "fake_a", "--target", "."])

    assert result.exit_code == 0, f"Missing schema must not crash CLI: {result.output}"
    data = json.loads(result.output)
    assert "sarif" in data


# ---------------------------------------------------------------------------
# ConfigError handling
# ---------------------------------------------------------------------------


def test_config_error_exits_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    from code_review.config import ConfigError

    def _raise(_skill_dir: Any) -> None:
        raise ConfigError("injected: bad toml")

    monkeypatch.setitem(adapters_mod.REGISTRY, "fake_a", _FakeA)
    monkeypatch.setattr("code_review.cli.load_config", _raise)

    # Typer's CliRunner mixes stderr into result.output; error message lands there.
    result = runner.invoke(app, ["--analyzer", "fake_a", "--target", "."])

    assert result.exit_code != 0, "ConfigError must produce non-zero exit"
    assert "injected: bad toml" in result.output, "Error message must appear in output"
    assert "Traceback" not in result.output, "Must not leak a raw Python traceback"
