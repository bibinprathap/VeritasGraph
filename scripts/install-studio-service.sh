#!/bin/bash
# Install / enable the VeritasGraph Studio auto-tunnel systemd service.
# Run with: sudo bash scripts/install-studio-service.sh
#
# After install the studio launches on every boot, opens a Cloudflare
# tunnel, and pushes the public URL to docs/studio/index.html on GitHub.
# Stable demo link: https://bibinprathap.github.io/VeritasGraph/studio/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_SRC="$SCRIPT_DIR/veritasgraph-studio.service"
UNIT_DST="/etc/systemd/system/veritasgraph-studio.service"
LAUNCH="$SCRIPT_DIR/start-studio-with-tunnel.sh"

if [ "$(id -u)" -ne 0 ]; then
    echo "Please run as root: sudo bash $0"
    exit 1
fi

if [ ! -f "$UNIT_SRC" ]; then
    echo "ERROR: $UNIT_SRC not found."
    exit 1
fi

chmod +x "$LAUNCH"

echo "Installing systemd unit -> $UNIT_DST"
cp "$UNIT_SRC" "$UNIT_DST"

systemctl daemon-reload
systemctl enable veritasgraph-studio.service
systemctl restart veritasgraph-studio.service

echo
echo "✅ Installed and started."
echo "   Status : systemctl status veritasgraph-studio.service"
echo "   Logs   : journalctl -u veritasgraph-studio.service -f"
echo "            tail -f /home/sijo/VeritasGraph/studio-tunnel.log"
echo "   Demo   : https://bibinprathap.github.io/VeritasGraph/studio/"
