# 🚀 Step 1: Sensor Installation and Configuration

This guide explains how to prepare the Proxmox node to expose hardware data and allow Home Assistant to obtain temperatures, physical sensors, and SMART disk attributes.

This data is used by the integration to provide **advanced monitoring and System Insight (V3/V4)**.

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

The official Proxmox API does not expose all hardware sensors.
Therefore, this integration uses a small service that acts as a bridge.

5.1. **Download and install the script**
Run these commands on your Proxmox server terminal:

```bash
wget https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/scripts/pve-sensors-api.py -O /usr/local/bin/pve-sensors-api.py
chmod +x /usr/local/bin/pve-sensors-api.py
```

5.2. **Configure as a system service**

Create the service file:

```bash
cat <<EOF > /etc/systemd/system/pve-sensors.service
[Unit]
Description=PVE Sensors API (User Mode)
After=network.target

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/pve-sensors-api.py
Restart=always
RestartSec=10s

NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=full

[Install]
WantedBy=default.target
EOF

```

5.3. **Activation**

```bash
systemctl daemon-reload
systemctl enable --now pve-sensors.service
```

5.4. **Final verification**
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
