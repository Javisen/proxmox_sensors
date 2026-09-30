#!/usr/bin/env bash
set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/scripts"
SIDECAR_PATH="/usr/local/bin/pve-sensors-api.py"
CONFIG_DIR="/etc/proxmox-sensors"
CONFIG_PATH="${CONFIG_DIR}/sidecar.conf"
SERVICE_PATH="/etc/systemd/system/pve-sensors.service"

if [[ ${EUID} -ne 0 ]]; then
  echo "This installer must be run as root."
  exit 1
fi

echo "Proxmox Extended Sensors - Hardware Sidecar installer"
echo

if systemctl list-unit-files | grep -q '^pve-sensors.service'; then
  echo "Existing Sidecar installation detected."
fi

echo
echo "Enter the Home Assistant IP address(es) allowed to access the Sidecar."
echo "Use commas to separate multiple addresses."
echo "Example: 192.168.1.50,192.168.1.60"

while true; do
  read -r -p "Allowed IP(s): " ALLOWED_INPUT
  if python3 - "${ALLOWED_INPUT}" <<'PY'
import ipaddress
import sys

raw = sys.argv[1]
items = [item.strip() for item in raw.split(",") if item.strip()]
if not items:
    raise SystemExit(1)
for item in items:
    ipaddress.ip_address(item)
PY
  then
    break
  fi
  echo "Invalid IP list. Please try again."
done

install -d -m 0755 "${CONFIG_DIR}"
printf 'ALLOWED_IPS=%s\n' "${ALLOWED_INPUT// /}" > "${CONFIG_PATH}"
chmod 0644 "${CONFIG_PATH}"

echo "Downloading Sidecar..."
curl -fsSL "${REPO_RAW}/pve-sensors-api.py" -o "${SIDECAR_PATH}"
chmod 0755 "${SIDECAR_PATH}"

cat > "${SERVICE_PATH}" <<'EOF'
[Unit]
Description=PVE Sensors API
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/bin/pve-sensors-api.py
Restart=always
RestartSec=10s

NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=full

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable pve-sensors.service >/dev/null
systemctl restart pve-sensors.service

sleep 1
if systemctl is-active --quiet pve-sensors.service; then
  echo
  echo "Sidecar installed/updated successfully."
  echo "Allowed IP(s): ${ALLOWED_INPUT// /}"
  echo "Listening port: 9000"
else
  echo
  echo "Sidecar failed to start."
  systemctl --no-pager -l status pve-sensors.service || true
  exit 1
fi
