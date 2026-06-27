#!/usr/bin/env python3
"""
install.py — GSD API-first workflow enhancements installer.

Installs (or restores after a GSD upgrade) the API-first workflow enhancements
into any GSD-enabled project. Idempotent: safe to run multiple times.

Usage
-----
  # Install into the current directory:
  python3 install.py

  # Install into a specific project directory:
  python3 install.py /path/to/project

  # Dry run — show what would be installed without writing anything:
  python3 install.py --dry-run [project-dir]

  # Update mode — copy files FROM the project BACK to this source tree
  # (use when you've modified installed files and want to save the changes):
  python3 install.py --update [project-dir]

  # Uninstall — remove all installed files and strip the CLAUDE.md section:
  python3 install.py --uninstall [project-dir]

What it installs
----------------
  .agents/skills/api-phase/SKILL.md             /api-phase slash command
  .agents/skills/api-plan/SKILL.md              /api-plan slash command
  .agents/skills/gsd-discuss-phase/SKILL.md     project-local patch — surfaces API gray
                                                areas natively in discuss-phase
  .claude/api-gray-areas.md                     API gray areas reference (read by the
                                                patched discuss-phase skill)
  .claude/templates/API-SPEC.md                 API contract template for api-phase output
  CLAUDE.md                                     Injects ## API-First Workflow section
                                                into the <!-- project-overrides --> block

What it does NOT install
------------------------
  Project-specific tests                  Test the API contract properties that
                                          are specific to your schema — the skill
                                          tells you what to verify, not how.

Upgrade safety
--------------
  All installed files live in .agents/skills/ (git-tracked, not GSD-managed) or
  in .claude/ (project-level, not in ~/.claude/gsd-core/). GSD upgrades operate
  on ~/.claude/gsd-core/ and ~/.claude/skills/ (global). Project files are not
  touched. Re-run this script after a GSD upgrade if any files were lost.
"""

from __future__ import annotations

import argparse
import difflib
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
TARGET_DIR = SCRIPT_DIR / "target"
CLAUDE_MD_SECTION = SCRIPT_DIR / "claude-md-section.md"

# File map: (source relative to TARGET_DIR, dest relative to project root)
FILE_MAP: list[tuple[str, str]] = [
    (".agents/skills/api-phase/SKILL.md",           ".agents/skills/api-phase/SKILL.md"),
    (".agents/skills/api-plan/SKILL.md",            ".agents/skills/api-plan/SKILL.md"),
    (".agents/skills/gsd-discuss-phase/SKILL.md",   ".agents/skills/gsd-discuss-phase/SKILL.md"),
    (".claude/api-gray-areas.md",                   ".claude/api-gray-areas.md"),
    (".claude/templates/API-SPEC.md",               ".claude/templates/API-SPEC.md"),
]

# Marker used to detect the API-first section in CLAUDE.md
CLAUDE_MD_MARKER = "## API-First Workflow"

# The block in CLAUDE.md that is user-controlled (our injection zone)
OVERRIDES_START = "<!-- project-overrides -->"
OVERRIDES_END   = "<!-- /project-overrides -->"


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
# Project detection
# ---------------------------------------------------------------------------

def detect_project(candidate: Path) -> Path:
    """Return the project root if candidate looks like a GSD-enabled project."""
    if not candidate.is_dir():
        raise SystemExit(red(f"Error: '{candidate}' is not a directory."))
    indicators = [".claude", ".planning", "CLAUDE.md"]
    found = [i for i in indicators if (candidate / i).exists()]
    if not found:
        print(yellow(
            f"Warning: '{candidate}' does not look like a GSD project "
            f"(none of {indicators} found). Continuing anyway."
        ))
    return candidate.resolve()


# ---------------------------------------------------------------------------
# Core install/update operations
# ---------------------------------------------------------------------------

def install_files(
    project: Path,
    dry_run: bool,
) -> tuple[list[str], list[str], list[str]]:
    """Copy files from target/ to project. Returns (installed, skipped, errors)."""
    installed, skipped, errors = [], [], []

    for src_rel, dst_rel in FILE_MAP:
        src = TARGET_DIR / src_rel
        dst = project / dst_rel

        if not src.exists():
            errors.append(f"{src_rel}: source file missing from installer package")
            continue

        src_text = src.read_text(encoding="utf-8")

        if dst.exists():
            dst_text = dst.read_text(encoding="utf-8")
            if src_text == dst_text:
                skipped.append(f"{dst_rel} (already up to date)")
                continue
            # File exists but differs — show a short diff and overwrite
            diff = list(difflib.unified_diff(
                dst_text.splitlines(), src_text.splitlines(),
                fromfile=f"project/{dst_rel}",
                tofile=f"installer/{src_rel}",
                lineterm="",
            ))
            print(dim(f"\n  diff for {dst_rel}:"))
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

        installed.append(dst_rel)

    return installed, skipped, errors


def inject_claude_md(project: Path, dry_run: bool) -> str:
    """Inject the ## API-First Workflow section into CLAUDE.md. Returns status."""
    claude_md = project / "CLAUDE.md"
    section = CLAUDE_MD_SECTION.read_text(encoding="utf-8").strip()

    if not claude_md.exists():
        if dry_run:
            return "would create CLAUDE.md with project-overrides block"
        content = f"{OVERRIDES_START}\n{section}\n{OVERRIDES_END}\n"
        claude_md.write_text(content, encoding="utf-8")
        return "created CLAUDE.md with project-overrides block"

    text = claude_md.read_text(encoding="utf-8")

    # Already present?
    if CLAUDE_MD_MARKER in text:
        return "already present — no change"

    # Try to inject into existing project-overrides block
    if OVERRIDES_START in text and OVERRIDES_END in text:
        # Insert before the closing tag, preserving surrounding whitespace
        new_text = text.replace(
            OVERRIDES_END,
            f"\n{section}\n{OVERRIDES_END}",
        )
        if not dry_run:
            claude_md.write_text(new_text, encoding="utf-8")
        return "injected into existing project-overrides block"

    # No project-overrides block — prepend one
    new_text = f"{OVERRIDES_START}\n{section}\n{OVERRIDES_END}\n\n{text}"
    if not dry_run:
        claude_md.write_text(new_text, encoding="utf-8")
    return "prepended new project-overrides block"


def eject_claude_md(project: Path, dry_run: bool) -> str:
    """Remove the ## API-First Workflow section from CLAUDE.md. Returns status."""
    claude_md = project / "CLAUDE.md"
    if not claude_md.exists():
        return "CLAUDE.md not found — nothing to remove"

    text = claude_md.read_text(encoding="utf-8")
    if CLAUDE_MD_MARKER not in text:
        return "section not present — nothing to remove"

    lines = text.splitlines(keepends=True)
    out, inside, found = [], False, False
    i = 0
    while i < len(lines):
        line = lines[i]
        if not inside and line.strip() == CLAUDE_MD_MARKER:
            inside = True
            found = True
            i += 1
            continue
        if inside:
            # Stop at the next ## heading or the overrides closing tag
            if (line.startswith("## ") and line.strip() != CLAUDE_MD_MARKER) or \
               line.strip() == OVERRIDES_END:
                inside = False
                # Don't consume this line — fall through to append it
            else:
                i += 1
                continue
        out.append(line)
        i += 1

    if not found:
        return "section not present — nothing to remove"

    # Collapse multiple blank lines left behind by the removal
    cleaned: list[str] = []
    blank_run = 0
    for line in out:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= 1:
                cleaned.append(line)
        else:
            blank_run = 0
            cleaned.append(line)

    if not dry_run:
        claude_md.write_text("".join(cleaned), encoding="utf-8")
    return "removed from CLAUDE.md"


def uninstall_files(project: Path, dry_run: bool) -> tuple[list[str], list[str]]:
    """Remove files installed by FILE_MAP. Returns (removed, skipped)."""
    removed, skipped = [], []
    for _src_rel, dst_rel in FILE_MAP:
        dst = project / dst_rel
        if not dst.exists():
            skipped.append(f"{dst_rel} (not present)")
            continue
        if not dry_run:
            dst.unlink()
            # Remove parent dir if now empty
            try:
                dst.parent.rmdir()
            except OSError:
                pass
        removed.append(dst_rel)
    return removed, skipped


def update_from_project(project: Path, dry_run: bool) -> None:
    """Copy files FROM the project BACK to target/ (save local changes)."""
    print(bold("Update mode — syncing project files back to installer source\n"))
    changed, unchanged, missing = [], [], []

    for src_rel, dst_rel in FILE_MAP:
        src = TARGET_DIR / src_rel
        project_file = project / dst_rel

        if not project_file.exists():
            missing.append(dst_rel)
            continue

        project_text = project_file.read_text(encoding="utf-8")
        if src.exists() and src.read_text(encoding="utf-8") == project_text:
            unchanged.append(dst_rel)
            continue

        if not dry_run:
            src.parent.mkdir(parents=True, exist_ok=True)
            src.write_text(project_text, encoding="utf-8")
        changed.append(dst_rel)

    _print_results(
        installed=changed, skipped=unchanged, errors=missing,
        mode="update", dry_run=dry_run,
        installed_label="updated in installer", skipped_label="unchanged",
        error_label="not in project (skipped)",
    )


# ---------------------------------------------------------------------------
# Output
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
    print(bold(f"  {mode}: {len(installed)} changed, {len(skipped)} unchanged, {len(errors)} errors  ({total} files)"))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Install GSD API-first workflow enhancements into a project.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "project_dir",
        nargs="?",
        default=".",
        help="Project root directory (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be installed without writing anything",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Copy files FROM the project BACK to this installer (save local changes)",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove all installed files and strip the CLAUDE.md section",
    )
    args = parser.parse_args()

    project = detect_project(Path(args.project_dir))
    mode_label = (
        "dry run" if args.dry_run else
        "update" if args.update else
        "uninstall" if args.uninstall else
        "install"
    )

    print(bold(f"\nGSD API-first — {mode_label}"))
    print(dim(f"  installer: {SCRIPT_DIR}"))
    print(dim(f"  project:   {project}\n"))

    if args.update:
        update_from_project(project, dry_run=args.dry_run)
        return

    if args.uninstall:
        removed, skipped = uninstall_files(project, dry_run=args.dry_run)
        claude_md_status = eject_claude_md(project, dry_run=args.dry_run)
        prefix = dim("[dry-run] ") if args.dry_run else ""
        for f in removed:
            print(f"  {prefix}{green('✓')} removed: {f}")
        for f in skipped:
            print(f"  {dim('–')} skipped: {dim(f)}")
        print(f"  {prefix}{green('✓')} CLAUDE.md: {claude_md_status}")
        print()
        print(bold(f"  uninstall: {len(removed)} removed, {len(skipped)} skipped"))
        return

    # Install mode
    installed, skipped, errors = install_files(project, dry_run=args.dry_run)

    claude_md_status = inject_claude_md(project, dry_run=args.dry_run)
    if "already present" in claude_md_status:
        skipped.append(f"CLAUDE.md ## API-First Workflow section ({claude_md_status})")
    else:
        installed.append(f"CLAUDE.md ({claude_md_status})")

    _print_results(
        installed=installed, skipped=skipped, errors=errors,
        mode="install", dry_run=args.dry_run,
    )

    if errors:
        print(red(f"\n  {len(errors)} error(s) — check the installer package is intact."))
        sys.exit(1)

    if not args.dry_run and installed:
        print()
        print(bold("  Next steps:"))
        print(f"    git add {project / '.agents'} {project / '.claude/api-gray-areas.md'} "
              f"{project / '.claude/templates'} {project / 'CLAUDE.md'}")
        print(f"    git commit -m 'chore: install GSD API-first workflow enhancements'")
        print()
        print(f"  New slash commands available:")
        print(f"    {green('/api-phase <N>')}   design HTTP contract from functional requirements")
        print(f"    {green('/api-plan <N>')}    plan with API-SPEC.md + governance docs auto-ingested")


if __name__ == "__main__":
    main()
