"""s0-t1 — ReviewBundle + deterministic JSON + published schema (ADR-0020).

The bundle is the agent's contract: the request echo plus one raw CaptureOutput per
tool, serialised to stable JSON and validated against a published schema. stdout is
deliberately opaque — the schema constrains *structure* (fields, status enum), never the
content of stdout.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from code_review.capture import CaptureOutput
from code_review.contracts import ReviewRequest
from code_review.review_bundle import (
    SCHEMA_ID,
    ReviewBundle,
    bundle_to_json,
    load_bundle_schema,
)


def _request() -> ReviewRequest:
    return ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=("app.py", "lib.py"),
        languages=frozenset({"python", "javascript"}),
        config={"ignored": "by-the-bundle"},
    )


def _mixed_outputs() -> tuple[CaptureOutput, ...]:
    return (
        CaptureOutput(tool="bandit", stdout="raw-bandit-json", exit_code=0,
                      command=("python", "-m", "bandit")),
        CaptureOutput.unavailable("eslint", "no config"),
        CaptureOutput(tool="semgrep", status="error", exit_code=2,
                      stderr="kaboom", error="exited 2: kaboom"),
    )


def test_bundle_to_dict_shape() -> None:
    d = ReviewBundle(_request(), _mixed_outputs()).to_dict()
    assert d["schema"] == "polyreview/review-bundle/v1"
    assert d["schema"] == SCHEMA_ID

    req = d["request"]
    assert req["scope"] == "per-task"
    assert req["diff_range"] is None
    assert req["target_paths"] == ["app.py", "lib.py"]
    # frozenset echoed as a sorted list (deterministic)
    assert req["languages"] == ["javascript", "python"]
    # config is deliberately NOT echoed into the bundle
    assert "config" not in req

    assert len(d["outputs"]) == 3
    first = d["outputs"][0]
    assert set(first) == {
        "tool", "status", "exit_code", "stdout", "stderr",
        "error", "command", "duration_s",
    }
    assert first["tool"] == "bandit"
    assert first["command"] == ["python", "-m", "bandit"]


def test_bundle_json_deterministic() -> None:
    bundle = ReviewBundle(_request(), _mixed_outputs())
    first = bundle_to_json(bundle)
    second = bundle_to_json(bundle)
    assert first == second  # byte-identical across calls
    # keys are sorted — re-serialising the parsed dict with sort_keys is a no-op
    assert first == json.dumps(json.loads(first), sort_keys=True, ensure_ascii=False)


def test_bundle_validates_against_schema() -> None:
    schema = load_bundle_schema()
    bundle = ReviewBundle(_request(), _mixed_outputs())
    # mixed ok / unavailable / error must validate clean
    jsonschema.validate(bundle.to_dict(), schema)


def test_invalid_bundle_rejected() -> None:
    schema = load_bundle_schema()

    bogus_status = ReviewBundle(_request(), _mixed_outputs()).to_dict()
    bogus_status["outputs"][0]["status"] = "weird"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bogus_status, schema)

    missing_tool = ReviewBundle(_request(), _mixed_outputs()).to_dict()
    del missing_tool["outputs"][0]["tool"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(missing_tool, schema)


def test_unavailable_capture_in_bundle() -> None:
    bundle = ReviewBundle(_request(), (CaptureOutput.unavailable("eslint", "no config"),))
    d = bundle.to_dict()
    out = d["outputs"][0]
    assert out["status"] == "unavailable"
    assert out["stdout"] == ""
    assert out["error"] == "no config"
    assert out["exit_code"] is None
    jsonschema.validate(d, load_bundle_schema())


def test_bundle_includes_timeout_capture() -> None:
    """s0 Minor #2: a `timeout` capture serialises and schema-validates in the bundle —
    the ADR-0019 status enum admits it and the killed-tool shape (no exit code) is faithful."""
    cap = CaptureOutput(
        tool="slow", status="timeout", error="timed out after 0.5s", exit_code=None
    )
    bundle = ReviewBundle(_request(), (cap,))
    d = bundle.to_dict()
    out = d["outputs"][0]
    assert out["status"] == "timeout"
    assert out["exit_code"] is None
    assert out["error"] == "timed out after 0.5s"
    jsonschema.validate(d, load_bundle_schema())


def test_raw_stdout_roundtrips() -> None:
    raw = '{not: "json"} ☃ <xml>\nsecond line\t tabbed'
    bundle = ReviewBundle(_request(), (CaptureOutput(tool="x", stdout=raw),))
    back = json.loads(bundle_to_json(bundle))
    # the agent must receive raw output verbatim — no parsing, no mangling
    assert back["outputs"][0]["stdout"] == raw


def test_raw_stdout_roundtrips_non_utf8() -> None:
    """Control chars and non-ASCII bytes round-trip verbatim (ensure_ascii=False)."""
    raw = "line1\x00\x01\x1f\x7f\x80\xff line2 café 😀"
    bundle = ReviewBundle(_request(), (CaptureOutput(tool="x", stdout=raw),))
    back = json.loads(bundle_to_json(bundle))
    assert back["outputs"][0]["stdout"] == raw


def test_empty_outputs_bundle_valid() -> None:
    """A bundle with no analyzer outputs is still schema-valid."""
    bundle = ReviewBundle(_request(), ())
    d = bundle.to_dict()
    assert d["outputs"] == []
    jsonschema.validate(d, load_bundle_schema())


# ---------------------------------------------------------------------------
# Golden-bundle regression guard
# ---------------------------------------------------------------------------

_FIXTURES = Path(__file__).parent / "fixtures"
_GOLDEN_PATH = _FIXTURES / "golden_review_bundle.json"

_GOLDEN_REQUEST = ReviewRequest(
    scope="per-task",
    diff_range="HEAD~3..HEAD",
    target_paths=("/repo/src/auth.py", "/repo/src/models.py"),
    languages=frozenset({"python"}),
    config={},
)

# Trimmed but representative raw tool outputs spanning all three format families
# and all four ADR-0019 statuses.
_GOLDEN_OUTPUTS: tuple[CaptureOutput, ...] = (
    # JSON format, ok (bandit)
    CaptureOutput(
        tool="bandit",
        stdout=(
            '{"errors":[],"metrics":{},"results":['
            '{"filename":"/repo/src/auth.py","issue_severity":"LOW",'
            '"issue_text":"hard-coded password","test_id":"B105"}]}'
        ),
        stderr="",
        exit_code=1,
        command=("python", "-m", "bandit", "-r", "/repo/src", "-f", "json"),
        duration_s=0.0,
    ),
    # SARIF format, ok (semgrep)
    CaptureOutput(
        tool="semgrep",
        stdout=(
            '{"runs":[{"results":[{"level":"error",'
            '"message":{"text":"SQL injection"},'
            '"ruleId":"python.inject.sql"}]}],"version":"2.1.0"}'
        ),
        stderr="",
        exit_code=0,
        command=("semgrep", "--sarif", "--config", "p/ci"),
        duration_s=0.0,
    ),
    # Plain text, ok (vulture)
    CaptureOutput(
        tool="vulture",
        stdout="/repo/src/auth.py:42: unused variable 'tmp' (60% confidence)\n",
        stderr="",
        exit_code=0,
        command=("vulture", "/repo/src"),
        duration_s=0.0,
    ),
    # error (trivy — DB absent)
    CaptureOutput(
        tool="trivy",
        stdout="",
        stderr="FATAL: DB error: failed to open DB\n",
        exit_code=None,
        status="error",
        error="exited 1: FATAL: DB error: failed to open DB",
        command=("trivy", "fs", "--format", "sarif", "/repo"),
        duration_s=0.0,
    ),
    # timeout (gitleaks)
    CaptureOutput(
        tool="gitleaks",
        stdout="",
        stderr="",
        exit_code=None,
        status="timeout",
        error="timed out after 60s",
        command=("gitleaks", "detect", "--source", "/repo"),
        duration_s=0.0,
    ),
    # unavailable (radon)
    CaptureOutput.unavailable("radon", "radon not found on PATH"),
)


def test_golden_bundle_byte_equal() -> None:
    """The emitted bundle must be byte-equal to the committed golden fixture.

    If the contract changes intentionally, regenerate with:
        python -c "
    from tests.test_review_bundle import _GOLDEN_REQUEST, _GOLDEN_OUTPUTS
    from code_review.review_bundle import ReviewBundle, bundle_to_json
    from pathlib import Path
    p = Path('tests/fixtures/golden_review_bundle.json')
    p.write_text(bundle_to_json(ReviewBundle(_GOLDEN_REQUEST, _GOLDEN_OUTPUTS)))
    "
    """
    assert _GOLDEN_PATH.exists(), (
        "golden fixture missing — generate it with the one-liner in this test's docstring"
    )
    bundle = ReviewBundle(_GOLDEN_REQUEST, _GOLDEN_OUTPUTS)
    assert bundle_to_json(bundle) == _GOLDEN_PATH.read_text(encoding="utf-8")
    jsonschema.validate(bundle.to_dict(), load_bundle_schema())
