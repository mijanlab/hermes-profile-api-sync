#!/usr/bin/env bash
set -euo pipefail
REPO_RAW="https://raw.githubusercontent.com/mijanlab/hermes-profile-api-sync/main"
DEST_SCRIPT="$HOME/.hermes/scripts/sync-ai.py"
DEST_WATCHER="$HOME/.hermes/scripts/sync-ai-watch.py"
BIN_PATH="/usr/local/bin/sync-ai"
SERVICE_PATH="/etc/systemd/system/sync-ai-watch.service"

mkdir -p "$(dirname "$DEST_SCRIPT")"

fetch() {
  if [ -f "./$1" ]; then cp "./$1" "$2"; else curl -fsSL "$REPO_RAW/$1" -o "$2"; fi
}
fetch sync-ai.py "$DEST_SCRIPT"
fetch sync-ai-watch.py "$DEST_WATCHER"
chmod +x "$DEST_SCRIPT" "$DEST_WATCHER"

cat > "$BIN_PATH" << EOF
#!/usr/bin/env bash
exec python3 "$DEST_SCRIPT" "\$@"
EOF
chmod +x "$BIN_PATH"

echo "Installed sync-ai -> $DEST_SCRIPT"

echo "Linking all current profiles..."
python3 "$DEST_SCRIPT" install

if command -v systemctl >/dev/null 2>&1 && [ "$(id -u)" = "0" ]; then
  TMP_UNIT="$(mktemp)"
  fetch sync-ai-watch.service "$TMP_UNIT"
  sed -e "s|__SCRIPT_PATH__|$DEST_WATCHER|" -e "s|__SERVICE_USER__|root|" "$TMP_UNIT" > "$SERVICE_PATH"
  rm -f "$TMP_UNIT"
  systemctl daemon-reload
  systemctl enable --now sync-ai-watch.service
  echo "sync-ai-watch installed and running: new profiles auto-link with zero commands."
elif command -v systemctl >/dev/null 2>&1; then
  echo "Not running as root: skipped the auto-link watcher service."
  echo "Re-run this installer as root for fully automatic new-profile linking,"
  echo "or run 'sync-ai install' manually after creating a new profile."
else
  echo "systemctl not found: run 'sync-ai install' after creating new profiles."
fi

echo
echo "Done. Logging in or out of any AI provider in ANY profile now applies"
echo "instantly to every other profile — including ones created later."
