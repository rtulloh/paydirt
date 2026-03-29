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
ICON_FILE="${APP_DIR}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
if [ -f "packaging/linux/icon.png" ]; then
    cp "packaging/linux/icon.png" "${ICON_FILE}"
elif ! [ -f "${ICON_FILE}" ]; then
    # Create a simple 256x256 blue PNG using Python if available
    python3 -c "
from PIL import Image
img = Image.new('RGB', (256, 256), color='#1e40af')
img.save('${ICON_FILE}')
" 2>/dev/null || echo "Warning: Could not create icon (PIL not installed)"
fi

# Download linuxdeploy if not present (use specific version, not continuous)
# Use no-fuse version to avoid FUSE dependency issues
if [ ! -f "./linuxdeploy-no-fuse-x86_64.AppImage" ]; then
    echo "Downloading linuxdeploy (no-fuse version)..."
    curl -sSL https://github.com/linuxdeploy/linuxdeploy/releases/download/2024-11-10/linuxdeploy-no-fuse-x86_64.AppImage -o linuxdeploy-no-fuse-x86_64.AppImage
    chmod +x linuxdeploy-no-fuse-x86_64.AppImage
fi

# Make it executable
chmod +x linuxdeploy-no-fuse-x86_64.AppImage

# Run linuxdeploy to bundle and create AppImage
# Use --install-deps to bundle libraries
echo "Running linuxdeploy..."
./linuxdeploy-no-fuse-x86_64.AppImage --appdir "${APP_DIR}" --desktop-file="${APP_DIR}/usr/share/applications/${APP_NAME}.desktop" --output appimage --install-deps

# Move AppImage to dist
mv "${APP_NAME}-${VERSION}-x86_64.AppImage" "dist/"

echo "Created AppImage: dist/${APP_NAME}-${VERSION}-x86_64.AppImage"