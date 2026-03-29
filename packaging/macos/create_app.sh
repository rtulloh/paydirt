#!/bin/bash
set -e

# Variables
APP_NAME="Paydirt"
APP_BUNDLE="${APP_NAME}.app"
EXECUTABLE="paydirt"
VERSION="${GITHUB_REF_NAME:-1.0.0}"

# Create .app bundle structure
mkdir -p "${APP_BUNDLE}/Contents/MacOS"
mkdir -p "${APP_BUNDLE}/Contents/Resources"

# Copy executable
cp "dist/${EXECUTABLE}" "${APP_BUNDLE}/Contents/MacOS/"
chmod +x "${APP_BUNDLE}/Contents/MacOS/${EXECUTABLE}"

# Copy LICENSE
cp "LICENSE" "${APP_BUNDLE}/Contents/Resources/"

# Create Info.plist
cat > "${APP_BUNDLE}/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleDisplayName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIdentifier</key>
    <string>com.paydirtfan.paydirt</string>
    <key>CFBundleVersion</key>
    <string>${VERSION}</string>
    <key>CFBundleShortVersionString</key>
    <string>${VERSION}</string>
    <key>CFBundleExecutable</key>
    <string>${EXECUTABLE}</string>
    <key>CFBundleIconFile</key>
    <string></string>
    <key>LSMinimumSystemVersion</key>
    <string>10.12</string>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © 2026 Paydirt Fan. All rights reserved.</string>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
</dict>
</plist>
EOF

# Create DMG using create-dmg
# Install create-dmg if not present
if ! command -v create-dmg &> /dev/null; then
    brew install create-dmg
fi

# Create a temporary directory for DMG contents
DMG_TEMP=$(mktemp -d)
cp -r "${APP_BUNDLE}" "${DMG_TEMP}/"
cp "LICENSE" "${DMG_TEMP}/"

# Create DMG (strip 'v' prefix from version if present)
VERSION_STRIPVED=$(echo "${VERSION}" | sed 's/^v//')
ARCH=$(uname -m)
DMG_NAME="${APP_NAME}-${VERSION_STRIPVED}-${ARCH}.dmg"
create-dmg \
  --volname "${APP_NAME} ${VERSION_STRIPVED}" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "${APP_NAME}.app" 200 190 \
  --hide-extension "${APP_NAME}.app" \
  --app-drop-link 600 185 \
  --no-internet-enable \
  "dist/${DMG_NAME}" \
  "${DMG_TEMP}"

# Clean up
rm -rf "${DMG_TEMP}"
echo "Created DMG: dist/${APP_NAME}-${VERSION}.dmg"