#!/usr/bin/env python3
"""Prefetch offline caches the analyzers need at runtime.

Two provisioning paths: (1) the vendored **semgrep ruleset** is copied from the
skill bundle into the runtime cache by ``provision_semgrep_rules()`` (s0-t1 /
ADR-0016) — not a download, so it is not manifest-tracked; (2) download-based
artifacts (e.g. a pinned Trivy DB) are hash-addressed via ``_ARTIFACTS`` + the
manifest below (still empty pending such a pin). The contract for path (2):

- caches live under ``cache/`` within ``code_review.paths.cache_root()`` (s0-t6) —
  the same base the consumers (trivy/js_base) read from;
- ``cache/manifest.json`` records the artifact set (id -> expected content hash) that
  has been fetched — manifest-addressed, not a verification of on-disk bytes;
- the script is idempotent — when the on-disk manifest already matches the desired
  artifact set, nothing is re-downloaded and the manifest is not rewritten.

This lets a future download-based artifact add an entry to ``_ARTIFACTS``
(id -> expected hash) and get idempotent download-on-change behaviour. Such a
fetch must verify the on-disk artifact bytes against the expected hash before
skipping; manifest equality alone does not detect a truncated or corrupted file.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# s0-t6 / ADR-0015: resolve the cache base through the same source of truth the
# consumers (trivy/js_base) use, so the producer cannot write somewhere the
# consumers don't read. Bootstrap sys.path so this runs as a bare script
# (`python scripts/prefetch_caches.py`) before the package is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from code_review.paths import cache_root  # noqa: E402

# artifact id -> expected content hash. Empty for now; populated as download-based
# artifacts (e.g. a Trivy DB pin) land. The semgrep ruleset is vendored, not
# downloaded, so it is provisioned by provision_semgrep_rules() rather than via
# this manifest (s0-t1 / ADR-0016).
_ARTIFACTS: dict[str, str] = {}


def prefetch_cache_dir() -> Path:
    """The directory this producer writes caches into — ``cache_root()/cache``,
    the exact tree the consumers resolve their reads against."""
    return cache_root() / "cache"


def _bundled_semgrep_rules() -> Path:
    """The vendored semgrep ruleset committed in the skill bundle (ADR-0016).
    Copied into ``cache_root()/cache/semgrep/rules`` so the semgrep adapter's
    cache-anchored lookup finds it — the runtime cache is gitignored, the
    vendored source is not."""
    return (
        Path(__file__).resolve().parent.parent
        / ".claude" / "skills" / "code-review" / "semgrep-rules"
    )


def provision_semgrep_rules(cache_dir: Path) -> int:
    """Copy the vendored ruleset into ``<cache_dir>/semgrep/rules`` idempotently.
    Returns the number of files written (0 when already up to date). Rules are
    expected in a flat layout (``*.yaml``/``*.yml`` directly under the bundle dir)."""
    src = _bundled_semgrep_rules()
    if not src.is_dir():
        # A missing vendored ruleset is a packaging regression, not "up to date" —
        # make it visible rather than silently provisioning nothing.
        print(f"prefetch: WARNING vendored semgrep rules missing at {src}", file=sys.stderr)
        return 0
    dst = cache_dir / "semgrep" / "rules"
    dst.mkdir(parents=True, exist_ok=True)
    written = 0
    for rule_file in sorted(src.glob("*.y*ml")):
        target = dst / rule_file.name
        content = rule_file.read_text(encoding="utf-8")
        if not target.exists() or target.read_text(encoding="utf-8") != content:
            target.write_text(content, encoding="utf-8")
            written += 1
    return written


def main() -> int:
    cache_dir = prefetch_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Vendored semgrep ruleset — reconciled on every run (idempotent copy),
    # independent of the download manifest below so it self-heals even when the
    # manifest is already up to date.
    written = provision_semgrep_rules(cache_dir)
    if written:
        print(f"prefetch: provisioned {written} semgrep rule file(s)")

    manifest_path = cache_dir / "manifest.json"

    existing: dict[str, str] | None = None
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            # Corrupt/partial manifest — treat as absent and rewrite cleanly (self-heal).
            existing = None

    if existing == _ARTIFACTS:
        print("prefetch: cache up to date; nothing to fetch")
        return 0

    # s3: download each artifact whose hash differs from `existing` into cache_dir here.
    manifest_path.write_text(json.dumps(_ARTIFACTS, indent=2) + "\n", encoding="utf-8")
    print(f"prefetch: wrote manifest with {len(_ARTIFACTS)} artifact(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
