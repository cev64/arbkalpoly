#!/bin/bash
# Installs a macOS LaunchAgent that runs autopull.sh every 5 minutes, so this
# checkout stays in sync with origin/main in the background - no terminal,
# no cron, survives reboots. Run this once from wherever you want the repo
# to live (e.g. after cloning it to ~/Desktop/arbkalpoly).
set -e
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLIST="$HOME/Library/LaunchAgents/com.arbkalpoly.autopull.plist"

mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.arbkalpoly.autopull</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$REPO_DIR/scripts/autopull.sh</string>
  </array>
  <key>StartInterval</key>
  <integer>300</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$REPO_DIR/scripts/autopull.log</string>
  <key>StandardErrorPath</key>
  <string>$REPO_DIR/scripts/autopull.log</string>
</dict>
</plist>
PLIST_EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load -w "$PLIST"

echo "Installed. $REPO_DIR will sync with origin/main every 5 minutes."
echo "Logs: $REPO_DIR/scripts/autopull.log"
echo "To stop syncing: launchctl unload $PLIST"
