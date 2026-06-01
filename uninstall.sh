#!/bin/bash
# J.A.R.V.I.S. Unlock HUD — kaldırma (LaunchAgent'ı durdurur ve plist'i siler)
set -euo pipefail

LABEL="com.jarvis.hud"
PLIST="$HOME/Library/LaunchAgents/com.jarvis.hud.plist"
UID_NUM="$(id -u)"

launchctl bootout "gui/$UID_NUM/$LABEL" 2>/dev/null || true
rm -f "$PLIST"
echo "✅ Kaldırıldı. (JarvisHUD.app ve repo dosyaları silinmedi — istersen klasörü elle silebilirsin.)"
