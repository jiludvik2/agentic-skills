import json
from pathlib import Path
from unittest.mock import patch

import jsonschema

FIXTURE = Path(__file__).parent.parent / "fixtures" / "python-with-known-issues"
SARIF_SCHEMA = Path(__file__).parent.parent.parent / "code_review" / "schemas" / "sarif-2.1.0.json"

# A minimal but valid bandit --format json document (one shell-injection finding).
_BANDIT_JSON = json.dumps(
    {
        "errors": [],
        "results": [
            {
                "test_id": "B602",
                "issue_text": "subprocess call with shell=True identified",
                "filename": "app.py",
                "line_number": 3,
                "issue_cwe": {"id": 78},
            }
        ],
    }
).encode()

# Newer bandit renders a Rich progress bar to STDOUT before the JSON (s0-t0 / F3).
_PROGRESS_BAR = "Working... ━━━━━━ 100% 0:00:00\n".encode()


def _result(stdout: bytes, returncode: int = 1):
    from code_review.adapters.base import SubprocessResult

    return SubprocessResult(stdout, b"", returncode)


def _py_request():
    from code_review.contracts import ReviewRequest

    return ReviewRequest(
        scope="per-task", diff_range=None, target_paths=("app.py",),
        languages=frozenset({"python"}), config={},
    )


async def test_bandit_parses_stdout_with_progress_bar_prefix() -> None:
    # F3: a progress bar ahead of the JSON must not break parsing.
    from code_review.adapters.bandit import BanditAdapter

    with patch(
        "code_review.adapters.bandit.run_subprocess",
        return_value=_result(_PROGRESS_BAR + _BANDIT_JSON),
    ):
        output = await BanditAdapter().run(_py_request())
    assert output.status == "ok", output.error
    rule_ids = [r["ruleId"] for r in output.sarif["runs"][0]["results"]]
    assert "bandit.B602" in rule_ids


async def test_bandit_parses_plain_json_stdout() -> None:
    # Regression: pure-JSON stdout (no progress bar) still parses.
    from code_review.adapters.bandit import BanditAdapter

    with patch(
        "code_review.adapters.bandit.run_subprocess",
        return_value=_result(_BANDIT_JSON),
    ):
        output = await BanditAdapter().run(_py_request())
    assert output.status == "ok", output.error
    assert output.sarif["runs"][0]["results"][0]["ruleId"] == "bandit.B602"


async def test_bandit_reports_error_on_garbage_stdout() -> None:
    # No JSON object at all → a clear error, never a silent empty success.
    from code_review.adapters.bandit import BanditAdapter

    with patch(
        "code_review.adapters.bandit.run_subprocess",
        return_value=_result(b"Working... totally not json"),
    ):
        output = await BanditAdapter().run(_py_request())
    assert output.status == "error"
    assert "no JSON object" in (output.error or "")


def test_bandit_protocol_conformance() -> None:
    from code_review.adapters.bandit import BanditAdapter
    from code_review.contracts import Analyzer

    assert isinstance(BanditAdapter(), Analyzer)
    assert BanditAdapter.name == "bandit"


async def test_bandit_empty_target_paths_returns_empty_sarif() -> None:
    from code_review.adapters.bandit import BanditAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(), languages=frozenset(), config={})
    output = await BanditAdapter().run(request)
    assert output.status == "ok"
    assert output.sarif.get("runs") == []


async def test_bandit_finds_subprocess_issue() -> None:
    from code_review.adapters.bandit import BanditAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(FIXTURE),),
                            languages=frozenset({"python"}), config={})
    output = await BanditAdapter().run(request)
    assert output.status == "ok"
    results = output.sarif["runs"][0]["results"]
    rule_ids = [r["ruleId"] for r in results]
    assert any("B404" in rid or "B603" in rid or "B602" in rid for rid in rule_ids), \
        f"Expected subprocess-related finding; got: {rule_ids}"


async def test_bandit_sarif_schema_valid() -> None:
    from code_review.adapters.bandit import BanditAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(FIXTURE),),
                            languages=frozenset({"python"}), config={})
    output = await BanditAdapter().run(request)
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)
