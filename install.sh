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

echo "==> Yükleniyor (HUD ajanı)"
launchctl bootout "gui/$UID_NUM/$LABEL" 2>/dev/null || true
sleep 1
launchctl bootstrap "gui/$UID_NUM" "$PLIST"

# ---- Optional: conversational assistant core (Python) -------------------
CORE="$ROOT/core"
if [ -d "$CORE" ] && [ "${JARVIS_SKIP_CORE:-0}" != "1" ]; then
  echo "==> Asistan çekirdeği (Python) kuruluyor"
  PY="$(command -v python3.12 || command -v python3)"
  if [ ! -d "$CORE/.venv" ]; then
    "$PY" -m venv "$CORE/.venv"
  fi
  "$CORE/.venv/bin/python" -m pip install --quiet --upgrade pip
  "$CORE/.venv/bin/python" -m pip install --quiet -r "$CORE/requirements.txt"

  CORE_PLIST="$HOME/Library/LaunchAgents/com.jarvis.core.plist"
  echo "==> LaunchAgent yazılıyor: $CORE_PLIST"
  cat > "$CORE_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.jarvis.core</string>
  <key>ProgramArguments</key>
  <array>
    <string>$CORE/.venv/bin/python</string>
    <string>$CORE/jarvis.py</string>
  </array>
  <key>WorkingDirectory</key><string>$CORE</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ProcessType</key><string>Interactive</string>
  <key>StandardOutPath</key><string>$CORE/jarvis-core.log</string>
  <key>StandardErrorPath</key><string>$CORE/jarvis-core.log</string>
</dict>
</plist>
PLIST
  launchctl bootout "gui/$UID_NUM/com.jarvis.core" 2>/dev/null || true
  sleep 1
  launchctl bootstrap "gui/$UID_NUM" "$CORE_PLIST" || true

  echo
  echo "ℹ️  Asistan için gerekli (bir kez):"
  echo "    1) core/.env doldur (ANTHROPIC_API_KEY, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID)"
  echo "    2) core/config.toml ayarla (ses, konum, dil)"
  echo "    3) Google: core/credentials.json koy + '$CORE/.venv/bin/python $CORE/google_auth.py'"
  echo "    4) İLK push-to-talk'ta macOS Mikrofon izni isteyecek — izin ver."
fi

echo
echo "✅ Kuruldu."
echo "   • Kilit açılışı: ekranı kilitleyip açın (sinematik HUD)."
echo "   • Asistan: ⌥⌘J — konuşmak için dokun, bitince tekrar dokun."
echo "   • HUD demo: \"$APP_BIN\" --demo"
