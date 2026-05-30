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
