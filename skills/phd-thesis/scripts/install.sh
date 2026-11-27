#!/bin/sh
# Link this skill into the global skill folders of Claude Code, Codex and Antigravity.
# Symlinks keep one source of truth in the thesis repository. Safe to rerun.
set -eu
SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
NAME=$(basename "$SKILL_DIR")
for target in "$HOME/.claude/skills" "$HOME/.codex/skills" "$HOME/.gemini/config/skills"; do
  mkdir -p "$target"
  link="$target/$NAME"
  if [ -e "$link" ] && [ ! -L "$link" ]; then
    echo "skip $link: exists and is not a symlink" >&2
    continue
  fi
  ln -sfn "$SKILL_DIR" "$link"
  echo "linked $link -> $SKILL_DIR"
done
