#!/usr/bin/env bash
# Install the DEA skill folder. Usage:
#   ./install.sh                 -> ~/.claude/skills/dea   (Claude Code, all projects)
#   ./install.sh --project DIR   -> DIR/.claude/skills/dea
#   ./install.sh --dest PATH     -> PATH/dea               (any agent's skills directory)
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dest="${HOME}/.claude/skills"
while [ $# -gt 0 ]; do
  case "$1" in
    --project) dest="${2:?--project needs a directory}/.claude/skills"; shift 2 ;;
    --dest) dest="${2:?--dest needs a path}"; shift 2 ;;
    -h|--help) sed -n '2,6p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
done
mkdir -p "$dest"
rm -rf "$dest/dea"
cp -r "$here/dea" "$dest/dea"
echo "Installed DEA to $dest/dea"
echo "Optional (best capture): npm i -D playwright && npx playwright install chromium"
