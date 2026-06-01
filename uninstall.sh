#!/bin/bash
# J.A.R.V.I.S. Unlock HUD — kaldırma (LaunchAgent'ı durdurur ve plist'i siler)
set -euo pipefail

UID_NUM="$(id -u)"

for LABEL in com.jarvis.hud com.jarvis.core; do
  launchctl bootout "gui/$UID_NUM/$LABEL" 2>/dev/null || true
  rm -f "$HOME/Library/LaunchAgents/$LABEL.plist"
done
echo "✅ Kaldırıldı (HUD + asistan çekirdeği). JarvisHUD.app ve repo dosyaları silinmedi — istersen klasörü elle silebilirsin."
