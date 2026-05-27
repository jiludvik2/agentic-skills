import json
from pathlib import Path

import jsonschema

SARIF_SCHEMA = Path(__file__).parent.parent.parent / "code_review" / "schemas" / "sarif-2.1.0.json"
PACKAGE = Path(__file__).parent.parent.parent / "code_review"


def test_pydeps_protocol_conformance():
    from code_review.adapters.pydeps import PydepsAdapter
    from code_review.contracts import Analyzer

    assert isinstance(PydepsAdapter(), Analyzer)
    assert PydepsAdapter.name == "pydeps"


async def test_pydeps_empty_target_paths_returns_empty():
    from code_review.adapters.pydeps import PydepsAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(), languages=frozenset(), config={})
    output = await PydepsAdapter().run(request)
    assert output.status == "ok"
    assert output.metrics is not None
    assert output.metrics.coupling == {}


async def test_pydeps_produces_coupling_metrics():
    from code_review.adapters.pydeps import PydepsAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(PACKAGE),),
                            languages=frozenset({"python"}), config={})
    output = await PydepsAdapter().run(request)
    assert output.status == "ok"
    assert output.metrics is not None
    assert len(output.metrics.coupling) > 0
    for entry in output.metrics.coupling.values():
        assert "fan_out" in entry
        assert "fan_in" in entry


async def test_pydeps_sarif_schema_valid():
    from code_review.adapters.pydeps import PydepsAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(PACKAGE),),
                            languages=frozenset({"python"}), config={})
    output = await PydepsAdapter().run(request)
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)
