"""s1-t2 — eslint invoke-and-capture contract (ADR-0020).

Pins the load-bearing invocation (NODE_PATH pointed at the vendored node_modules so the
SARIF formatter resolves; cwd anchored at the targets' common-ancestor for eslint v9
flat-config discovery — F8), the raw stdout passthrough (the formatter's SARIF is captured
verbatim, no parse), and the availability pre-flights (missing binary / no JS / no flat
config → unavailable per ADR-0019, no longer error).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from code_review.adapters.eslint import EslintAdapter
from code_review.adapters.js_base import node_binary
from code_review.capture import CaptureOutput
from code_review.contracts import Analyzer, ReviewRequest
from code_review.paths import node_modules_dir

FIXTURE = Path(__file__).parent.parent / "fixtures" / "js-with-known-issues"
ESLINT_FIXTURE = Path(__file__).parent.parent / "fixtures" / "js-eslint"
SKILL_ROOT = Path(__file__).parent.parent.parent / ".claude" / "skills" / "code-review"

_FORMATTER = "@microsoft/eslint-formatter-sarif"


def _req(paths: tuple[str, ...]) -> ReviewRequest:
    return ReviewRequest(scope="per-task", diff_range=None, target_paths=paths,
                         languages=frozenset(), config={})


def test_eslint_protocol_conformance() -> None:
    assert isinstance(EslintAdapter(), Analyzer)
    assert EslintAdapter.name == "eslint"
    assert EslintAdapter.node_tool == "eslint"


async def test_eslint_invocation_pins_node_path_and_cwd_anchor(tmp_path: Path) -> None:
    (tmp_path / "eslint.config.js").write_text("export default [];\n")
    (tmp_path / "app.js").write_text("const x = 1;\n")
    mock = AsyncMock(return_value=CaptureOutput(tool="eslint", stdout="{}", exit_code=0))
    with (
        patch("code_review.adapters.eslint.node_binary", return_value=Path("/fake/eslint")),
        patch("code_review.adapters.eslint.run_and_capture", new=mock),
    ):
        await EslintAdapter().run(_req((str(tmp_path),)))
    args = mock.call_args.args
    kwargs = mock.call_args.kwargs
    assert args[0] == "eslint"
    assert "node" in args
    assert args[args.index("--format") + 1] == _FORMATTER  # SARIF formatter kept
    # NODE_PATH points at the vendored node_modules so the formatter resolves from any cwd.
    env = kwargs["env"]
    assert isinstance(env, dict) and str(node_modules_dir()) in env["NODE_PATH"]
    # cwd is anchored at the target dir for eslint v9 flat-config discovery (F8).
    cwd = kwargs["cwd"]
    assert isinstance(cwd, str) and Path(cwd).is_dir()
    assert Path(cwd) == tmp_path
    # eslint exits 0 (clean) or 1 (findings) — both tolerated.
    assert kwargs.get("ok_exit_codes") == (0, 1)


async def test_eslint_captures_raw_stdout(tmp_path: Path) -> None:
    """The formatter's SARIF lands verbatim on the capture — no JSON parse/normalise."""
    (tmp_path / "eslint.config.js").write_text("export default [];\n")
    (tmp_path / "app.js").write_text("const x = 1;\n")
    cap = CaptureOutput(tool="eslint", stdout='{"runs": []}', exit_code=0)
    with (
        patch("code_review.adapters.eslint.node_binary", return_value=Path("/fake/eslint")),
        patch("code_review.adapters.eslint.run_and_capture", new=AsyncMock(return_value=cap)),
    ):
        out = await EslintAdapter().run(_req((str(tmp_path),)))
    assert out is cap


async def test_eslint_unavailable_when_vendored_binary_absent(tmp_path: Path) -> None:
    with patch("code_review.adapters.eslint.node_binary", return_value=None):
        out = await EslintAdapter().run(_req((str(tmp_path),)))
    assert out.status == "unavailable"
    assert "setup.sh" in (out.error or "")


async def test_eslint_empty_target_paths_unavailable() -> None:
    with patch("code_review.adapters.eslint.node_binary", return_value=Path("/fake/eslint")):
        out = await EslintAdapter().run(_req(()))
    assert out.status == "unavailable"


async def test_eslint_anchors_cwd_at_existing_directory_for_missing_file() -> None:
    """A single target that is not an existing directory (a single file, or a file
    deleted by a diff) must still anchor eslint's cwd at an existing dir (the parent)."""
    mock = AsyncMock(return_value=CaptureOutput(tool="eslint", stdout="{}", exit_code=0))
    missing = str(ESLINT_FIXTURE / "no_such_file.js")
    with (
        patch("code_review.adapters.eslint.node_binary", return_value=Path("/fake/eslint")),
        patch("code_review.adapters.eslint.run_and_capture", new=mock),
    ):
        await EslintAdapter().run(_req((missing,)))
    cwd = mock.call_args.kwargs["cwd"]
    assert isinstance(cwd, str) and Path(cwd).is_dir(), f"cwd must be an existing dir, got {cwd!r}"


async def test_eslint_no_flat_config_is_unavailable(tmp_path: Path) -> None:
    """A JS target with no eslint.config.* (and no .eslintrc) anywhere upward is
    'nothing to run here', not a failure: unavailable, and eslint is never invoked."""
    (tmp_path / "app.js").write_text("const x = 1;\n")
    mock = AsyncMock(return_value=CaptureOutput(tool="eslint"))
    with (
        patch("code_review.adapters.eslint.node_binary", return_value=Path("/fake/eslint")),
        patch("code_review.adapters.eslint.run_and_capture", new=mock),
    ):
        out = await EslintAdapter().run(_req((str(tmp_path),)))
    assert out.status == "unavailable", out.error
    assert "config" in (out.error or "").lower()
    assert not mock.called, "eslint must not be invoked when there is no config to run"


async def test_eslint_legacy_only_config_is_unavailable(tmp_path: Path) -> None:
    """s1-t0: a JS target whose only discoverable config is a legacy .eslintrc* maps to
    `unavailable`, not `error` — the vendored ESLint v9 is flat-config-only and would
    exit 2, and exit 2 is otherwise surfaced as `error`. eslint is never invoked.
    RED before s1-t0: legacy presence passed the availability gate, eslint ran, and v9's
    exit 2 was reported as a spurious red on real repos (express)."""
    (tmp_path / "app.js").write_text("const x = 1;\n")
    (tmp_path / ".eslintrc.json").write_text('{"rules": {}}\n')
    mock = AsyncMock(return_value=CaptureOutput(tool="eslint", stdout="{}", exit_code=0))
    with (
        patch("code_review.adapters.eslint.node_binary", return_value=Path("/fake/eslint")),
        patch("code_review.adapters.eslint.run_and_capture", new=mock),
    ):
        out = await EslintAdapter().run(_req((str(tmp_path),)))
    assert out.status == "unavailable", out.error
    reason = (out.error or "").lower()
    assert "flat" in reason and "legacy" in reason, out.error
    assert not mock.called, "eslint must not run on a legacy-only target (v9 can't consume it)"


async def test_eslint_flat_config_beats_nearer_legacy(tmp_path: Path) -> None:
    """A flat config discoverable further upward still wins when a nearer dir carries
    only a legacy .eslintrc — v9 ignores .eslintrc entirely and keeps searching upward
    for a flat config, so the target remains lintable (eslint must be invoked)."""
    (tmp_path / "eslint.config.js").write_text("export default [];\n")
    sub = tmp_path / "pkg"
    sub.mkdir()
    (sub / ".eslintrc.json").write_text('{"rules": {}}\n')
    (sub / "app.js").write_text("const x = 1;\n")
    mock = AsyncMock(return_value=CaptureOutput(tool="eslint", stdout="{}", exit_code=0))
    with (
        patch("code_review.adapters.eslint.node_binary", return_value=Path("/fake/eslint")),
        patch("code_review.adapters.eslint.run_and_capture", new=mock),
    ):
        out = await EslintAdapter().run(_req((str(sub),)))
    assert mock.called, "a flat config upward must still be discovered past a nearer legacy config"
    assert out.status == "ok", out.error


def test_discover_eslint_config_distinguishes_flat_legacy_none(tmp_path: Path) -> None:
    """s1-t0 unit: the config-detection helper distinguishes flat-present from
    legacy-only from none. Only "flat" is lintable for the vendored v9."""
    from code_review.adapters.eslint import _discover_eslint_config

    none_dir = tmp_path / "none"
    none_dir.mkdir()
    assert _discover_eslint_config(str(none_dir)) == "none"

    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    (legacy_dir / ".eslintrc.json").write_text("{}\n")
    assert _discover_eslint_config(str(legacy_dir)) == "legacy"

    flat_dir = tmp_path / "flat"
    flat_dir.mkdir()
    (flat_dir / "eslint.config.js").write_text("export default [];\n")
    assert _discover_eslint_config(str(flat_dir)) == "flat"


async def test_eslint_unavailable_without_js(tmp_path: Path) -> None:
    """A target tree with no JS/TS at all is 'nothing to run' — unavailable, never invoked."""
    (tmp_path / "app.py").write_text("x = 1\n")
    mock = AsyncMock(return_value=CaptureOutput(tool="eslint"))
    with (
        patch("code_review.adapters.eslint.node_binary", return_value=Path("/fake/eslint")),
        patch("code_review.adapters.eslint.run_and_capture", new=mock),
    ):
        out = await EslintAdapter().run(_req((str(tmp_path),)))
    assert out.status == "unavailable", out.error
    assert "javascript" in (out.error or "").lower()
    assert not mock.called, "eslint must not be invoked when there is no JS to analyse"


async def test_eslint_with_flat_config_invokes(tmp_path: Path) -> None:
    """Regression: a target that DOES carry a flat config still reaches the invocation —
    the no-config / no-JS skips must not short-circuit the normal path."""
    (tmp_path / "eslint.config.js").write_text("export default [];\n")
    (tmp_path / "app.js").write_text("const x = 1;\n")
    mock = AsyncMock(return_value=CaptureOutput(tool="eslint", stdout="{}", exit_code=1))
    with (
        patch("code_review.adapters.eslint.node_binary", return_value=Path("/fake/eslint")),
        patch("code_review.adapters.eslint.run_and_capture", new=mock),
    ):
        out = await EslintAdapter().run(_req((str(tmp_path),)))
    assert mock.called, "eslint must be invoked when a flat config is present"
    assert out.status == "ok", out.error


@pytest.mark.integration
@pytest.mark.skipif(
    node_binary("eslint") is None,
    reason="eslint not in node_modules (run scripts/setup.sh)",
)
async def test_eslint_integration_single_file_target() -> None:
    """A single existing file target from a foreign cwd: the adapter anchors eslint's cwd
    at the file's directory so the project's flat config is discovered and the file falls
    within the base path. Raw SARIF lands on stdout."""
    out = await EslintAdapter().run(_req((str(ESLINT_FIXTURE / "lint_me.js"),)))
    assert out.status == "ok", out.error
    sarif = json.loads(out.stdout)
    assert len(sarif["runs"][0]["results"]) >= 1, "expected eslint to flag the planted violations"


@pytest.mark.integration
@pytest.mark.skipif(
    node_binary("eslint") is None,
    reason="eslint not in node_modules (run scripts/setup.sh)",
)
async def test_eslint_formatter_resolves_from_foreign_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run from a cwd with no node_modules and confirm the SARIF formatter still resolves
    via the adapter's NODE_PATH — no module-not-found / 'Cannot find formatter'."""
    monkeypatch.setenv("POLYREVIEW_CACHE_DIR", str(SKILL_ROOT))
    (tmp_path / "eslint.config.mjs").write_text(
        "export default [{ rules: { 'no-unused-vars': 'error' } }];\n"
    )
    (tmp_path / "lint_me.js").write_text("const unused = 1;\nexport const used = 2;\n")
    monkeypatch.chdir(tmp_path)
    out = await EslintAdapter().run(_req(("lint_me.js",)))
    err = (out.error or "").lower()
    assert "cannot find" not in err and "formatter" not in err, out.error
    assert out.status == "ok", out.error


@pytest.mark.integration
@pytest.mark.skipif(
    node_binary("eslint") is None,
    reason="eslint not in node_modules (run scripts/setup.sh)",
)
async def test_eslint_integration_detects_console_log() -> None:
    """Pointed at a JS project dir that ships its own flat config, the adapter discovers
    that config (cwd anchored at the target root) and reports the planted violations."""
    request = ReviewRequest(
        scope="per-task", diff_range=None, target_paths=(str(ESLINT_FIXTURE),),
        languages=frozenset({"javascript", "typescript"}), config={},
    )
    out = await EslintAdapter().run(request)
    assert out.status == "ok", out.error
    sarif = json.loads(out.stdout)
    results = sarif["runs"][0]["results"]
    assert len(results) >= 1, "expected eslint to flag the planted violations"
    rule_ids = {r.get("ruleId") for r in results}
    assert rule_ids & {"no-console", "no-unused-vars"}, rule_ids
