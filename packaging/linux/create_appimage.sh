#!/bin/bash
set -e

APP_NAME="Paydirt"
EXECUTABLE="paydirt"
VERSION="${GITHUB_REF_NAME:-1.0.0}"
APP_DIR="${APP_NAME}.AppDir"

# Create AppDir structure with all required icon directories
mkdir -p "${APP_DIR}/usr/bin"
mkdir -p "${APP_DIR}/usr/share/applications"
mkdir -p "${APP_DIR}/usr/share/icons/hicolor/16x16/apps"
mkdir -p "${APP_DIR}/usr/share/icons/hicolor/32x32/apps"
mkdir -p "${APP_DIR}/usr/share/icons/hicolor/64x64/apps"
mkdir -p "${APP_DIR}/usr/share/icons/hicolor/128x128/apps"
mkdir -p "${APP_DIR}/usr/share/icons/hicolor/256x256/apps"
mkdir -p "${APP_DIR}/usr/share/icons/hicolor/scalable/apps"
mkdir -p "${APP_DIR}/usr/share/pixmaps"

# Copy executable
cp "dist/${EXECUTABLE}" "${APP_DIR}/usr/bin/"
chmod +x "${APP_DIR}/usr/bin/${EXECUTABLE}"

# Copy LICENSE
cp "LICENSE" "${APP_DIR}/"

# Create desktop file in correct location
cat > "${APP_DIR}/usr/share/applications/${APP_NAME}.desktop" <<EOF
[Desktop Entry]
Name=${APP_NAME}
Comment=A Python simulation of the classic Paydirt football board game
Exec=${EXECUTABLE}
Icon=${APP_NAME}
Terminal=true
Type=Application
Categories=Game;Sports;
EOF

# Create a simple icon if not present
# Create icon in all required sizes
if [ -f "packaging/linux/icon.png" ]; then
    cp "packaging/linux/icon.png" "${APP_DIR}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
    cp "packaging/linux/icon.png" "${APP_DIR}/usr/share/pixmaps/${APP_NAME}.png"
else
    echo "Creating default icon..."
    # Create a simple 256x256 blue PNG using imagemagick convert
    convert -size 256x256 xc:'#1e40af' "${APP_DIR}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
    convert -size 256x256 xc:'#1e40af' "${APP_DIR}/usr/share/pixmaps/${APP_NAME}.png"
    # Create smaller sizes
    for size in 16 32 64 128; do
        convert -size ${size}x${size} xc:'#1e40af' "${APP_DIR}/usr/share/icons/hicolor/${size}x${size}/apps/${APP_NAME}.png"
    done
    # Create scalable version (just copy the 256)
    cp "${APP_DIR}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png" "${APP_DIR}/usr/share/icons/hicolor/scalable/apps/${APP_NAME}.png"
fi

# Verify icon exists
ICON_FILE="${APP_DIR}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
if [ ! -f "${ICON_FILE}" ]; then
    echo "Error: Failed to create icon"
    exit 1
fi

# Download linuxdeploy if not present
# Use the continuous build which should always be available
if [ ! -f "./linuxdeploy-x86_64.AppImage" ]; then
    echo "Downloading linuxdeploy..."
    curl -fSL "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage" -o linuxdeploy-x86_64.AppImage || {
        echo "Failed to download linuxdeploy, trying alternative URL..."
        curl -fSL "https://github.com/linuxdeploy/linuxdeploy/releases/latest/download/linuxdeploy-x86_64.AppImage" -o linuxdeploy-x86_64.AppImage
    }
    chmod +x linuxdeploy-x86_64.AppImage
fi

# Verify the file is valid
file linuxdeploy-x86_64.AppImage || true

# Make it executable
chmod +x linuxdeploy-x86_64.AppImage

# Run linuxdeploy to bundle and create AppImage
echo "Running linuxdeploy..."
./linuxdeploy-x86_64.AppImage --appdir "${APP_DIR}" --desktop-file="${APP_DIR}/usr/share/applications/${APP_NAME}.desktop" --output appimage

# Move AppImage to dist
mv "${APP_NAME}-${VERSION}-x86_64.AppImage" "dist/"

echo "Created AppImage: dist/${APP_NAME}-${VERSION}-x86_64.AppImage"