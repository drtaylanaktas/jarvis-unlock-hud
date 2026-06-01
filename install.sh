#!/bin/bash
# J.A.R.V.I.S. Unlock HUD — kurulum
# Derler ve ekran kilidi açılışında otomatik çalışması için LaunchAgent yükler.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
APP_BIN="$ROOT/JarvisHUD.app/Contents/MacOS/JarvisHUD"
PLIST="$HOME/Library/LaunchAgents/com.jarvis.hud.plist"
LABEL="com.jarvis.hud"
UID_NUM="$(id -u)"

echo "==> Derleniyor"
bash "$ROOT/build.sh"

echo "==> LaunchAgent yazılıyor: $PLIST"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$APP_BIN</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>ProcessType</key>
  <string>Interactive</string>
  <key>StandardOutPath</key>
  <string>$ROOT/jarvis.log</string>
  <key>StandardErrorPath</key>
  <string>$ROOT/jarvis.log</string>
</dict>
</plist>
PLIST

echo "==> Yükleniyor"
launchctl bootout "gui/$UID_NUM/$LABEL" 2>/dev/null || true
sleep 1
launchctl bootstrap "gui/$UID_NUM" "$PLIST"

echo "✅ Kuruldu. Ekran kilidini açtığınızda J.A.R.V.I.S. devreye girer."
echo "   Hemen denemek için: \"$APP_BIN\" --demo"
