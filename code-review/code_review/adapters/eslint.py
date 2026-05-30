from __future__ import annotations

import json
import os
from typing import Any, ClassVar

from code_review.adapters.base import run_subprocess
from code_review.adapters.js_base import node_binary
from code_review.adapters.sarif_utils import empty_sarif, normalise_sarif
from code_review.contracts import AnalyzerOutput, ReviewRequest
from code_review.paths import node_modules_dir

# ESLint v9 discovers a flat config by searching UPWARD from cwd; a project with
# none (and no legacy .eslintrc) exits 2 with "couldn't find an eslint.config file".
# We mirror that upward walk so "nothing to lint here" is reported as `unavailable`
# (a clean skip, ADR-0019) rather than a bare `eslint exited 2` error.
_FLAT_CONFIG_NAMES = (
    "eslint.config.js", "eslint.config.mjs", "eslint.config.cjs",
    "eslint.config.ts", "eslint.config.mts", "eslint.config.cts",
)
_LEGACY_CONFIG_NAMES = (
    ".eslintrc", ".eslintrc.js", ".eslintrc.cjs",
    ".eslintrc.json", ".eslintrc.yml", ".eslintrc.yaml",
)


def _has_eslint_config(anchor: str) -> bool:
    """True if any eslint config (flat or legacy) is discoverable on the upward
    path from ``anchor`` to the filesystem root — the same search ESLint itself
    performs from its cwd."""
    current = os.path.abspath(anchor)
    while True:
        for name in (*_FLAT_CONFIG_NAMES, *_LEGACY_CONFIG_NAMES):
            if os.path.isfile(os.path.join(current, name)):
                return True
        parent = os.path.dirname(current)
        if parent == current:
            return False
        current = parent


class EslintAdapter:
    name: ClassVar[str] = "eslint"
    kind: ClassVar[str] = "deterministic"
    default_timeout_s: ClassVar[int] = 90
    scope_restrictions: ClassVar[frozenset[str]] = frozenset()
    node_tool: ClassVar[str] = "eslint"

    async def run(self, request: ReviewRequest) -> AnalyzerOutput:
        binary = node_binary("eslint")
        if binary is None:
            return AnalyzerOutput(
                sarif={}, status="error",
                error="eslint not found. Run scripts/setup.sh first.",
            )
        if not request.target_paths:
            return AnalyzerOutput(sarif=empty_sarif("eslint"))
        # eslint v9 flat config is discovered by searching UPWARD from the process
        # cwd (never into child dirs), and its "base path" is that cwd — targets
        # outside it are silently ignored ("File ignored because outside of base
        # path"). So the adapter anchors eslint's cwd at the targets' common-ancestor
        # directory: the reviewed project's own eslint.config.* is then found by the
        # upward search, and every target falls within the base path, regardless of
        # the caller's cwd. This assumes the targets share one project root (the
        # standard "review a project" case) — eslint v9's model is a single flat
        # config at that root governing the tree; targets spanning unrelated roots
        # collapse the anchor to their nearest common ancestor. Targets are passed
        # relative to the anchor — absolute paths can mismatch the realpath'd cwd
        # through symlinks (macOS /tmp → /private/tmp) and falsely trip the base-path
        # guard. The anchor must be a directory to serve as cwd: commonpath of a
        # single path returns that path, so fall back to its parent when it is not an
        # existing dir (a single file, or a deleted file from a diff).
        abs_targets = [os.path.abspath(p) for p in request.target_paths]
        anchor = os.path.commonpath(abs_targets)
        if not os.path.isdir(anchor):
            anchor = os.path.dirname(anchor)
        # No flat config (and no legacy .eslintrc) discoverable from the anchor
        # upward → eslint has nothing it can lint here. Report it as a clean skip,
        # not the bare `eslint exited 2` that pollutes an otherwise-green review
        # (ADR-0019). A genuine eslint failure with a config present still → error.
        if not _has_eslint_config(anchor):
            return AnalyzerOutput(
                sarif=empty_sarif("eslint"), status="unavailable",
                error=(
                    "no ESLint config (eslint.config.* or .eslintrc*) "
                    f"found under {anchor}"
                ),
            )
        rel_targets = tuple(os.path.relpath(p, anchor) for p in abs_targets)
        cmd = (
            "node", str(binary),
            "--format", "@microsoft/eslint-formatter-sarif",
            *rel_targets,
        )
        # The anchored cwd above is the reviewed project, which has no vendored
        # node_modules, so eslint cannot resolve the SARIF formatter by cwd-relative
        # module lookup. node_modules_dir() is resolved here in the parent process
        # (CWD-anchored via cache_root(), independent of the subprocess cwd) and
        # exported as an absolute NODE_PATH so the formatter resolves regardless of
        # where the target lives (replaces the smoke harness's stopgap).
        env = dict(os.environ)
        vendored = str(node_modules_dir())
        existing = env.get("NODE_PATH")
        # Prepend the vendored dir so it takes precedence over any inherited path.
        env["NODE_PATH"] = os.pathsep.join([vendored, existing]) if existing else vendored
        result = await run_subprocess(
            *cmd, timeout_s=self.default_timeout_s, cwd=anchor, env=env
        )
        if result.error is not None:
            return AnalyzerOutput(sarif={}, status="error", error=result.error)
        if result.timed_out:
            return AnalyzerOutput(sarif={}, status="timeout", error="eslint timed out")
        # ESLint exits 0 (no findings), 1 (findings), 2 (error) — 0 and 1 are success
        if result.returncode not in (0, 1):
            stderr = result.stderr.decode(errors="replace")
            return AnalyzerOutput(
                sarif={}, status="error",
                error=f"eslint exited {result.returncode}: {stderr}",
            )
        try:
            sarif: dict[str, Any] = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            return AnalyzerOutput(sarif={}, status="error", error=f"invalid JSON: {exc}")
        return AnalyzerOutput(sarif=normalise_sarif(sarif))
