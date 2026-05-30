"""Single source of truth for the skill-bundle manifest (ADR-0018 §2).

The bundle is the subset of ``.claude/skills/code-review/`` that ships in the wheel
and is placed by ``polyreview install``. Packaging (s6-t1), the install command
(s6-t2) and the uninstall guard (s7-t0) all read these constants so the three
operations cannot diverge.

In the built wheel, the assets are force-included under ``code_review/_bundle/``
(the ``BUNDLE_ROOT`` subdir; see ``pyproject.toml``
``[tool.hatch.build.targets.wheel.force-include]``) so they are reachable via
``importlib.resources.files("code_review")`` from an installed layout.
"""

from __future__ import annotations

# Subdirectory within the installed ``code_review`` package where the wheel
# force-includes the bundle assets.
BUNDLE_ROOT = "_bundle"

# Files copied verbatim into ``<skills-dir>/code-review/`` at install time.
BUNDLE_FILES: tuple[str, ...] = (
    "SKILL.md",
    "code-review.toml.example",
    "package.json",
    "package-lock.json",
)

# Directories copied whole (recursively) into ``<skills-dir>/code-review/``.
BUNDLE_DIRS: tuple[str, ...] = ("semgrep-rules",)

# Every manifest entry (files then dirs) — for presence assertions and listing.
BUNDLE_MANIFEST: tuple[str, ...] = BUNDLE_FILES + BUNDLE_DIRS

# Provisioned/produced trees that are NEVER shipped or copied (ADR-0018 §2):
# node_modules (~102 MB, host-specific), cache (~1 GB, Trivy DB), runs (outputs).
BUNDLE_EXCLUDED: tuple[str, ...] = ("node_modules", "cache", "runs")
