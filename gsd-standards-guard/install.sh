#!/usr/bin/env bash
# install.sh — install (or uninstall) the gsd-standards-guard addon into a GSD
# project. Zero vendor patches: everything lands in project-owned, upgrade-safe
# locations (.claude/skills/, .claude/hooks/, .claude/settings.json, docs/,
# CLAUDE.md). See README.
#
# Usage:
#   ./install.sh [--project PATH]     install into PATH (default: current dir)
#   ./install.sh --uninstall [--project PATH]
#
# What it does (install):
#   1. copies the skills into PATH/.claude/skills/ and the hook into
#      PATH/.claude/hooks/ (.claude/skills/ is where Claude Code discovers skills;
#      it sits outside GSD's manifest, so upgrades never touch it)
#   2. adds/replaces our hooks.PreToolUse entry in PATH/.claude/settings.json
#      (preserving every other entry — GSD's merge writer preserves it in turn)
#   3. inserts the marked directive block into PATH/CLAUDE.md
#   4. seeds docs/adr/index.yaml + docs/ARCHITECTURE.md if absent, then validates
#      that index.yaml parses (fail loud otherwise)
#   5. never touches anything under .claude/gsd-core/ or .claude/agents/
set -eu

SRC="$(cd "$(dirname "$0")" && pwd)"
PROJECT="."
UNINSTALL=0

while [ $# -gt 0 ]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --project=*) PROJECT="${1#*=}"; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

PROJECT="$(cd "$PROJECT" && pwd)"
BEGIN="<!-- gsd-standards-guard:begin -->"
END="<!-- gsd-standards-guard:end -->"
HOOK_CMD='node "$CLAUDE_PROJECT_DIR/.claude/hooks/gsd-standards-guard.js"'
SETTINGS="$PROJECT/.claude/settings.json"
CLAUDE_MD="$PROJECT/CLAUDE.md"

command -v node >/dev/null 2>&1 || { echo "error: node is required (Claude Code project)"; exit 1; }

# Remove the marked block from a file, if present (prints the remainder).
strip_block() {
  awk -v b="$BEGIN" -v e="$END" '
    $0 == b {skip=1}
    skip==0 {print}
    $0 == e {skip=0}
  ' "$1"
}

if [ "$UNINSTALL" -eq 1 ]; then
  echo "gsd-standards-guard: uninstalling from $PROJECT"
  rm -rf "$PROJECT/.claude/skills/gsd-standards-guard" \
         "$PROJECT/.claude/skills/write-adr" \
         "$PROJECT/.claude/skills/standards-audit" \
         "$PROJECT/.claude/skills/adr-index-audit" \
         "$PROJECT/.claude/hooks/gsd-standards-guard.js"
  if [ -f "$SETTINGS" ]; then
    node "$SRC/templates/merge-settings.js" "$SETTINGS" "" --remove
  fi
  if [ -f "$CLAUDE_MD" ] && grep -qF "$BEGIN" "$CLAUDE_MD"; then
    tmp="$(mktemp)"; strip_block "$CLAUDE_MD" > "$tmp"
    # collapse a trailing run of blank lines to one
    awk 'NF{blank=0} !NF{blank++} blank<2' "$tmp" > "$CLAUDE_MD"; rm -f "$tmp"
    echo "  removed CLAUDE.md block"
  fi
  echo "  left docs/, .claude/gsd-core/, and .claude/agents/ untouched"
  echo "done."
  exit 0
fi

echo "gsd-standards-guard: installing into $PROJECT"

# 1. Copy the skills into .claude/skills/ and the hook into .claude/hooks/.
mkdir -p "$PROJECT/.claude/skills" "$PROJECT/.claude/hooks"
cp -R "$SRC/skills/gsd-standards-guard"   "$PROJECT/.claude/skills/"
cp -R "$SRC/skills/write-adr"             "$PROJECT/.claude/skills/"
cp -R "$SRC/skills/standards-audit"       "$PROJECT/.claude/skills/"
cp -R "$SRC/skills/adr-index-audit"       "$PROJECT/.claude/skills/"
cp    "$SRC/hooks/gsd-standards-guard.js" "$PROJECT/.claude/hooks/gsd-standards-guard.js"
echo "  copied engine + skills → .claude/skills/, hook → .claude/hooks/"

# 2. Wire the PreToolUse hook in settings.json (add-or-replace, preserve the rest).
node "$SRC/templates/merge-settings.js" "$SETTINGS" "$HOOK_CMD"

# 3. Insert/replace the marked directive block in CLAUDE.md.
BLOCK="$(printf '%s\n' "$BEGIN"; cat "$SRC/templates/claude-md-block.md"; printf '%s\n' "$END")"
if [ -f "$CLAUDE_MD" ]; then
  if grep -qF "$BEGIN" "$CLAUDE_MD"; then
    tmp="$(mktemp)"; strip_block "$CLAUDE_MD" > "$tmp"; mv "$tmp" "$CLAUDE_MD"
  fi
  [ -s "$CLAUDE_MD" ] && printf '\n' >> "$CLAUDE_MD"
  printf '%s\n' "$BLOCK" >> "$CLAUDE_MD"
  echo "  updated CLAUDE.md block"
else
  printf '%s\n' "$BLOCK" > "$CLAUDE_MD"
  echo "  created CLAUDE.md with block"
fi

# 4. Seed docs contract if absent, then validate the index parses (fail loud).
mkdir -p "$PROJECT/docs/adr"
if [ ! -f "$PROJECT/docs/adr/index.yaml" ]; then
  cp "$SRC/templates/index.yaml" "$PROJECT/docs/adr/index.yaml"
  echo "  seeded docs/adr/index.yaml (author your rules — it starts empty)"
fi
if [ ! -f "$PROJECT/docs/ARCHITECTURE.md" ]; then
  cp "$SRC/templates/ARCHITECTURE.md" "$PROJECT/docs/ARCHITECTURE.md"
  echo "  seeded docs/ARCHITECTURE.md (authoring contract skeleton)"
fi
if [ ! -f "$PROJECT/docs/STANDARDS.md" ]; then
  cp "$SRC/templates/STANDARDS.md" "$PROJECT/docs/STANDARDS.md"
  echo "  seeded docs/STANDARDS.md (code-conventions skeleton)"
fi
if node "$PROJECT/.claude/skills/gsd-standards-guard/engine.js" --lint --project "$PROJECT" >/dev/null 2>&1; then
  echo "  index.yaml parses + lints ✓"
else
  # Lint is non-fatal (integrity gaps are the project's to fix), but a hard
  # parse failure means the hook would degrade — surface it either way.
  echo "  NOTE: index.yaml lint reported issues — run:"
  echo "        node .claude/skills/gsd-standards-guard/engine.js --lint --pretty"
fi

echo "done. Nothing under .claude/gsd-core/ or .claude/agents/ was touched."
