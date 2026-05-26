#!/usr/bin/env python3
"""Prefetch offline caches the analyzers need at runtime.

Stub for s1: the artifact map is empty. Real fetches (Trivy DB, Semgrep rule packs)
land with the analyzers that need them in s3. The contract this establishes now:

- caches live under ``cache/`` in the current working directory;
- a content-addressed ``cache/manifest.json`` records what has been fetched;
- the script is idempotent — when the on-disk manifest already matches the desired
  artifact set, nothing is re-downloaded and the manifest is not rewritten.

This lets s3 add an entry to ``_ARTIFACTS`` (id -> content hash) and get idempotent
download-on-change behaviour for free.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# artifact id -> expected content hash. Empty in s1; populated as analyzers land in s3.
_ARTIFACTS: dict[str, str] = {}


def main() -> int:
    cache_dir = Path.cwd() / "cache"
    cache_dir.mkdir(exist_ok=True)
    manifest_path = cache_dir / "manifest.json"

    existing: dict[str, str] | None = None
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))

    if existing == _ARTIFACTS:
        print("prefetch: cache up to date; nothing to fetch")
        return 0

    # s3: download each artifact whose hash differs from `existing` into cache_dir here.
    manifest_path.write_text(json.dumps(_ARTIFACTS, indent=2) + "\n", encoding="utf-8")
    print(f"prefetch: wrote manifest with {len(_ARTIFACTS)} artifact(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
