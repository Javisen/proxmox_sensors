# 🌡️ Step 1: Hardware Sensors and Sidecar Setup

This guide prepares a Proxmox VE node so **Proxmox Extended Sensors V5** can read hardware information that is not exposed by the standard Proxmox API.

The hardware sidecar is used for data such as temperatures, memory information, mounted disks and SMART details. V5 also exposes a **Sidecar Status** diagnostic entity so Home Assistant can report whether these endpoints are healthy.

---

## 1. Install the required packages

Install the hardware and SMART utilities on the Proxmox host:

```bash
apt update && apt install lm-sensors smartmontools -y
```

- **lm-sensors** → CPU, motherboard, chipset, VRM, fan and other supported sensor data
- **smartmontools** → SMART information for HDD, SSD and supported NVMe devices

---

## 2. Detect hardware sensors

Run:

```bash
sensors-detect
```

Follow the wizard and enable the modules appropriate for your hardware.

> [!CAUTION]
> At the end of `sensors-detect`, read the prompt carefully. If it asks whether detected modules should be added to `/etc/modules`, make sure the required modules are saved so they also load after reboot.

---

## 3. Verify `lm-sensors`

Run:

```bash
sensors
```

You should see the sensors exposed by your hardware and kernel drivers.

If your Intel system uses `coretemp` and it has not loaded automatically, you can test it with:

```bash
modprobe coretemp
sensors
```

Do not force `coretemp` on systems that use a different hardware sensor driver.

---

## 4. Install the Sidecar

Run the following command on each PVE/PBS host where you want to install the Hardware Sidecar:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/scripts/install-sidecar.sh)
```

During installation, you will be prompted to enter the IP address(es) of your Home Assistant instance(s). Multiple IP addresses can be entered separated by commas.

Only the specified IP addresses will be allowed to access the Hardware Sidecar.

> **Note:** If the Sidecar is already installed, run the same command again to update the existing installation and configure the authorized Home Assistant IP addresses.

## 5. Check the Sidecar

Check the status of the Sidecar service:

```bash
systemctl status pve-sensors.service
```

The service should be shown as `active (running)`.
---

## 6. What V5 does when the sidecar fails

A temporary sidecar failure does not force all previously valid hardware entities to disappear immediately.

V5 preserves the last valid hardware data where possible and exposes one **Sidecar Status** sensor per PVE node with the state of:

- Memory
- Mounts
- Sensors
- SMART

Typical Sidecar Status states are:

- `ok`
- `degraded`
- `error`
- `unknown`

---

## ✔ Conclusion

Once `lm-sensors`, SMART support and `pve-sensors.service` are working, Home Assistant can obtain the additional hardware information supported by your Proxmox host.

Next: [02. Proxmox User and Permissions](02-proxmox-config.md)
