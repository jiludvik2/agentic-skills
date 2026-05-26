import subprocess
import sys
from pathlib import Path


def test_skill_paths_dirs_inside_root(tmp_path: Path):
    from code_review.paths import SkillPaths

    paths = SkillPaths(skill_root=tmp_path)
    assert paths.runs_dir.is_relative_to(tmp_path)
    assert paths.cache_dir.is_relative_to(tmp_path)


def test_cwd_guard_accepts_symlink_inside_cwd(tmp_path: Path):
    real_output = tmp_path / "real_output.json"
    real_output.touch()
    symlink = tmp_path / "link_output.json"
    symlink.symlink_to(real_output)

    result = subprocess.run(
        [sys.executable, "-m", "code_review.cli", "--output", str(symlink)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    combined = result.stdout + result.stderr
    assert "sandbox" not in combined.lower() and "outside cwd" not in combined.lower()
