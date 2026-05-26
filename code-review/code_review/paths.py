from __future__ import annotations

from pathlib import Path


class SkillPaths:
    def __init__(self, skill_root: Path) -> None:
        self.skill_root = skill_root

    @property
    def runs_dir(self) -> Path:
        return self.skill_root / "runs"

    @property
    def cache_dir(self) -> Path:
        return self.skill_root / "cache"
