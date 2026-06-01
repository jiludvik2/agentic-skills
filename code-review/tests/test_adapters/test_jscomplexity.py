"""s4-t1 — jscomplexity invoke-and-capture contract (ADR-0020 / ADR-0022).

JS/TS complexity = radon `cc` parity for JavaScript and TypeScript, achieved by reusing the
vendored ESLint `complexity` core rule (threshold 0 ⇒ every function reported) via an
adapter-supplied flat config — zero new tool. TypeScript reaches parity through a second
flat-config block pointing the vendored `@typescript-eslint/parser` at `.ts/.tsx/.mts/.cts`
(ADR-0022 TS follow-up, story-jscomplexity-ts); the rule is syntactic, so no tsconfig.

Pins the load-bearing invocation (`--no-config-lookup`, the adapter-supplied `--config`,
the SARIF formatter, NODE_PATH, `ok_exit_codes=(0,1)`, anchored cwd), the raw passthrough,
and the ADR-0019 availability pre-flights (missing binary / no targets / no JS files).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from code_review.adapters.jscomplexity import JsComplexityAdapter
from code_review.capture import CaptureOutput
from code_review.contracts import Analyzer, ReviewRequest

JS_FIXTURE = Path(__file__).parent.parent / "fixtures" / "js-complexity"


def _req(paths: tuple[str, ...]) -> ReviewRequest:
    return ReviewRequest(scope="per-task", diff_range=None, target_paths=paths,
                         languages=frozenset(), config={})


def test_jscomplexity_protocol_conformance() -> None:
    assert isinstance(JsComplexityAdapter(), Analyzer)
    assert JsComplexityAdapter.name == "jscomplexity"
    assert JsComplexityAdapter.node_tool == "eslint"


async def test_jscomplexity_invocation_pins_flags(tmp_path: Path) -> None:
    """Pins the self-supplied complexity `--config` (present + threshold-0 rule),
    `--no-config-lookup`, the SARIF formatter, NODE_PATH, and `ok_exit_codes`."""
    captured: dict[str, Any] = {}

    async def fake(*args: str, **kwargs: object) -> CaptureOutput:
        captured["args"] = args
        captured["kwargs"] = kwargs
        idx = args.index("--config")
        config_path = Path(args[idx + 1])
        captured["config_exists"] = config_path.is_file()
        captured["config_text"] = config_path.read_text() if config_path.is_file() else ""
        return CaptureOutput(tool="jscomplexity", stdout='{"runs": [{"results": []}]}', exit_code=0)

    (tmp_path / "a.js").write_text("function f(){return 1;}\n", encoding="utf-8")
    with (
        patch("code_review.adapters.jscomplexity.node_binary", return_value=Path("/fake/eslint")),
        patch("code_review.adapters.jscomplexity.run_and_capture", new=fake),
    ):
        await JsComplexityAdapter().run(_req((str(tmp_path),)))

    args = captured["args"]
    assert args[0] == "jscomplexity"
    assert "node" in args
    assert "--no-config-lookup" in args, "host project's own eslint config must NOT be merged"
    assert args[args.index("--format") + 1] == "@microsoft/eslint-formatter-sarif"
    assert captured["config_exists"], "the complexity --config file must exist at invocation"
    assert "complexity" in captured["config_text"], "config must enable the complexity rule"
    assert "0" in captured["config_text"], "complexity threshold must be 0 (report every function)"
    kwargs = captured["kwargs"]
    assert kwargs["ok_exit_codes"] == (0, 1)
    assert "NODE_PATH" in kwargs["env"], "vendored NODE_PATH must be exported for the formatter"


async def test_jscomplexity_captures_raw_stdout(tmp_path: Path) -> None:
    (tmp_path / "a.js").write_text("function f(){return 1;}\n", encoding="utf-8")
    cap = CaptureOutput(tool="jscomplexity", stdout='{"runs": [{"results": []}]}', exit_code=0)
    with (
        patch("code_review.adapters.jscomplexity.node_binary", return_value=Path("/fake/eslint")),
        patch("code_review.adapters.jscomplexity.run_and_capture", new=AsyncMock(return_value=cap)),
    ):
        out = await JsComplexityAdapter().run(_req((str(tmp_path),)))
    assert out is cap


async def test_jscomplexity_unavailable_when_binary_absent(tmp_path: Path) -> None:
    (tmp_path / "a.js").write_text("function f(){return 1;}\n", encoding="utf-8")
    mock = AsyncMock(return_value=CaptureOutput(tool="jscomplexity"))
    with (
        patch("code_review.adapters.jscomplexity.node_binary", return_value=None),
        patch("code_review.adapters.jscomplexity.run_and_capture", new=mock),
    ):
        out = await JsComplexityAdapter().run(_req((str(tmp_path),)))
    assert out.status == "unavailable"
    assert "setup.sh" in (out.error or "")
    assert mock.await_count == 0


async def test_jscomplexity_unavailable_on_empty_targets() -> None:
    mock = AsyncMock(return_value=CaptureOutput(tool="jscomplexity"))
    with (
        patch("code_review.adapters.jscomplexity.node_binary", return_value=Path("/fake/eslint")),
        patch("code_review.adapters.jscomplexity.run_and_capture", new=mock),
    ):
        out = await JsComplexityAdapter().run(_req(()))
    assert out.status == "unavailable"
    assert mock.await_count == 0


async def test_jscomplexity_unavailable_when_no_js_files(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("no code here\n", encoding="utf-8")
    mock = AsyncMock(return_value=CaptureOutput(tool="jscomplexity"))
    with (
        patch("code_review.adapters.jscomplexity.node_binary", return_value=Path("/fake/eslint")),
        patch("code_review.adapters.jscomplexity.run_and_capture", new=mock),
    ):
        out = await JsComplexityAdapter().run(_req((str(tmp_path),)))
    assert out.status == "unavailable"
    assert mock.await_count == 0


@pytest.mark.integration
async def test_jscomplexity_reports_per_function_complexity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """End-to-end against the real vendored ESLint: the branchy.js fixture yields a
    `complexity`-rule SARIF result naming the function and its computed value (s4 / G8)."""
    if shutil.which("node") is None:
        pytest.skip("node not on PATH")
    from code_review.adapters.js_base import node_binary

    if node_binary("eslint") is None:
        pytest.skip("vendored eslint not provisioned (run scripts/setup.sh)")

    out = await JsComplexityAdapter().run(_req((str(JS_FIXTURE),)))
    assert out.status == "ok", f"expected ok, got {out.status}: {out.error}"
    payload = json.loads(out.stdout)
    results = payload.get("runs", [{}])[0].get("results", [])
    rule_ids = [r.get("ruleId", "") for r in results]
    assert any("complexity" in rid for rid in rule_ids), (
        f"complexity rule not fired; got {rule_ids}"
    )
    uris = {
        r.get("locations", [{}])[0]
        .get("physicalLocation", {})
        .get("artifactLocation", {})
        .get("uri", "")
        for r in results
    }
    assert any(u.endswith("branchy.js") for u in uris), f"no branchy.js finding; got {uris}"
    messages = " ".join(r.get("message", {}).get("text", "") for r in results)
    assert "complexity" in messages.lower(), f"expected a complexity message; got {messages!r}"


@pytest.mark.integration
async def test_jscomplexity_reports_typescript_complexity() -> None:
    """jscomplexity-ts-t1 (ADR-0022 follow-up): end-to-end against the real vendored
    ESLint + @typescript-eslint/parser — the branchy.ts fixture (type-annotated, so
    espree alone cannot parse it) yields a `complexity`-rule SARIF result naming the
    function. Proves TS reaches complexity parity with JS via the parser-only config."""
    if shutil.which("node") is None:
        pytest.skip("node not on PATH")
    from code_review.adapters.js_base import node_binary

    if node_binary("eslint") is None:
        pytest.skip("vendored eslint not provisioned (run scripts/setup.sh)")

    ts_target = JS_FIXTURE / "branchy.ts"
    out = await JsComplexityAdapter().run(_req((str(ts_target),)))
    assert out.status == "ok", f"expected ok, got {out.status}: {out.error}"
    payload = json.loads(out.stdout)
    results = payload.get("runs", [{}])[0].get("results", [])
    rule_ids = [r.get("ruleId", "") for r in results]
    assert any("complexity" in rid for rid in rule_ids), (
        f"complexity rule not fired on .ts (parser not wired?); got {rule_ids}"
    )
    uris = {
        r.get("locations", [{}])[0]
        .get("physicalLocation", {})
        .get("artifactLocation", {})
        .get("uri", "")
        for r in results
    }
    assert any(u.endswith("branchy.ts") for u in uris), f"no branchy.ts finding; got {uris}"
    messages = " ".join(r.get("message", {}).get("text", "") for r in results)
    assert "complexity" in messages.lower(), f"expected a complexity message; got {messages!r}"


# The TS config block globs four extensions; each is a distinct ESLint language case
# (.tsx adds JSX, .mts/.cts toggle the module system). Validate the whole advertised
# surface so it cannot silently regress to ".ts only" — the committed branchy.ts fixture
# covers the .ts case above; these tmp-dir variants cover the other three without bloating
# the fixtures dir. (.cts reuses the .mts body — both are plain typed functions; only the
# module-resolution mode differs, which the syntactic complexity rule is agnostic to.)
_TSX_SOURCE = """\
interface P { a: boolean; b: boolean; }
function branchy(p: P): JSX.Element {
  if (p.a) return <div>1</div>;
  else if (p.b) return <div>2</div>;
  else if (p.a && p.b) return <div>3</div>;
  return <span>{p.a || p.b ? 4 : 5}</span>;
}
export { branchy };
"""
_MTS_SOURCE = """\
interface P { a: boolean; b: boolean; }
export function branchy(p: P): number {
  if (p.a) return 1;
  else if (p.b) return 2;
  else if (p.a && p.b) return 3;
  return p.a || p.b ? 4 : 5;
}
"""


@pytest.mark.integration
@pytest.mark.parametrize(
    ("filename", "source"),
    [("branchy.tsx", _TSX_SOURCE), ("branchy.mts", _MTS_SOURCE), ("branchy.cts", _MTS_SOURCE)],
)
async def test_jscomplexity_covers_all_typescript_extensions(
    tmp_path: Path, filename: str, source: str
) -> None:
    """jscomplexity-ts story review: the config advertises `.ts/.tsx/.mts/.cts`, so the
    tested surface must equal the advertised surface — `.tsx` (JSX) and `.mts/.cts` (module
    variants) each parse via @typescript-eslint/parser and fire the complexity rule."""
    if shutil.which("node") is None:
        pytest.skip("node not on PATH")
    from code_review.adapters.js_base import node_binary

    if node_binary("eslint") is None:
        pytest.skip("vendored eslint not provisioned (run scripts/setup.sh)")

    (tmp_path / filename).write_text(source, encoding="utf-8")
    out = await JsComplexityAdapter().run(_req((str(tmp_path / filename),)))
    assert out.status == "ok", f"expected ok, got {out.status}: {out.error}"
    results = json.loads(out.stdout).get("runs", [{}])[0].get("results", [])
    rule_ids = [r.get("ruleId", "") for r in results]
    assert any("complexity" in rid for rid in rule_ids), (
        f"complexity rule not fired on {filename} (parser not applied to this ext?); "
        f"got {rule_ids}"
    )
