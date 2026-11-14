#!/usr/bin/env bash
# Make the competitor fleet callable: symlink each agent definition into
# ~/.claude/agents/ so Claude Code registers them as subagents (usable standalone
# AND by competitor_workflow.js via agentType). The repo stays the source of truth.
# Idempotent and reversible — re-run any time; undo with the rm line printed at the end.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$HOME/.claude/agents"
mkdir -p "$DEST"

linked=0
for f in "$SKILL_DIR"/agents/*.md; do
  base="$(basename "$f")"            # e.g. matrix-builder.md
  target="$DEST/competitor-$base"    # -> competitor-matrix-builder.md (namespaced, no clobber)
  ln -sf "$f" "$target"
  echo "linked  competitor-$base  ->  $f"
  linked=$((linked + 1))
done

echo ""
echo "Done: $linked agent(s) linked into $DEST"
echo "Undo: rm $DEST/competitor-*.md"
