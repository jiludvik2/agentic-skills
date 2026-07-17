#!/bin/sh
# install.sh — copy the /api-spec skill + template into a GSD project and add the
# "## API-First Workflow" block to CLAUDE.md and/or AGENTS.md when present. See README.
# Usage: ./install.sh [project-dir]   (default: current directory)
set -eu

SRC="$(cd "$(dirname "$0")" && pwd)"
PROJECT="${1:-.}"
START="<!-- gsd-api-first:start -->"
END="<!-- gsd-api-first:end -->"

# Install the payload — map each visible source file to its (hidden) home in the project.
mkdir -p "$PROJECT/.agents/skills/api-spec" "$PROJECT/.claude/templates"
cp "$SRC/skills/api-spec/SKILL.md" "$PROJECT/.agents/skills/api-spec/SKILL.md"
cp "$SRC/templates/API-SPEC.md"    "$PROJECT/.claude/templates/API-SPEC.md"

# Add the routing block to CLAUDE.md and/or AGENTS.md, once, only if present.
found=0
for f in "$PROJECT/CLAUDE.md" "$PROJECT/AGENTS.md"; do
  [ -f "$f" ] || continue
  found=1
  grep -qF -e "$START" -e "## API-First Workflow" "$f" && continue
  [ -s "$f" ] && printf '\n' >>"$f"
  { printf '%s\n' "$START"; cat "$SRC/claude-md-section.md"; printf '%s\n' "$END"; } >>"$f"
done

[ "$found" -eq 1 ] || echo "WARNING: no CLAUDE.md or AGENTS.md in $PROJECT — skill installed; add the block from claude-md-section.md manually." >&2
