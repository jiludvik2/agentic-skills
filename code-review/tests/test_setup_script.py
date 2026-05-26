from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SETUP = REPO_ROOT / "scripts" / "setup.sh"
PREFETCH = REPO_ROOT / "scripts" / "prefetch_caches.py"


def test_setup_script_exists_and_executable() -> None:
    assert SETUP.exists(), f"missing {SETUP}"
    assert os.access(SETUP, os.X_OK), "setup.sh is not executable"
    assert PREFETCH.exists(), f"missing {PREFETCH}"


def test_setup_script_passes_shellcheck_or_bash_n() -> None:
    r = subprocess.run(["bash", "-n", str(SETUP)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    if shutil.which("shellcheck"):
        sc = subprocess.run(["shellcheck", "-S", "error", str(SETUP)], capture_output=True, text=True)
        assert sc.returncode == 0, sc.stdout + sc.stderr


def test_prefetch_caches_idempotent(tmp_path: Path) -> None:
    r1 = subprocess.run([sys.executable, str(PREFETCH)], capture_output=True, text=True, cwd=tmp_path)
    assert r1.returncode == 0, r1.stderr
    cache = tmp_path / "cache"
    manifest = cache / "manifest.json"
    assert cache.exists(), "cache/ not created"
    assert manifest.exists(), "cache/manifest.json not created"
    mtime1 = manifest.stat().st_mtime_ns

    r2 = subprocess.run([sys.executable, str(PREFETCH)], capture_output=True, text=True, cwd=tmp_path)
    assert r2.returncode == 0, r2.stderr
    assert cache.exists()
    assert manifest.stat().st_mtime_ns == mtime1, "manifest rewritten on idempotent re-run"


def test_prefetch_recovers_from_corrupt_manifest(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "manifest.json").write_text("{ this is not valid json", encoding="utf-8")
    r = subprocess.run([sys.executable, str(PREFETCH)], capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    import json as _json

    _json.loads((cache / "manifest.json").read_text(encoding="utf-8"))  # now valid


def test_setup_script_has_no_host_root_traversal() -> None:
    text = SETUP.read_text(encoding="utf-8")
    assert "../../.." not in text, "fragile host-root traversal must not be present (deferred to s1-t4)"
    assert "2>/dev/null" not in text, "error-swallowing resolution must not be present"


def test_setup_script_fails_loud_on_bad_step(tmp_path: Path) -> None:
    # Inject a failing command in place of the first real step; the script must abort
    # non-zero and name the step in the error.
    broken = SETUP.read_text(encoding="utf-8").replace("uv sync --frozen", "false", 1)
    p = tmp_path / "setup_broken.sh"
    p.write_text(broken, encoding="utf-8")
    p.chmod(0o755)
    r = subprocess.run(["bash", str(p)], capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode != 0
    combined = r.stdout + r.stderr
    assert "uv sync" in combined, f"error did not name the failing step: {combined!r}"
    assert "ERROR" in combined or "fail" in combined.lower()
