"""s0-t1 — ReviewBundle + deterministic JSON + published schema (ADR-0020).

The bundle is the agent's contract: the request echo plus one raw CaptureOutput per
tool, serialised to stable JSON and validated against a published schema. stdout is
deliberately opaque — the schema constrains *structure* (fields, status enum), never the
content of stdout.
"""

from __future__ import annotations

import json

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


def test_raw_stdout_roundtrips() -> None:
    raw = '{not: "json"} ☃ <xml>\nsecond line\t tabbed'
    bundle = ReviewBundle(_request(), (CaptureOutput(tool="x", stdout=raw),))
    back = json.loads(bundle_to_json(bundle))
    # the agent must receive raw output verbatim — no parsing, no mangling
    assert back["outputs"][0]["stdout"] == raw
