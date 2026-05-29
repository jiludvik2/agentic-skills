import json
from pathlib import Path

import jsonschema

FIXTURE = Path(__file__).parent.parent / "fixtures" / "python-with-known-issues"
SARIF_SCHEMA = Path(__file__).parent.parent.parent / "code_review" / "schemas" / "sarif-2.1.0.json"


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
