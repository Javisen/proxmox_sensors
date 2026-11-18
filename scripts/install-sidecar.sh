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

# Check the unit file written by this installer directly. A pipe into `grep -q`
# can fail under pipefail (SIGPIPE, exit 141) and miss an existing install.
if [[ -f "${SERVICE_PATH}" ]]; then
  echo "Existing Sidecar installation detected."
fi

echo
echo "Enter the Home Assistant IP address(es) allowed to access the Sidecar."
echo "Use commas to separate multiple addresses."
echo "Example: 192.168.1.50,192.168.1.60"

# The IP prompt needs an interactive stdin. With `curl ... | bash`, stdin is the
# script itself, so `read` would consume script lines instead of user input.
if [[ ! -t 0 ]]; then
  echo "Error: stdin is not a terminal. Run the installer interactively, e.g.:" >&2
  echo "  bash <(curl -fsSL ${REPO_RAW}/install-sidecar.sh)" >&2
  exit 1
fi

# Read existing ALLOWED_IPS from sidecar.conf as default (parsed, not sourced)
DEFAULT_IPS=""
if [[ -r "${CONFIG_PATH}" ]]; then
  DEFAULT_IPS="$(sed -n 's/^[[:space:]]*ALLOWED_IPS[[:space:]]*=[[:space:]]*//p' "${CONFIG_PATH}" \
    | tail -n1 | tr -d "\"' \r")"
  if [[ -n "${DEFAULT_IPS}" ]]; then
    echo "Current value from ${CONFIG_PATH}: ${DEFAULT_IPS}"
    echo "Press Enter to keep it, or edit the line."
  fi
fi

while true; do
  # -e: use readline, -i: pre-fill the editable input line with the default
  read -r -e -i "${DEFAULT_IPS}" -p "Allowed IP(s): " ALLOWED_INPUT
  # Empty input falls back to the default (safety net if -i has no effect)
  ALLOWED_INPUT="${ALLOWED_INPUT:-${DEFAULT_IPS}}"
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
