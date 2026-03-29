#!/bin/bash
set -e

APP_NAME="Paydirt"
EXECUTABLE="paydirt"
VERSION="${GITHUB_REF_NAME:-1.0.0}"
APP_DIR="${APP_NAME}.AppDir"

# Create AppDir structure
mkdir -p "${APP_DIR}/usr/bin"
mkdir -p "${APP_DIR}/usr/share/applications"
mkdir -p "${APP_DIR}/usr/share/icons/hicolor/256x256/apps"

# Copy executable
cp "dist/${EXECUTABLE}" "${APP_DIR}/usr/bin/"
chmod +x "${APP_DIR}/usr/bin/${EXECUTABLE}"

# Copy LICENSE
cp "LICENSE" "${APP_DIR}/"

# Create desktop file
cat > "${APP_DIR}/${APP_NAME}.desktop" <<EOF
[Desktop Entry]
Name=${APP_NAME}
Exec=${EXECUTABLE}
Icon=${APP_NAME}
Type=Application
Categories=Game;
EOF

# Create a simple icon (placeholder)
# If we have an icon file, copy it; otherwise create a dummy
ICON_FILE="${APP_DIR}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
if [ -f "packaging/linux/icon.png" ]; then
    cp "packaging/linux/icon.png" "${ICON_FILE}"
else
    # Create a 1x1 pixel PNG as placeholder (not great but works)
    convert -size 256x256 xc:blue "${ICON_FILE}" 2>/dev/null || \
    echo "No icon created (ImageMagick not installed)"
fi

# Download linuxdeploy if not present
if ! command -v linuxdeploy &> /dev/null; then
    wget -q https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
    chmod +x linuxdeploy-x86_64.AppImage
    sudo mv linuxdeploy-x86_64.AppImage /usr/local/bin/linuxdeploy
fi

# Run linuxdeploy to bundle and create AppImage
linuxdeploy --appdir "${APP_DIR}" --output appimage

# Move AppImage to dist
mv "${APP_NAME}-${VERSION}-x86_64.AppImage" "dist/"

echo "Created AppImage: dist/${APP_NAME}-${VERSION}-x86_64.AppImage"