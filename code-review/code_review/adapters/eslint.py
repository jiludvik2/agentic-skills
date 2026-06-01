from __future__ import annotations

import os
from typing import ClassVar

from code_review.adapters.js_base import has_js_files, node_binary
from code_review.capture import CaptureOutput, run_and_capture
from code_review.contracts import ReviewRequest
from code_review.paths import node_modules_dir

# ESLint v9 discovers a flat config by searching UPWARD from cwd and ignores legacy
# .eslintrc* entirely (flat-config support was dropped in v9). A target with no flat
# config on the upward path exits 2 with "couldn't find an eslint.config file" — even
# when a legacy .eslintrc IS present (express ships .eslintrc and nothing else). We
# mirror that flat-only upward walk so "nothing v9 can lint here" is reported as
# `unavailable` (a clean skip, ADR-0019) rather than a bare `eslint exited 2` error.
# Legacy-only targets get a distinct, actionable reason; the bare exit 2 was a spurious
# red on real repos before s1-t0.
_FLAT_CONFIG_NAMES = (
    "eslint.config.js", "eslint.config.mjs", "eslint.config.cjs",
    "eslint.config.ts", "eslint.config.mts", "eslint.config.cts",
)
_LEGACY_CONFIG_NAMES = (
    ".eslintrc", ".eslintrc.js", ".eslintrc.cjs",
    ".eslintrc.json", ".eslintrc.yml", ".eslintrc.yaml",
)
_SARIF_FORMATTER = "@microsoft/eslint-formatter-sarif"


def _discover_eslint_config(anchor: str) -> str:
    """Classify the eslint config discoverable on the upward path from ``anchor`` to
    the filesystem root, mirroring ESLint v9's own flat-config search:

    - ``"flat"``  — a flat ``eslint.config.*`` is reachable (lintable by v9).
    - ``"legacy"`` — no flat config, but a legacy ``.eslintrc*`` was seen on the path.
      v9 cannot consume it (flat-config-only) — treat as unavailable, not lintable.
    - ``"none"``  — no config of any kind on the path.

    Only ``"flat"`` is lintable for the vendored v9; a nearer legacy config never
    masks a flat config further up (v9 ignores .eslintrc and keeps searching)."""
    current = os.path.abspath(anchor)
    saw_legacy = False
    while True:
        for name in _FLAT_CONFIG_NAMES:
            if os.path.isfile(os.path.join(current, name)):
                return "flat"
        if not saw_legacy:
            saw_legacy = any(
                os.path.isfile(os.path.join(current, name)) for name in _LEGACY_CONFIG_NAMES
            )
        parent = os.path.dirname(current)
        if parent == current:
            return "legacy" if saw_legacy else "none"
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
        # exited 2` (ADR-0019, s0-t2). Distinct from the config skips below.
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
        # Classify the config discoverable from the anchor upward. The vendored ESLint
        # v9 is flat-config-only, so anything but a flat config means "nothing v9 can
        # lint here" → a clean skip (ADR-0019), not the bare `eslint exited 2` that
        # pollutes an otherwise-green review. A genuine eslint failure WITH a flat
        # config present still surfaces as `error` (the ok_exit_codes boundary below).
        config_kind = _discover_eslint_config(anchor)
        if config_kind == "legacy":
            return CaptureOutput.unavailable(
                "eslint",
                f"ESLint v9 requires a flat config (eslint.config.*); target under "
                f"{anchor} ships only a legacy .eslintrc — unsupported (add an "
                f"eslint.config.* to enable linting)",
            )
        if config_kind == "none":
            return CaptureOutput.unavailable(
                "eslint",
                f"no ESLint flat config (eslint.config.*) found under {anchor}",
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
