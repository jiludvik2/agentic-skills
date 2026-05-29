import shutil
from pathlib import Path
from unittest.mock import patch

_PATCH_TARGET = "code_review.adapters.js_base._node_modules"


def test_node_binary_returns_none_when_not_installed(tmp_path: Path) -> None:
    from code_review.adapters.js_base import node_binary

    with patch(_PATCH_TARGET, return_value=tmp_path / "node_modules"):
        result = node_binary("eslint")
    assert result is None


def test_node_binary_returns_path_when_present(tmp_path: Path) -> None:
    from code_review.adapters.js_base import node_binary

    bin_dir = tmp_path / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    fake = bin_dir / "eslint"
    fake.touch()
    with patch(_PATCH_TARGET, return_value=tmp_path / "node_modules"):
        result = node_binary("eslint")
    assert result == fake


def test_probe_js_adapter_unavailable_no_node_modules(tmp_path: Path) -> None:
    from code_review.adapters.js_base import probe_js_adapter

    with patch(_PATCH_TARGET, return_value=tmp_path / "node_modules"):
        probe = probe_js_adapter("eslint")
    assert probe["status"] == "unavailable"
    assert "setup.sh" in probe["error"]


def test_probe_js_adapter_available_when_binary_present(tmp_path: Path) -> None:
    from code_review.adapters.js_base import probe_js_adapter

    if shutil.which("node") is None:
        import pytest
        pytest.skip("node not on PATH")
    bin_dir = tmp_path / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "eslint").touch()
    with patch(_PATCH_TARGET, return_value=tmp_path / "node_modules"):
        probe = probe_js_adapter("eslint")
    assert probe["status"] == "available"


def test_probe_js_adapter_unavailable_no_node(tmp_path: Path) -> None:
    from code_review.adapters.js_base import probe_js_adapter

    with (
        patch(_PATCH_TARGET, return_value=tmp_path / "node_modules"),
        patch("code_review.adapters.js_base.shutil.which", return_value=None),
    ):
        probe = probe_js_adapter("eslint")
    assert probe["status"] == "unavailable"
    assert "node" in probe["error"]
