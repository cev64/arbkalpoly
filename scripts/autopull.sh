#!/bin/bash
# Keeps this checkout in sync with origin/main. This is a mirror, not a
# workspace: it discards any local edits to tracked files so it always
# matches what's on GitHub. Run periodically via the LaunchAgent installed
# by install-autopull.sh, or by hand whenever you want the latest right now.
set -e
cd "$(dirname "$0")/.."

git fetch origin main
git reset --hard origin/main

if [ -d ".venv" ]; then
  source .venv/bin/activate
  pip install -q -r requirements.txt
fi
