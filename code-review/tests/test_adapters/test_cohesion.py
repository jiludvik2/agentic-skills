import json
from pathlib import Path

import jsonschema

FIXTURE = Path(__file__).parent.parent / "fixtures" / "python-with-known-issues"
SARIF_SCHEMA = Path(__file__).parent.parent.parent / "code_review" / "schemas" / "sarif-2.1.0.json"


def test_cohesion_protocol_conformance():
    from code_review.adapters.cohesion_ import CohesionAdapter
    from code_review.contracts import Analyzer

    assert isinstance(CohesionAdapter(), Analyzer)
    assert CohesionAdapter.name == "cohesion"


async def test_cohesion_empty_target_paths():
    from code_review.adapters.cohesion_ import CohesionAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(), languages=frozenset(), config={})
    output = await CohesionAdapter().run(request)
    assert output.status == "ok"
    assert output.metrics is not None
    assert output.metrics.per_class == {}


async def test_cohesion_detects_low_cohesion_class():
    from code_review.adapters.cohesion_ import CohesionAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(FIXTURE / "cohesive.py"),),
                            languages=frozenset({"python"}), config={})
    output = await CohesionAdapter().run(request)
    assert output.status == "ok"
    results = output.sarif["runs"][0]["results"]
    assert any(r["ruleId"] == "cohesion.low-cohesion" for r in results), \
        f"Expected low-cohesion finding; got: {[r['ruleId'] for r in results]}"


async def test_cohesion_populates_per_class_metrics():
    from code_review.adapters.cohesion_ import CohesionAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(FIXTURE / "cohesive.py"),),
                            languages=frozenset({"python"}), config={})
    output = await CohesionAdapter().run(request)
    assert output.metrics is not None
    assert len(output.metrics.per_class) > 0
    for entry in output.metrics.per_class.values():
        assert "cohesion" in entry
        assert "lineno" in entry


async def test_cohesion_sarif_schema_valid():
    from code_review.adapters.cohesion_ import CohesionAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(FIXTURE),),
                            languages=frozenset({"python"}), config={})
    output = await CohesionAdapter().run(request)
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)
