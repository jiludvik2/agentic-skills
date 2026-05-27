import json
from pathlib import Path

import jsonschema

FIXTURE = Path(__file__).parent.parent / "fixtures" / "python-with-known-issues"
SARIF_SCHEMA = Path(__file__).parent.parent.parent / "code_review" / "schemas" / "sarif-2.1.0.json"


def test_vulture_protocol_conformance():
    from code_review.adapters.vulture import VultureAdapter
    from code_review.contracts import Analyzer

    assert isinstance(VultureAdapter(), Analyzer)
    assert VultureAdapter.name == "vulture"


async def test_vulture_empty_target_paths():
    from code_review.adapters.vulture import VultureAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(), languages=frozenset(), config={})
    output = await VultureAdapter().run(request)
    assert output.status == "ok"
    assert output.sarif.get("runs") == []


async def test_vulture_detects_unused_function():
    from code_review.adapters.vulture import VultureAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(FIXTURE / "dead.py"),),
                            languages=frozenset({"python"}), config={})
    output = await VultureAdapter().run(request)
    assert output.status == "ok"
    results = output.sarif["runs"][0]["results"]
    rule_ids = [r["ruleId"] for r in results]
    assert any("vulture.unused-" in rid for rid in rule_ids), \
        f"Expected unused-* finding; got: {rule_ids}"


async def test_vulture_sarif_schema_valid():
    from code_review.adapters.vulture import VultureAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(FIXTURE),),
                            languages=frozenset({"python"}), config={})
    output = await VultureAdapter().run(request)
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)
