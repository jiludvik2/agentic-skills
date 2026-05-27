import json
from pathlib import Path

import jsonschema

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "python-with-known-issues"
SCHEMA_PATH = Path(__file__).parent.parent.parent / "code_review" / "schemas" / "sarif-2.1.0.json"
HIGH_CC_FILE = str(FIXTURE_PATH / "complex.py")


def _make_request():
    from code_review.contracts import ReviewRequest

    return ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=(str(FIXTURE_PATH),),
        languages=frozenset({"python"}),
        config={},
    )


def test_radon_protocol_conformance():
    from code_review.adapters.radon import RadonAdapter
    from code_review.contracts import Analyzer

    assert isinstance(RadonAdapter(), Analyzer)
    assert RadonAdapter.name == "radon"


async def test_radon_produces_metric_set():
    from code_review.adapters.radon import RadonAdapter

    output = await RadonAdapter().run(_make_request())

    assert output.metrics is not None
    assert len(output.metrics.per_file) > 0


async def test_radon_high_cc_function_detected():
    from code_review.adapters.radon import RadonAdapter

    output = await RadonAdapter().run(_make_request())

    assert output.metrics is not None
    matching = {p: v for p, v in output.metrics.per_file.items() if "complex.py" in p}
    assert matching, f"complex.py not in per_file keys: {list(output.metrics.per_file)}"
    entry = next(iter(matching.values()))
    max_cc = max(f["cc"] for f in entry["functions"])
    assert max_cc >= 10, f"Expected CC ≥ 10, got {max_cc}"


async def test_radon_empty_target_paths_returns_empty_metricset() -> None:
    from code_review.adapters.radon import RadonAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=(),
        languages=frozenset(),
        config={},
    )
    output = await RadonAdapter().run(request)

    assert output.status == "ok"
    assert output.sarif.get("runs") == []
    assert output.metrics is not None
    assert output.metrics.per_file == {}
    assert output.metrics.per_class == {}
    assert output.metrics.coupling == {}


async def test_radon_sarif_is_valid():
    from code_review.adapters.radon import RadonAdapter

    output = await RadonAdapter().run(_make_request())

    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.validate(output.sarif, schema)
    assert "runs" in output.sarif
    results = output.sarif["runs"][0].get("results")
    assert results is not None
