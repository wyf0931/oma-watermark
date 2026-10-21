#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
VERSION="${OMA_APP_VERSION:-${VERSION:-0.1.3}}"
export MACOSX_DEPLOYMENT_TARGET="${MACOSX_DEPLOYMENT_TARGET:-12.0}"

if [ ! -f "models/inpainting_lama_2025jan.onnx" ]; then
  uv run oma-watermark-download-model
fi

npm ci
npm run build:css

rm -rf build dist
uv sync --extra desktop
OMA_APP_VERSION="$VERSION" uv run pyinstaller packaging/oma-watermark.spec --noconfirm --clean

APP="dist/Watermark Remover.app"
if [ ! -d "$APP" ]; then
  echo "Error: $APP was not created" >&2
  exit 1
fi

# Ad-hoc signing lets the app launch on the build machine. A Developer ID
# certificate is still required for a warning-free Gatekeeper experience.
codesign --force --deep --sign - "$APP"

rm -rf dist/dmg
mkdir -p dist/dmg
cp -R "$APP" dist/dmg/
ln -s /Applications dist/dmg/Applications

ARCH="$(uname -m)"
DMG="dist/Watermark-Remover-${VERSION}-${ARCH}.dmg"
hdiutil create \
  -volname "Watermark Remover" \
  -srcfolder dist/dmg \
  -ov \
  -format UDZO \
  "$DMG"
rm -rf dist/dmg

echo "Built $DMG"
