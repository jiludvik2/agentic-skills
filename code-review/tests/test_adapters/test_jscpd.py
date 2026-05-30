from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import jsonschema
import pytest

from code_review.adapters.js_base import node_binary

# A byte-identical clone pair: jscpd's token matcher needs identical tokens, so
# the js-with-known-issues "duplicate" (renamed identifiers) falls below the
# min-tokens threshold. This dedicated fixture is the real duplication signal.
FIXTURE = Path(__file__).parent.parent / "fixtures" / "js-duplication"
SARIF_SCHEMA = Path(__file__).parent.parent.parent / "code_review" / "schemas" / "sarif-2.1.0.json"


def test_jscpd_protocol_conformance() -> None:
    from code_review.adapters.jscpd import JscpdAdapter
    from code_review.contracts import Analyzer

    assert isinstance(JscpdAdapter(), Analyzer)
    assert JscpdAdapter.name == "jscpd"
    assert JscpdAdapter.node_tool == "jscpd"


async def test_jscpd_returns_error_when_binary_absent(tmp_path: Path) -> None:
    from code_review.adapters.jscpd import JscpdAdapter
    from code_review.contracts import ReviewRequest

    with patch("code_review.adapters.jscpd.node_binary", return_value=None):
        request = ReviewRequest(
            scope="per-task", diff_range=None,
            target_paths=(str(tmp_path),),
            languages=frozenset(), config={},
        )
        output = await JscpdAdapter().run(request)
    assert output.status == "error"
    assert "setup.sh" in (output.error or "")


async def test_jscpd_empty_target_paths() -> None:
    from code_review.adapters.jscpd import JscpdAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(
        scope="per-task", diff_range=None,
        target_paths=(), languages=frozenset(), config={},
    )
    with patch("code_review.adapters.jscpd.node_binary", return_value=Path("/fake/jscpd")):
        output = await JscpdAdapter().run(request)
    assert output.status == "ok"


def _report_writer(payload: str) -> object:
    """Return a run_subprocess side-effect that drops the jscpd JSON report
    into whatever directory the adapter passes as --output."""
    from code_review.adapters.base import SubprocessResult

    def fake_run(*args: object, **kwargs: object) -> SubprocessResult:
        arglist = list(args)
        output_dir = Path(str(arglist[arglist.index("--output") + 1]))
        (output_dir / "jscpd-report.json").write_text(payload)
        return SubprocessResult(b"", b"", 0)

    return fake_run


async def test_jscpd_parses_json_to_sarif() -> None:
    from code_review.adapters.jscpd import JscpdAdapter
    from code_review.contracts import ReviewRequest

    fake_json = json.dumps({
        "duplicates": [
            {
                "firstFile": {"name": "src/a.ts", "start": 10},
                "secondFile": {"name": "src/b.ts", "start": 20},
            }
        ],
        "statistics": {"total": {"duplicatedLines": 5}},
    })

    request = ReviewRequest(
        scope="per-task", diff_range=None,
        target_paths=("src/",), languages=frozenset(), config={},
    )
    with (
        patch("code_review.adapters.jscpd.node_binary", return_value=Path("/fake/jscpd")),
        patch("code_review.adapters.jscpd.has_js_files", return_value=True),
        patch(
            "code_review.adapters.jscpd.run_subprocess",
            new=AsyncMock(side_effect=_report_writer(fake_json)),
        ),
    ):
        output = await JscpdAdapter().run(request)

    assert output.status == "ok"
    assert output.sarif["runs"][0]["tool"]["driver"]["name"] == "jscpd"
    results = output.sarif["runs"][0]["results"]
    assert len(results) == 1
    assert results[0]["ruleId"] == "jscpd.duplicate-code"
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)


async def test_jscpd_writes_report_to_tempdir_and_parses_it() -> None:
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.jscpd import JscpdAdapter
    from code_review.contracts import ReviewRequest

    fake_json = json.dumps({
        "duplicates": [
            {
                "firstFile": {"name": "src/a.ts", "start": 10},
                "secondFile": {"name": "src/b.ts", "start": 20},
            }
        ],
        "statistics": {"total": {"duplicatedLines": 5}},
    })
    seen_output: dict[str, str] = {}

    def fake_run(*args: object, **kwargs: object) -> SubprocessResult:
        arglist = list(args)
        idx = arglist.index("--output")
        output_dir = Path(str(arglist[idx + 1]))
        # jscpd treats --output as a directory and writes jscpd-report.json into it.
        assert output_dir.is_dir(), "--output must be a real directory, not /dev/stdout"
        assert str(output_dir) != "/dev/stdout"
        seen_output["dir"] = str(output_dir)
        (output_dir / "jscpd-report.json").write_text(fake_json)
        return SubprocessResult(b"", b"", 0)

    request = ReviewRequest(
        scope="per-task", diff_range=None,
        target_paths=("src/",), languages=frozenset(), config={},
    )
    with (
        patch("code_review.adapters.jscpd.node_binary", return_value=Path("/fake/jscpd")),
        patch("code_review.adapters.jscpd.has_js_files", return_value=True),
        patch(
            "code_review.adapters.jscpd.run_subprocess",
            new=AsyncMock(side_effect=fake_run),
        ),
    ):
        output = await JscpdAdapter().run(request)

    assert output.status == "ok"
    results = output.sarif["runs"][0]["results"]
    assert len(results) == 1
    assert results[0]["ruleId"] == "jscpd.duplicate-code"
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)
    # Temp dir is cleaned up after the run.
    assert not Path(seen_output["dir"]).exists()


async def test_jscpd_handles_empty_duplicates() -> None:
    from code_review.adapters.jscpd import JscpdAdapter
    from code_review.contracts import ReviewRequest

    fake_json = json.dumps({"duplicates": [], "statistics": {}})

    request = ReviewRequest(
        scope="per-task", diff_range=None,
        target_paths=("src/",), languages=frozenset(), config={},
    )
    with (
        patch("code_review.adapters.jscpd.node_binary", return_value=Path("/fake/jscpd")),
        patch("code_review.adapters.jscpd.has_js_files", return_value=True),
        patch(
            "code_review.adapters.jscpd.run_subprocess",
            new=AsyncMock(side_effect=_report_writer(fake_json)),
        ),
    ):
        output = await JscpdAdapter().run(request)

    assert output.status == "ok"
    assert output.sarif["runs"][0]["results"] == []


async def test_jscpd_unavailable_without_js(tmp_path: Path) -> None:
    """jscpd is intentionally JS-scoped (lang_select._JS_ADAPTERS; capabilities
    languages=[javascript, typescript]) — duplication detection is a deliberately
    JS-only feature. On a no-JS target it must skip cleanly as `unavailable` rather
    than run the out-of-scope language duplication it is capable of (story-level fix,
    ADR-0019). Defense-in-depth for the all-analyzer / --target path that bypasses
    language selection."""
    from code_review.adapters.base import SubprocessResult
    from code_review.adapters.jscpd import JscpdAdapter
    from code_review.contracts import ReviewRequest

    (tmp_path / "app.py").write_text("x = 1\n")
    invoked = False

    async def fake_run(*args: object, **kwargs: object) -> SubprocessResult:
        nonlocal invoked
        invoked = True
        return SubprocessResult(b"", b"", 0)

    request = ReviewRequest(scope="per-task", diff_range=None,
                            target_paths=(str(tmp_path),), languages=frozenset(), config={})
    with (
        patch("code_review.adapters.jscpd.node_binary", return_value=Path("/fake/jscpd")),
        patch("code_review.adapters.jscpd.run_subprocess", new=AsyncMock(side_effect=fake_run)),
    ):
        output = await JscpdAdapter().run(request)
    assert output.status == "unavailable", output.error
    assert "javascript" in (output.error or "").lower()
    assert not invoked, "jscpd must not be invoked when there is no JS to analyse"


@pytest.mark.integration
@pytest.mark.skipif(
    node_binary("jscpd") is None,
    reason="jscpd not in node_modules (run scripts/setup.sh)",
)
async def test_jscpd_integration() -> None:
    from code_review.adapters.jscpd import JscpdAdapter
    from code_review.contracts import ReviewRequest

    request = ReviewRequest(
        scope="per-task",
        diff_range=None,
        target_paths=(str(FIXTURE),),
        languages=frozenset({"javascript", "typescript"}),
        config={},
    )
    output = await JscpdAdapter().run(request)
    assert output.status == "ok"
    # The fixture is a genuine clone pair (clone_a.ts / clone_b.ts); the AC
    # requires the duplication to actually be reported, not just a valid SARIF.
    assert len(output.sarif["runs"][0]["results"]) >= 1
    schema = json.loads(SARIF_SCHEMA.read_text())
    jsonschema.validate(output.sarif, schema)
