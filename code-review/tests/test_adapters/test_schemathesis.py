from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import jsonschema
import pytest

SARIF_SCHEMA = (
    Path(__file__).parent.parent.parent / "code_review" / "schemas" / "sarif-2.1.0.json"
)

fastapi = pytest.importorskip("fastapi", reason="fastapi required for schemathesis tests")
uvicorn = pytest.importorskip("uvicorn", reason="uvicorn required for schemathesis tests")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_request(contract_config: dict[str, Any]) -> Any:
    from code_review.contracts import ReviewRequest

    return ReviewRequest(
        scope="story-level",
        diff_range=None,
        target_paths=(),
        languages=frozenset(),
        config={"contract_testing": contract_config},
    )


# ---------------------------------------------------------------------------
# 1. Protocol conformance
# ---------------------------------------------------------------------------


def test_schemathesis_adapter_protocol_conformance() -> None:
    from code_review.adapters.schemathesis_ import SchemathesisAdapter
    from code_review.contracts import Analyzer

    adapter = SchemathesisAdapter()
    assert isinstance(adapter, Analyzer)
    assert SchemathesisAdapter.name == "schemathesis"
    assert SchemathesisAdapter.kind == "contract"
    assert SchemathesisAdapter.default_timeout_s == 600
    assert SchemathesisAdapter.scope_restrictions == frozenset({"story-level"})


# ---------------------------------------------------------------------------
# 2. No targets → empty ok
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_targets_returns_empty_ok() -> None:
    from code_review.adapters.schemathesis_ import SchemathesisAdapter

    request = _make_request({})
    output = await SchemathesisAdapter().run(request)
    assert output.status == "ok"
    runs = output.sarif.get("runs", [])
    total_results = sum(len(r.get("results", [])) for r in runs)
    assert total_results == 0


# ---------------------------------------------------------------------------
# 3. Failure → SARIF mapping helper (unit test with synthetic data)
# ---------------------------------------------------------------------------


def test_failure_to_sarif_result() -> None:
    from code_review.adapters.schemathesis_ import _failure_to_sarif_result

    mock_failure = MagicMock()
    mock_failure.title = "response_schema_violation"
    mock_failure.message = "Field 'user_name' missing"
    mock_failure.operation = "GET /users/{user_id}"

    result = _failure_to_sarif_result(mock_failure)

    assert result["ruleId"] == "schemathesis.response_schema_violation"
    assert result["level"] == "error"
    assert "GET /users/{user_id}" in result["properties"]["endpoint"]
    assert "Field 'user_name' missing" in result["message"]["text"]
    assert result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "api"


def test_conformance_failure_maps_to_response_schema_violation() -> None:
    """A response_schema_conformance failure (class JsonSchemaError, title 'Response violates
    schema') must map to the stable ruleId schemathesis.response_schema_violation — NOT a slug of
    the human-readable title (which would be 'response_violates_schema')."""
    from code_review.adapters.schemathesis_ import _failure_to_sarif_result

    class JsonSchemaError(Exception):  # mirrors Schemathesis 4.0.10's failure class name
        title = "Response violates schema"
        message = "'user_name' is a required property"
        operation = "GET /users/{user_id}"

    result = _failure_to_sarif_result(JsonSchemaError())

    assert result["ruleId"] == "schemathesis.response_schema_violation"
    assert result["level"] == "error"
    assert "user_name" in result["message"]["text"]
    assert result["properties"]["endpoint"] == "GET /users/{user_id}"


def test_server_error_maps_to_stable_ruleid() -> None:
    """A server-error failure maps to schemathesis.server_error regardless of title phrasing."""
    from code_review.adapters.schemathesis_ import _failure_to_sarif_result

    class ServerError(Exception):  # mirrors Schemathesis 4.0.10's failure class name
        title = "Server error (5xx)"  # punctuation that a naive slug would mangle
        message = "500 Internal Server Error"
        operation = "GET /items"

    result = _failure_to_sarif_result(ServerError())

    assert result["ruleId"] == "schemathesis.server_error"


# ---------------------------------------------------------------------------
# 3b. Unexpected execution errors surface as findings (not swallowed) — F1
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unexpected_exception_becomes_execution_error_finding() -> None:
    """A non-FailureGroup error from call_and_validate (connection drop, validation
    bug) must yield one schemathesis.execution-error finding naming the operation —
    never be swallowed as a (false) conformant pass (bandit B110)."""
    from code_review.adapters.schemathesis_ import _failure_to_sarif_result, _run_operation

    mock_op = MagicMock()
    mock_op.label = "GET /widgets"
    mock_case = MagicMock()
    mock_case.call_and_validate.side_effect = RuntimeError("boom")

    with patch("code_review.adapters.schemathesis_.h_find", return_value=mock_case):
        failures = await _run_operation(mock_op, MagicMock())

    assert len(failures) == 1, failures
    result = _failure_to_sarif_result(failures[0])
    assert result["ruleId"] == "schemathesis.execution-error"
    assert result["level"] == "error"
    assert result["properties"]["endpoint"] == "GET /widgets"
    assert "boom" in result["message"]["text"]


@pytest.mark.asyncio
async def test_failure_group_path_unchanged() -> None:
    """Regression: a FailureGroup is still unpacked into its constituent failures,
    unchanged by the execution-error handling."""
    from schemathesis.core.failures import FailureGroup

    from code_review.adapters.schemathesis_ import _failure_to_sarif_result, _run_operation

    class JsonSchemaError(Exception):  # mirrors Schemathesis 4.0.10's failure class name
        title = "Response violates schema"
        message = "'user_name' is a required property"
        operation = "GET /users"

    mock_op = MagicMock()
    mock_op.label = "GET /users"
    mock_case = MagicMock()
    mock_case.call_and_validate.side_effect = FailureGroup([JsonSchemaError()])

    with patch("code_review.adapters.schemathesis_.h_find", return_value=mock_case):
        failures = await _run_operation(mock_op, MagicMock())

    assert len(failures) == 1, failures
    result = _failure_to_sarif_result(failures[0])
    assert result["ruleId"] == "schemathesis.response_schema_violation"
    assert "user_name" in result["message"]["text"]


# ---------------------------------------------------------------------------
# 4. Auth from env var
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auth_token_read_from_env_not_in_sarif() -> None:
    from code_review.adapters.schemathesis_ import SchemathesisAdapter

    target_cfg = {
        "my-api": {
            "spec_url": "http://localhost:9/openapi.json",
            "base_url": "http://localhost:9",
            "auth": {"token_env": "MY_TEST_TOKEN"},
            "timeout_s": 60,
        }
    }
    request = _make_request(target_cfg)

    session_headers_captured: dict[str, str] = {}

    async def fake_run_operation(op: Any, session: Any) -> list[Any]:
        session_headers_captured.update(dict(session.headers))
        return []

    mock_op = MagicMock(spec=["ok", "as_strategy"])
    mock_op.ok.return_value = mock_op

    mock_schema = MagicMock()
    mock_schema.get_all_operations.return_value = [mock_op]

    with (
        patch.dict(os.environ, {"MY_TEST_TOKEN": "super-secret-token"}),
        patch(
            "schemathesis.openapi.from_url",
            return_value=mock_schema,
        ),
        patch(
            "code_review.adapters.schemathesis_._run_operation",
            side_effect=fake_run_operation,
        ),
    ):
        output = await SchemathesisAdapter().run(request)

    sarif_text = json.dumps(output.sarif)
    assert "super-secret-token" not in sarif_text
    # Minor #7: the token must also never leak into the error channel the sub-agent reads.
    assert "super-secret-token" not in (output.error or "")
    auth_header = session_headers_captured.get("Authorization", "")
    assert auth_header == "Bearer super-secret-token"


# ---------------------------------------------------------------------------
# 5. Cache redirect: HYPOTHESIS_STORAGE_DIRECTORY set under $TMPDIR
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hypothesis_cache_redirected_to_tmpdir(tmp_path: Path) -> None:
    from code_review.adapters.schemathesis_ import SchemathesisAdapter

    request = _make_request({
        "target": {
            "spec_url": "http://localhost:9/openapi.json",
            "base_url": "http://localhost:9",
            "auth": {"token_env": "NONEXISTENT_TOKEN_XYZ"},
            "timeout_s": 1,
        }
    })

    storage_dir_seen: list[str] = []

    def capturing_from_url(*args: Any, **kwargs: Any) -> Any:
        storage_dir_seen.append(os.environ.get("HYPOTHESIS_STORAGE_DIRECTORY", ""))
        raise ConnectionError("simulated unreachable")

    with (
        patch.dict(os.environ, {"TMPDIR": str(tmp_path)}),
        patch("schemathesis.openapi.from_url", side_effect=capturing_from_url),
    ):
        await SchemathesisAdapter().run(request)

    assert storage_dir_seen, "from_url was never called"
    assert storage_dir_seen[0].startswith(str(tmp_path)), (
        f"HYPOTHESIS_STORAGE_DIRECTORY={storage_dir_seen[0]!r} is not under TMPDIR={tmp_path}"
    )


# ---------------------------------------------------------------------------
# 6. Unreachable target → status=error with sandbox hint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hypothesis_env_var_restored_after_run(monkeypatch: Any) -> None:
    """The adapter must not leave HYPOTHESIS_STORAGE_DIRECTORY mutated in the process env
    (it runs in-process per ADR-0009, so a leak crosses analyzers/runs)."""
    from code_review.adapters.schemathesis_ import SchemathesisAdapter

    request = _make_request({
        "target": {
            "spec_url": "http://localhost:9/openapi.json",
            "base_url": "http://localhost:9",
            "auth": {"token_env": "NONE"},
            "timeout_s": 1,
        }
    })

    def boom(*a: Any, **k: Any) -> Any:
        raise ConnectionError("unreachable")  # enters the tmpdir block, then errors out

    # Case 1: var previously unset → must be absent again after the run.
    monkeypatch.delenv("HYPOTHESIS_STORAGE_DIRECTORY", raising=False)
    with patch("schemathesis.openapi.from_url", side_effect=boom):
        await SchemathesisAdapter().run(request)
    assert "HYPOTHESIS_STORAGE_DIRECTORY" not in os.environ

    # Case 2: var previously set to a sentinel → must be restored to the sentinel.
    monkeypatch.setenv("HYPOTHESIS_STORAGE_DIRECTORY", "/sentinel/path")
    with patch("schemathesis.openapi.from_url", side_effect=boom):
        await SchemathesisAdapter().run(request)
    assert os.environ["HYPOTHESIS_STORAGE_DIRECTORY"] == "/sentinel/path"


@pytest.mark.asyncio
async def test_unreachable_target_returns_error() -> None:
    from code_review.adapters.schemathesis_ import SchemathesisAdapter

    request = _make_request({
        "dead": {
            "spec_url": "http://localhost:1/openapi.json",
            "base_url": "http://localhost:1",
            "auth": {"token_env": "NONE"},
            "timeout_s": 5,
        }
    })
    output = await SchemathesisAdapter().run(request)
    assert output.status == "error"
    assert output.error is not None
    assert "sandbox.allowedDomains" in output.error


# ---------------------------------------------------------------------------
# 7. Deadline / timeout: partial findings preserved
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeout_status_with_partial_findings() -> None:
    """
    Exercises the timeout path: first operation returns a finding (and sleeps briefly
    to ensure elapsed > timeout_s), second operation is never reached because the
    timeout check fires at the top of the loop.  Asserts status="timeout" and that
    the partial finding is preserved in SARIF.
    """
    import asyncio as _asyncio

    from code_review.adapters.schemathesis_ import SchemathesisAdapter

    # Two mock operations — op1 produces a finding, op2 should never execute.
    mock_op1 = MagicMock(spec=["ok", "as_strategy"])
    mock_op1.ok.return_value = mock_op1
    mock_op2 = MagicMock(spec=["ok", "as_strategy"])
    mock_op2.ok.return_value = mock_op2

    mock_schema = MagicMock()
    mock_schema.get_all_operations.return_value = [mock_op1, mock_op2]

    first_call_done = False

    async def first_returns_finding_second_unreachable(op: Any, session: Any) -> list[Any]:
        nonlocal first_call_done
        if not first_call_done:
            first_call_done = True
            # Sleep long enough to ensure elapsed > timeout_s=0.001 s after this call.
            await _asyncio.sleep(0.05)
            mock_failure = MagicMock()
            mock_failure.title = "server_error"
            mock_failure.message = "500"
            mock_failure.operation = "GET /items"
            return [mock_failure]
        # Should never be reached — the timeout check fires before op2.
        return []

    request = _make_request({
        "target": {
            "spec_url": "http://localhost:9/openapi.json",
            "base_url": "http://localhost:9",
            "auth": {"token_env": "NONE"},
            "timeout_s": 0.001,  # expires after the first _run_operation sleep
        }
    })

    with (
        patch("schemathesis.openapi.from_url", return_value=mock_schema),
        patch(
            "code_review.adapters.schemathesis_._run_operation",
            side_effect=first_returns_finding_second_unreachable,
        ),
    ):
        output = await SchemathesisAdapter().run(request)

    assert output.status == "timeout", (
        f"expected status='timeout', got {output.status!r}"
    )
    results = output.sarif.get("runs", [{}])[0].get("results", [])
    assert len(results) >= 1, (
        f"expected at least 1 partial finding in SARIF, got {results!r}"
    )


# ---------------------------------------------------------------------------
# 8. Integration test — real Schemathesis run against fixture app
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_integration_real_schemathesis_run() -> None:
    from code_review.adapters.schemathesis_ import SchemathesisAdapter

    sys = __import__("sys")
    fixture_dir = (
        Path(__file__).parent.parent / "fixtures" / "schemathesis-target"
    )
    sys.path.insert(0, str(fixture_dir))
    try:
        from app import running_server  # type: ignore[import-not-found]
    finally:
        sys.path.pop(0)

    with running_server() as base_url:
        spec_url = f"{base_url}/openapi.json"
        request = _make_request({
            "fixture-app": {
                "spec_url": spec_url,
                "base_url": base_url,
                "auth": {"token_env": "NONEXISTENT_FOR_TEST"},
                "timeout_s": 120,
            }
        })
        output = await SchemathesisAdapter().run(request)

    assert output.status in ("ok", "timeout"), (
        f"unexpected status: {output.status!r} / {output.error}"
    )

    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)

    runs = output.sarif.get("runs", [])
    results = [r for run in runs for r in run.get("results", [])]
    # AC #1: the planted 2xx schema drift (handler returns `username`, OpenAPI declares
    # `user_name`) must surface as response_schema_violation naming the divergent field.
    violations = [r for r in results if r["ruleId"] == "schemathesis.response_schema_violation"]
    assert violations, (
        "expected a schemathesis.response_schema_violation finding for the planted drift; got "
        f"{[r['ruleId'] for r in results]!r}"
    )
    assert any("user_name" in v["message"]["text"] for v in violations), (
        "expected the violation message to name the divergent field 'user_name'"
    )
