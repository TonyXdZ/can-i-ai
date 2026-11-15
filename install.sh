#!/usr/bin/env bash
# Installs "Can I Run AI?" for the current user on Linux (no sudo needed).
#   curl -fsSL https://raw.githubusercontent.com/TonyXdZ/can-i-ai/main/install.sh | bash
set -euo pipefail

REPO="${CIRA_REPO:-TonyXdZ/can-i-ai}"
URL="${CIRA_URL:-https://github.com/${REPO}/releases/latest/download/can-i-run-ai-linux}"
BIN_DIR="${HOME}/.local/bin"
APP_DIR="${HOME}/.local/share/applications"

mkdir -p "$BIN_DIR" "$APP_DIR"
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

echo "Downloading Can I Run AI?..."
if command -v curl >/dev/null 2>&1; then
  curl -fsSL "$URL" -o "$tmp"
elif command -v wget >/dev/null 2>&1; then
  wget -qO "$tmp" "$URL"
else
  echo "Please install curl or wget and try again." >&2
  exit 1
fi

chmod +x "$tmp"
mv "$tmp" "${BIN_DIR}/can-i-run-ai"

# App-menu icon (optional: a failed download just means no icon)
ICON_DIR="${HOME}/.local/share/icons"
ICON_FILE="${ICON_DIR}/can-i-run-ai.png"
ICON_URL="${CIRA_ICON_URL:-https://raw.githubusercontent.com/${REPO}/main/icon.png}"
mkdir -p "$ICON_DIR"
if command -v curl >/dev/null 2>&1; then
  curl -fsSL "$ICON_URL" -o "$ICON_FILE" 2>/dev/null || rm -f "$ICON_FILE"
else
  wget -qO "$ICON_FILE" "$ICON_URL" 2>/dev/null || rm -f "$ICON_FILE"
fi

cat > "${APP_DIR}/can-i-run-ai.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Can I Run AI?
Comment=Check which AI models your computer can run
Exec=${BIN_DIR}/can-i-run-ai
Icon=${ICON_FILE}
Terminal=false
Categories=Utility;System;
EOF

echo "Installed to ${BIN_DIR}/can-i-run-ai"
echo "Find it in your app menu, or run: can-i-run-ai"
case ":${PATH}:" in
  *":${BIN_DIR}:"*) ;;
  *) echo "Note: add ${BIN_DIR} to your PATH to run it by name from a terminal." ;;
esac
echo "To uninstall: rm ${BIN_DIR}/can-i-run-ai ${APP_DIR}/can-i-run-ai.desktop ${ICON_FILE}"
