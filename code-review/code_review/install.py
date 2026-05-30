"""Agent-independent install/uninstall of the skill bundle (ADR-0018).

The bundle (``code_review.bundle.BUNDLE_MANIFEST``) is copied into the user-level
skills directory of whatever agent(s) the user runs, resolved from a target
**registry**. s6-t2 (`polyreview install`) and s7-t0 (`polyreview uninstall`) both
import this module so they share one registry, one env→home resolution, one
auto-detect predicate, and one bundle marker — no duplication.
"""

from __future__ import annotations

import importlib.resources
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from code_review.bundle import BUNDLE_DIRS, BUNDLE_FILES, BUNDLE_ROOT

# Directory name the bundle lands in; must match SKILL.md `name: code-review`.
SKILL_DIR_NAME = "code-review"

# Marker used by the install idempotency check and the uninstall safety guard
# (ADR-0018 §5): a readable SKILL.md with a frontmatter line declaring our name.
# Anchored to a full line (not a bare substring) so a near-collision like
# `name: code-reviewer` cannot pass the guard and become eligible for a --force
# rmtree (the guard gates a destructive op shared with s7's uninstall).
_MARKER_FILE = "SKILL.md"
_MARKER_RE = re.compile(r"^name:[ \t]*code-review[ \t]*$", re.MULTILINE)

# Registry target ids, in default-write order (neutral first).
TARGETS: tuple[str, ...] = ("agents", "claude", "copilot", "gemini")

# Per-agent home base dir (relative to $HOME) used by the auto-detect predicate.
# `agents` is the neutral default and has no "is present" concept — always written.
_HOME_BASE: dict[str, str] = {
    "agents": ".agents",
    "claude": ".claude",
    "copilot": ".copilot",
    "gemini": ".gemini",
}


def skills_dir(target: str) -> Path:
    """User-level skills directory for a registry target id (ADR-0018 §1).

    Resolved ``$HOME``-relative (and via ``CLAUDE_CONFIG_DIR`` for ``claude``) at
    call time, so tests stay hermetic by monkeypatching ``$HOME`` / the env var.
    """
    if target not in TARGETS:
        raise ValueError(f"unknown agent target: {target!r} (choose from {', '.join(TARGETS)})")
    if target == "claude":
        base = os.environ.get("CLAUDE_CONFIG_DIR")
        root = Path(base) if base else Path.home() / ".claude"
        return root / "skills"
    return Path.home() / _HOME_BASE[target] / "skills"


def home_present(target: str) -> bool:
    """A non-neutral agent home "is present" iff its base dir exists (ADR-0018 §1)."""
    if target == "agents":
        return True
    return (Path.home() / _HOME_BASE[target]).is_dir()


def default_targets() -> list[str]:
    """No-``--agent`` policy: neutral ``agents`` plus every agent home present."""
    return [t for t in TARGETS if t == "agents" or home_present(t)]


def resolve_targets(agent: list[str] | None, all_targets: bool) -> list[str]:
    """Map the install/uninstall flags to an ordered, de-duplicated target set."""
    if all_targets:
        return list(TARGETS)
    if agent:
        for a in agent:
            if a not in TARGETS:
                raise ValueError(
                    f"unknown agent target: {a!r} (choose from {', '.join(TARGETS)})"
                )
        return list(dict.fromkeys(agent))
    return default_targets()


def bundle_source_dir() -> Path:
    """Resolve the on-disk bundle root the copy reads from.

    Installed wheel: ``code_review/_bundle/`` (force-included, s6-t1). Source
    checkout (no ``_bundle/``): fall back to the repo's
    ``.claude/skills/code-review/`` so the SDLC dev cycle can install too.
    """
    pkg = Path(str(importlib.resources.files("code_review")))
    wheel_bundle = pkg / BUNDLE_ROOT
    if wheel_bundle.is_dir():
        return wheel_bundle
    dev_bundle = pkg.parent / ".claude" / "skills" / SKILL_DIR_NAME
    if dev_bundle.is_dir():
        return dev_bundle
    raise FileNotFoundError(
        "skill bundle not found: neither the wheel _bundle/ nor the dev "
        ".claude/skills/code-review/ is present"
    )


def is_our_bundle(dest: Path) -> bool:
    """True iff ``dest`` looks like our installed bundle (marker check, ADR-0018 §5)."""
    marker = dest / _MARKER_FILE
    if not marker.is_file():
        return False
    head = marker.read_text(encoding="utf-8", errors="replace")[:512]
    return bool(_MARKER_RE.search(head))


def _copy_bundle(src: Path, dest: Path) -> None:
    """Copy the manifest (files verbatim, dirs recursively) into ``dest``."""
    dest.mkdir(parents=True, exist_ok=True)
    for name in BUNDLE_FILES:
        shutil.copy2(src / name, dest / name)
    for name in BUNDLE_DIRS:
        shutil.copytree(src / name, dest / name, dirs_exist_ok=True)


@dataclass(frozen=True)
class TargetResult:
    """Outcome for one registry target."""

    target: str
    dest: Path
    action: str  # written | refreshed | skipped | refused


def install(targets: list[str], force: bool) -> list[TargetResult]:
    """Copy the bundle into each target's ``<skills-dir>/code-review/`` (ADR-0018 §4).

    create-if-missing; idempotent reported no-op without ``--force``; remove-then-copy
    refresh with it; refuse (never overwrite) a path that exists but isn't our bundle.
    """
    src = bundle_source_dir()
    results: list[TargetResult] = []
    for target in targets:
        dest = skills_dir(target) / SKILL_DIR_NAME
        if dest.exists():
            if not is_our_bundle(dest):
                results.append(TargetResult(target, dest, "refused"))
                continue
            if force:
                shutil.rmtree(dest)
                _copy_bundle(src, dest)
                results.append(TargetResult(target, dest, "refreshed"))
            else:
                results.append(TargetResult(target, dest, "skipped"))
        else:
            _copy_bundle(src, dest)
            results.append(TargetResult(target, dest, "written"))
    return results
