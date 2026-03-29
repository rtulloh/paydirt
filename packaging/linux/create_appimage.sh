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
if ! head -c 2 linuxdeploy-x86_64.AppImage | grep -q $'\x7fELF'; then
    echo "Warning: Downloaded file may not be a valid ELF executable"
    cat linuxdeploy-x86_64.AppImage | head -c 200
fi

# Make it executable
chmod +x linuxdeploy-x86_64.AppImage

# Run linuxdeploy to bundle and create AppImage
echo "Running linuxdeploy..."
./linuxdeploy-x86_64.AppImage --appdir "${APP_DIR}" --desktop-file="${APP_DIR}/usr/share/applications/${APP_NAME}.desktop" --output appimage

# Move AppImage to dist
mv "${APP_NAME}-${VERSION}-x86_64.AppImage" "dist/"

echo "Created AppImage: dist/${APP_NAME}-${VERSION}-x86_64.AppImage"