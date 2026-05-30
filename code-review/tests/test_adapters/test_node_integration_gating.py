"""Meta-test for s1-t3 / F9: the Node-analyzer integration tests must actually
RUN in CI (on a vendored toolchain), not be silently skipif-skipped — otherwise
F1/F2/F8 regressions stay invisible. The three still-broken adapters are
xfail(strict) referencing their fixing story so CI stays green while the tests
genuinely run; an unexpected pass fails, forcing each fix-story to flip its xfail.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from code_review.adapters.js_base import node_binary

ADAPTERS_DIR = Path(__file__).parent

# (test module file, test function, node_tool, must be xfail(strict))
_NODE_INTEGRATION = [
    ("test_jscpd.py", "test_jscpd_integration", "jscpd", False),  # F2/s2 fixed
    ("test_depcruiser.py", "test_depcruiser_integration", "depcruise", True),
    ("test_eslint.py", "test_eslint_integration_detects_console_log", "eslint", True),
    ("test_knip.py", "test_knip_integration", "knip", False),
]


def _load_module(filename: str) -> object:
    path = ADAPTERS_DIR / filename
    spec = importlib.util.spec_from_file_location(f"_meta_{filename[:-3]}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_node_integration_tests_run_when_vendored() -> None:
    for filename, fn_name, tool, must_xfail in _NODE_INTEGRATION:
        module = _load_module(filename)
        fn = getattr(module, fn_name)
        marks = list(getattr(fn, "pytestmark", []))
        names = {m.name for m in marks}

        # All four are integration-marked: the matrix job selects them with
        # `-m integration`; the main job (`-m "not integration"`) deselects them.
        assert "integration" in names, f"{fn_name}: missing @pytest.mark.integration"

        if must_xfail:
            xfails = [m for m in marks if m.name == "xfail"]
            assert len(xfails) == 1, (
                f"{fn_name}: expected exactly one xfail marker, got {len(xfails)}"
            )
            assert xfails[0].kwargs.get("strict") is True, f"{fn_name}: xfail must be strict=True"
            assert xfails[0].kwargs.get("reason"), f"{fn_name}: xfail must name its fixing story"

        # When the toolchain is vendored, the skip gate must be inactive so the
        # test actually runs (skipif condition is evaluated at import time). On a
        # toolchain-less machine this branch is a no-op by design — the CI guard
        # step is the fail-loud gate that enforces the toolchain is present.
        if node_binary(tool) is not None:
            skipifs = [m for m in marks if m.name == "skipif"]
            assert all(m.args[0] is False for m in skipifs), (
                f"{fn_name}: skipped despite a vendored toolchain — F9 would mask it"
            )
