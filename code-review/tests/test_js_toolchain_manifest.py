"""s1-t1 / ADR-0017: the committed JS toolchain manifest + lockfile at the skill
root pin the five Node packages the JS/TS analyzers depend on, so a clean
`setup.sh` (`npm ci`) produces a reproducible toolchain (FINDINGS F5)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).parent.parent / ".claude" / "skills" / "code-review"
PACKAGE_JSON = SKILL_ROOT / "package.json"
LOCKFILE = SKILL_ROOT / "package-lock.json"

# Caret-major pins per ADR-0017. dependency-cruiser's exact pin is delegated to
# s3 (it must work on both Node 20 and 22), so here we only require its presence.
EXPECTED_PINS = {
    "eslint": "^9",
    "knip": "^5",
    "jscpd": "^4",
    "@microsoft/eslint-formatter-sarif": "^3",
}
MUST_BE_PRESENT = set(EXPECTED_PINS) | {"dependency-cruiser"}

# s3-t0: the lowest dependency-cruiser release that runs on the supported Node
# range (ADR-0017: Node 20 + 22, and modern Node generally). Up to and including
# 16.10.1, ``src/cli/utl/assert-file-existence.mjs`` does
# ``import { accessSync, R_OK } from "node:fs"`` — and Node ≥22 rejects ``R_OK``
# as a named export of ``node:fs`` (it lives on ``fs.constants``), so the CLI
# dies with a SyntaxError before doing any work (FINDINGS F1). 16.10.2 switched
# to ``import { accessSync, constants } from "node:fs"`` and loads cleanly.
# Boundary confirmed empirically against the npm tarballs on Node 24:
# 16.10.1 broken, 16.10.2 fixed (the story's "~16.3" estimate was wrong).
DEPCRUISER_NODE_FS_CONSTANTS_FLOOR = (16, 10, 2)


def _version_tuple(v: str) -> tuple[int, ...]:
    # Drop any pre-release/build suffix (e.g. "16.10.2-beta-1") before comparing.
    core = re.split(r"[-+]", v, maxsplit=1)[0]
    return tuple(int(part) for part in core.split("."))


def test_depcruiser_pin_is_node_compatible() -> None:
    """s3-t0 (F1): the locked dependency-cruiser must be a version that imports
    ``R_OK`` from ``node:fs/constants`` rather than as a named export of
    ``node:fs`` — i.e. ``>= 16.10.2`` — so the coupling analyzer survives the
    supported Node range instead of dying on the ``R_OK`` SyntaxError."""
    lock = json.loads(LOCKFILE.read_text(encoding="utf-8"))
    entry = lock["packages"]["node_modules/dependency-cruiser"]
    locked = _version_tuple(entry["version"])
    assert locked >= DEPCRUISER_NODE_FS_CONSTANTS_FLOOR, (
        f"dependency-cruiser locked at {entry['version']} is below the "
        f"Node-fs/constants floor {'.'.join(map(str, DEPCRUISER_NODE_FS_CONSTANTS_FLOOR))} "
        "(F1: R_OK SyntaxError on Node >=22)"
    )


def _all_deps(manifest: dict[str, Any]) -> dict[str, str]:
    return {**manifest.get("dependencies", {}), **manifest.get("devDependencies", {})}


def test_package_manifest_exists() -> None:
    assert PACKAGE_JSON.is_file(), f"missing {PACKAGE_JSON}"


def test_package_manifest_pins_node_tools() -> None:
    manifest = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    deps = _all_deps(manifest)
    for pkg in MUST_BE_PRESENT:
        assert pkg in deps, f"{pkg} not pinned in package.json"
    for pkg, pin in EXPECTED_PINS.items():
        assert deps[pkg] == pin, f"{pkg}: expected {pin}, got {deps[pkg]}"


def test_lockfile_present() -> None:
    assert LOCKFILE.is_file(), f"missing {LOCKFILE} — run `npm install` at {SKILL_ROOT}"


def test_lockfile_pins_match_manifest() -> None:
    """Every tool in the manifest resolves to a concrete lockfile version whose
    MAJOR matches the manifest's caret/tilde-major pin — the manifest↔lock drift
    guard for the `^N` pins ADR-0017 uses (the capabilities↔lock guard is s1-t2).

    Pin forms other than `^N`/`~N`/`N…` fail loudly rather than no-op, so a later
    story rewriting a pin to a range/tag (e.g. the s3 depcruiser bump) can't slip
    the guard silently — it must extend this check."""
    manifest = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    lock = json.loads(LOCKFILE.read_text(encoding="utf-8"))
    packages: dict[str, Any] = lock.get("packages", {})
    deps = _all_deps(manifest)

    for pkg, pin in deps.items():
        entry = packages.get(f"node_modules/{pkg}")
        assert entry is not None, f"{pkg} absent from lockfile packages"
        locked = entry.get("version", "")
        m = re.match(r"^[\^~]?(\d+)(?:\.|$)", pin)
        assert m is not None, (
            f"{pkg}: unrecognised pin form {pin!r} — extend this drift guard to "
            "cover it (a range/tag pin introduced by a later story)"
        )
        assert locked.startswith(m.group(1) + "."), (
            f"{pkg}: manifest pin {pin} but lockfile {locked} (major mismatch)"
        )
