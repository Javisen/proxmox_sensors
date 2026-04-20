# 🚀 Step 1: Sensor Installation and Configuration

This guide explains how to prepare the Proxmox node to expose hardware data and allow Home Assistant to obtain temperatures, physical sensors, and SMART disk attributes.

This data is used by the integration to provide **advanced monitoring and System Insight (V3)**.

---

## 1. Installing Dependencies

To enable all hardware and SMART sensors, install:

- **lm-sensors** → CPU, motherboard, chipset, VRM, fans  
- **smartmontools** → SMART information for HDD, SSD and NVMe  

apt update && apt install lm-sensors smartmontools -y

## 2. Hardware Detection

* **Run the wizard:**

```bash
sensors-detect

```

Answer **YES** (or press Enter) to all questions.

When finished, the system will detect the necessary modules (for example: coretemp on Intel CPUs).

## 3. Module Persistence

At the end of the process, you will see this prompt:

Do you want to add these lines automatically to /etc/modules? (yes/NO)

> [!CAUTION]
> **You must manually type `yes` and press Enter.** If you only press Enter, `NO` will be selected by default and sensors will not load after reboot.

## 4. Immediate Verification

To activate sensors without rebooting:

```bash
modprobe coretemp
sensors

```

## 🚀 Step 5: Installing the Sensor Server (API Bridge)

The official Proxmox API does not expose all hardware sensors. Therefore, this integration uses a small service that acts as a bridge.

To avoid running scripts as root, we will create a dedicated `homeassistant` user and run the API as a user-level service.

### 5.1. Create User and Enable Persistence
Run these commands as **root** to create the user and ensure their services start at boot:

```bash
# Create the user
adduser homeassistant

# Ensure the service starts at boot and stays running after logout
loginctl enable-linger homeassistant
```

### 5.2. Download and Setup (as homeassistant user)
Switch to the new user and set up the script:

```bash
# Switch to the user session
su - homeassistant

# Create necessary folders
mkdir -p ~/.local/bin
mkdir -p ~/.config/systemd/user/

# Download the script
wget https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/scripts/pve-sensors-api.py -O ~/.local/bin/pve-sensors-api.py
chmod +x ~/.local/bin/pve-sensors-api.py
```

### 5.3. Create the User Service
While still logged in as the **homeassistant** user, create the service file:

```bash
cat <<EOF > ~/.config/systemd/user/pve-sensors.service
[Unit]
Description=PVE Sensors API (User Mode)
After=network.target

[Service]
ExecStart=/usr/bin/python3 %h/.local/bin/pve-sensors-api.py
Restart=always
RestartSec=10s

[Install]
WantedBy=default.target
EOF
```

### 5.4. Activation
Since you are logged in via `su`, you must export the runtime path to avoid "Operation not permitted" errors, then enable the service:

```bash
# Fix the D-Bus connection for this session
export XDG_RUNTIME_DIR=/run/user/$(id -u)

# Load, Enable, and Start
systemctl --user daemon-reload
systemctl --user enable pve-sensors.service
systemctl --user start pve-sensors.service
```

### 5.5. Final verification
Check the status of the service:
```bash
systemctl --user status pve-sensors.service
```

Open in your browser:

```
http://YOUR_PROXMOX_IP:9000/sensors
```

If a JSON with temperatures and sensors appears, the service is working correctly.

## ✔ Conclusion

Once:
- sensors returns data correctly
- The pve-sensors.service is active

Home Assistant will be able to obtain all hardware data automatically, without additional configuration.
