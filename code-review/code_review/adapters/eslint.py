from __future__ import annotations

import os
from typing import ClassVar

from code_review.adapters.js_base import has_js_files, node_binary
from code_review.capture import CaptureOutput, run_and_capture
from code_review.contracts import ReviewRequest
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
_SARIF_FORMATTER = "@microsoft/eslint-formatter-sarif"


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

    async def run(self, request: ReviewRequest) -> CaptureOutput:
        binary = node_binary("eslint")
        if binary is None:
            # Missing vendored binary is a provisioning gap, not a scan failure
            # (ADR-0019): report unavailable, carrying the actionable reason.
            return CaptureOutput.unavailable(
                "eslint", "eslint not found in vendored node_modules. Run scripts/setup.sh first."
            )
        if not request.target_paths:
            return CaptureOutput.unavailable("eslint", "no target paths to analyse")
        # No JS/TS anywhere in the target → nothing for eslint to do (e.g. a
        # pure-Python review). A clean skip, not the spurious red of `eslint
        # exited 2` (ADR-0019, s0-t2). Distinct from the no-flat-config skip below.
        if not has_js_files(request.target_paths):
            return CaptureOutput.unavailable(
                "eslint", "no JavaScript/TypeScript files in target"
            )
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
            return CaptureOutput.unavailable(
                "eslint",
                f"no ESLint config (eslint.config.* or .eslintrc*) found under {anchor}",
            )
        rel_targets = tuple(os.path.relpath(p, anchor) for p in abs_targets)
        # The SARIF formatter (a vendored *package* loaded by name) is kept: eslint emits
        # SARIF on stdout, which the thin runner captures verbatim (ADR-0020) — no parse
        # here. The anchored cwd is the reviewed project, which has no vendored
        # node_modules, so eslint cannot resolve that formatter by cwd-relative lookup.
        # node_modules_dir() is resolved in the parent process (CWD-anchored via
        # cache_root(), independent of the subprocess cwd) and exported as an absolute
        # NODE_PATH so the formatter resolves regardless of where the target lives.
        cmd = (
            "node", str(binary),
            "--format", _SARIF_FORMATTER,
            *rel_targets,
        )
        env = dict(os.environ)
        vendored = str(node_modules_dir())
        existing = env.get("NODE_PATH")
        # Prepend the vendored dir so it takes precedence over any inherited path.
        env["NODE_PATH"] = os.pathsep.join([vendored, existing]) if existing else vendored
        # ESLint exits 0 (no findings) or 1 (findings present) — both are success; 2 (a
        # genuine config/crash error) is left untolerated and surfaces as `error`.
        return await run_and_capture(
            "eslint", *cmd,
            timeout_s=self.default_timeout_s,
            cwd=anchor,
            env=env,
            ok_exit_codes=(0, 1),
        )
