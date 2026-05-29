#!/usr/bin/env python3
"""Prefetch offline caches the analyzers need at runtime.

Stub for s1: the artifact map is empty. Real fetches (Trivy DB, Semgrep rule packs)
land with the analyzers that need them in s3. The contract this establishes now:

- caches live under ``cache/`` within ``code_review.paths.cache_root()`` (s0-t6) —
  the same base the consumers (trivy/js_base) read from;
- ``cache/manifest.json`` records the artifact set (id -> expected content hash) that
  has been fetched — manifest-addressed, not a verification of on-disk bytes;
- the script is idempotent — when the on-disk manifest already matches the desired
  artifact set, nothing is re-downloaded and the manifest is not rewritten.

This lets s3 add an entry to ``_ARTIFACTS`` (id -> expected hash) and get idempotent
download-on-change behaviour. s3 must verify the on-disk artifact bytes against the
expected hash before skipping a fetch; manifest equality alone does not detect a
truncated or corrupted cached file.
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

# artifact id -> expected content hash. Empty in s1; populated as analyzers land in s3.
_ARTIFACTS: dict[str, str] = {}


def prefetch_cache_dir() -> Path:
    """The directory this producer writes caches into — ``cache_root()/cache``,
    the exact tree the consumers resolve their reads against."""
    return cache_root() / "cache"


def main() -> int:
    cache_dir = prefetch_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
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
