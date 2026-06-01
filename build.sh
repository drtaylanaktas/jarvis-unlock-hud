#!/bin/bash
# J.A.R.V.I.S. Unlock HUD — derleme & .app paketleme
# Konumdan bağımsız: script kendi dizinine göre çalışır.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
APP="$ROOT/JarvisHUD.app"
MACOS="$APP/Contents/MacOS"
RES="$APP/Contents/Resources"

command -v swiftc >/dev/null || { echo "HATA: swiftc bulunamadı. Xcode Command Line Tools kurun: xcode-select --install"; exit 1; }

echo "==> Eski paket temizleniyor"
rm -rf "$APP"
mkdir -p "$MACOS" "$RES"

echo "==> Swift derleniyor"
swiftc -O \
  -framework Cocoa -framework WebKit \
  "$ROOT/src/main.swift" \
  -o "$MACOS/JarvisHUD"

echo "==> HUD kopyalanıyor"
cp "$ROOT/hud/index.html" "$RES/index.html"
# Opsiyonel ses dosyaları (kullanıcının kendi yasal kopyaları) varsa pakete koy.
# Bunlar repoda YOKTUR; .gitignore ile dışlanır.
for f in "$ROOT"/hud/intro.* "$ROOT"/hud/voice.*; do
  [ -e "$f" ] && cp "$f" "$RES/" && echo "   + $(basename "$f")"
done

echo "==> Info.plist yazılıyor"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>JarvisHUD</string>
  <key>CFBundleDisplayName</key><string>J.A.R.V.I.S.</string>
  <key>CFBundleIdentifier</key><string>com.jarvis.hud</string>
  <key>CFBundleExecutable</key><string>JarvisHUD</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>LSMinimumSystemVersion</key><string>13.0</string>
  <key>LSUIElement</key><true/>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST

echo "==> Ad-hoc imza"
codesign --force --deep -s - "$APP" 2>/dev/null || echo "   (imza atlandı — yerel çalıştırma için sorun değil)"

echo "✅ Derleme tamam: $APP"
echo "   Demo: \"$MACOS/JarvisHUD\" --demo"
