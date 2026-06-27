#!/usr/bin/env python3
"""
install.py — GSD standard-enforcement addon installer.

Patches four GSD core files to enforce architecture contracts, generate ADRs,
and enable full-codebase audits. Backs up the patched files to gsd-local-patches/
so they survive future GSD upgrades (re-apply with /gsd-update --reapply).

Idempotent: safe to run multiple times.

Usage
-----
  # Install at user level (patches ~/.claude/):
  python3 install.py
  python3 install.py --user

  # Install at project level (patches {project}/.claude/):
  python3 install.py --project /path/to/project

  # Dry run — show what would change without writing anything:
  python3 install.py [--user | --project PATH] --dry-run

  # Update mode — copy installed files BACK to target/ (save local edits):
  python3 install.py [--user | --project PATH] --update

What it patches
---------------
  gsd-core/workflows/code-review.md          Adds --audit flag (Tier 0 scope:
                                              full src/market_data codebase review)
  gsd-core/workflows/discuss-phase.md        Adds write_adrs step — generates ADRs
                                              for significant decisions after discuss
  gsd-core/workflows/discuss-phase/          Lazy-loaded step that implements ADR
    steps/write-adrs.md                      generation (NEW file, not in upstream)
  agents/gsd-code-reviewer.md               Adds architecture/standards contract
                                              loading (reads docs/ARCHITECTURE.md,
                                              docs/STANDARDS.md, docs/adr/)

Upgrade safety
--------------
  After patching, each file is backed up to gsd-local-patches/ inside the GSD
  config directory. When /gsd-update --reapply runs after a GSD upgrade, it
  restores these backups. Re-running this installer refreshes the backups to
  the latest version in target/.
"""

from __future__ import annotations

import argparse
import datetime
import difflib
import hashlib
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent

# Files patched, relative to the GSD config dir (e.g. ~/.claude/ or .claude/)
PATCH_FILES: list[str] = [
    "gsd-core/workflows/code-review.md",
    "gsd-core/workflows/discuss-phase.md",
    "gsd-core/workflows/discuss-phase/steps/write-adrs.md",
    "agents/gsd-code-reviewer.md",
]

# write-adrs.md is a new file with no upstream counterpart — no pristine hash
_NEW_FILES: frozenset[str] = frozenset({"gsd-core/workflows/discuss-phase/steps/write-adrs.md"})


# ---------------------------------------------------------------------------
# Colour helpers (gracefully degrade if no TTY)
# ---------------------------------------------------------------------------

def _c(code: str, text: str) -> str:
    if sys.stdout.isatty():
        return f"\033[{code}m{text}\033[0m"
    return text


green  = lambda t: _c("32", t)
yellow = lambda t: _c("33", t)
red    = lambda t: _c("31", t)
bold   = lambda t: _c("1",  t)
dim    = lambda t: _c("2",  t)


# ---------------------------------------------------------------------------
# GSD detection
# ---------------------------------------------------------------------------

def detect_gsd_dir(user: bool, project: Path | None) -> Path:
    """Return the GSD config directory and verify GSD is installed there."""
    if project is not None:
        gsd_dir = project / ".claude"
        version_file = gsd_dir / "gsd-core" / "VERSION"
        if not version_file.exists():
            raise SystemExit(
                red(
                    f"Error: No local GSD install found at {gsd_dir / 'gsd-core'}/ — "
                    f"use --user to patch the global install"
                )
            )
        return gsd_dir

    # User level
    gsd_dir = Path.home() / ".claude"
    version_file = gsd_dir / "gsd-core" / "VERSION"
    if not version_file.exists():
        raise SystemExit(
            red(
                f"Error: GSD not found at {gsd_dir / 'gsd-core'}/ — "
                f"install GSD first with: npx -y @opengsd/gsd-core@latest --claude"
            )
        )
    return gsd_dir


def read_gsd_version(gsd_dir: Path) -> str:
    """Read GSD version from VERSION file."""
    version_file = gsd_dir / "gsd-core" / "VERSION"
    try:
        return version_file.read_text(encoding="utf-8").strip()
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Core install operation
# ---------------------------------------------------------------------------

def install_files(
    gsd_dir: Path,
    dry_run: bool,
) -> tuple[list[str], list[str], list[str]]:
    """Patch files from target/ into gsd_dir. Returns (installed, skipped, errors)."""
    installed, skipped, errors = [], [], []

    for rel_path in PATCH_FILES:
        src = SCRIPT_DIR / "target" / rel_path
        dst = gsd_dir / rel_path

        if not src.exists():
            errors.append(f"{rel_path}: source file missing from installer package")
            continue

        src_text = src.read_text(encoding="utf-8")

        if dst.exists():
            dst_text = dst.read_text(encoding="utf-8")
            if src_text == dst_text:
                skipped.append(rel_path)
                continue
            # File differs — show a short unified diff before overwriting
            diff = list(difflib.unified_diff(
                dst_text.splitlines(), src_text.splitlines(),
                fromfile=f"installed/{rel_path}",
                tofile=f"patch/{rel_path}",
                lineterm="",
            ))
            print(dim(f"\n  diff for {rel_path}:"))
            for line in diff[:30]:
                if line.startswith("+"):
                    print(green(f"    {line}"))
                elif line.startswith("-"):
                    print(red(f"    {line}"))
                else:
                    print(dim(f"    {line}"))
            if len(diff) > 30:
                print(dim(f"    ... ({len(diff) - 30} more lines)"))

        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(src_text, encoding="utf-8")

        installed.append(rel_path)

    return installed, skipped, errors


# ---------------------------------------------------------------------------
# gsd-local-patches backup
# ---------------------------------------------------------------------------

def update_local_patches(gsd_dir: Path, dry_run: bool, gsd_version: str) -> None:
    """Backup patched files to gsd-local-patches/ and update backup-meta.json."""
    patches_dir = gsd_dir / "gsd-local-patches"
    meta_path = patches_dir / "backup-meta.json"

    # Load existing backup-meta if present
    meta: dict = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            meta = {}

    # Ensure required fields exist
    if "files" not in meta:
        meta["files"] = []
    if "pristine_hashes" not in meta:
        meta["pristine_hashes"] = {}

    for rel_path in PATCH_FILES:
        gsd_file = gsd_dir / rel_path
        backup_file = patches_dir / rel_path
        patched_content = (SCRIPT_DIR / "target" / rel_path).read_text(encoding="utf-8")

        # Compute pristine hash only for files that exist upstream (not new files)
        # and only on first install (file currently differs from our patch)
        if rel_path not in _NEW_FILES and gsd_file.exists():
            current = gsd_file.read_text(encoding="utf-8")
            if current != patched_content and rel_path not in meta["pristine_hashes"]:
                # File exists and differs from our patch — it's the pristine upstream version
                pristine_hash = hashlib.sha256(current.encode()).hexdigest()
                meta["pristine_hashes"][rel_path] = pristine_hash

        # Track in the files list
        if rel_path not in meta["files"]:
            meta["files"].append(rel_path)

        if not dry_run:
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            backup_file.write_text(patched_content, encoding="utf-8")

    # Update metadata fields
    meta["backed_up_at"] = (
        datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    )
    meta["from_version"] = gsd_version
    meta["installer"] = "gsd-standard-enforcement"

    if not dry_run:
        patches_dir.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Update mode — copy installed files back to target/
# ---------------------------------------------------------------------------

def update_from_gsd(gsd_dir: Path, dry_run: bool) -> None:
    """Copy files FROM gsd_dir BACK to target/ (save local edits to installer)."""
    print(bold("Update mode — syncing installed files back to installer source\n"))
    changed, unchanged, missing = [], [], []

    for rel_path in PATCH_FILES:
        src = SCRIPT_DIR / "target" / rel_path
        installed_file = gsd_dir / rel_path

        if not installed_file.exists():
            missing.append(rel_path)
            continue

        installed_text = installed_file.read_text(encoding="utf-8")
        if src.exists() and src.read_text(encoding="utf-8") == installed_text:
            unchanged.append(rel_path)
            continue

        if not dry_run:
            src.parent.mkdir(parents=True, exist_ok=True)
            src.write_text(installed_text, encoding="utf-8")
        changed.append(rel_path)

    _print_results(
        installed=changed,
        skipped=unchanged,
        errors=missing,
        mode="update",
        dry_run=dry_run,
        installed_label="updated in installer",
        skipped_label="unchanged",
        error_label="not installed (skipped)",
    )


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _print_results(
    installed: list[str],
    skipped: list[str],
    errors: list[str],
    mode: str,
    dry_run: bool,
    installed_label: str = "installed",
    skipped_label: str = "already up to date",
    error_label: str = "error",
) -> None:
    prefix = dim("[dry-run] ") if dry_run else ""

    print()
    for f in installed:
        print(f"  {prefix}{green('✓')} {installed_label}: {f}")
    for f in skipped:
        print(f"  {dim('–')} {skipped_label}: {dim(f)}")
    for f in errors:
        print(f"  {red('✗')} {error_label}: {f}")

    total = len(installed) + len(skipped) + len(errors)
    print()
    print(bold(
        f"  {mode}: {len(installed)} changed, {len(skipped)} unchanged, "
        f"{len(errors)} errors  ({total} files)"
    ))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Patch GSD core files to enforce architecture contracts and enable audit mode.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    scope = parser.add_mutually_exclusive_group()
    scope.add_argument(
        "--user",
        action="store_true",
        help="Patch the user-level GSD install at ~/.claude/ (default)",
    )
    scope.add_argument(
        "--project",
        metavar="PATH",
        type=Path,
        help="Patch a project-level GSD install at PATH/.claude/",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without writing anything",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Copy installed files FROM the GSD install BACK to target/ (save local edits)",
    )
    args = parser.parse_args()

    # Resolve scope
    project: Path | None = None
    if args.project is not None:
        project = args.project.resolve()
        if not project.is_dir():
            raise SystemExit(red(f"Error: '{project}' is not a directory."))

    gsd_dir = detect_gsd_dir(user=args.user, project=project)
    gsd_version = read_gsd_version(gsd_dir)

    scope_label = f"project ({gsd_dir})" if project else f"user ({gsd_dir})"
    mode_label = "dry run" if args.dry_run else ("update" if args.update else "install")

    print(bold(f"\nGSD standard-enforcement — {mode_label}"))
    print(dim(f"  installer: {SCRIPT_DIR}"))
    print(dim(f"  target:    {gsd_dir}"))
    print(dim(f"  GSD:       {gsd_version}"))
    print(dim(f"  scope:     {scope_label}\n"))

    if args.update:
        update_from_gsd(gsd_dir, dry_run=args.dry_run)
        return

    # Install mode
    installed, skipped, errors = install_files(gsd_dir, dry_run=args.dry_run)

    _print_results(
        installed=installed,
        skipped=skipped,
        errors=errors,
        mode="install",
        dry_run=args.dry_run,
    )

    if errors:
        print(red(f"\n  {len(errors)} error(s) — check the installer package is intact."))
        sys.exit(1)

    # Update gsd-local-patches backup
    if not args.dry_run and (installed or skipped):
        update_local_patches(gsd_dir, dry_run=False, gsd_version=gsd_version)
        patches_dir = gsd_dir / "gsd-local-patches"
        print(dim(f"\n  Backup updated: {patches_dir}/"))
    elif args.dry_run:
        print(dim(f"\n  [dry-run] Would update: {gsd_dir}/gsd-local-patches/"))

    if not args.dry_run and installed:
        print()
        print(bold("  Next steps:"))
        print()
        print(f"    Patches applied ({len(installed)} file(s) updated):")
        for f in installed:
            print(f"      {dim(f)}")
        print()
        print(f"    After a future GSD upgrade, re-apply with:")
        print(f"      python3 {SCRIPT_DIR}/install.py")
        print(f"    Or let GSD restore the backup automatically:")
        print(f"      /gsd-update --reapply")
        print()
        print(f"  Active patches:")
        print(f"    {green('--audit flag')}          full-codebase review scope in /gsd-code-review")
        print(f"    {green('architecture contract')} gsd-code-reviewer loads docs/ARCHITECTURE.md + ADRs")
        print(f"    {green('ADR generation')}        discuss-phase writes ADRs for significant decisions")


if __name__ == "__main__":
    main()
