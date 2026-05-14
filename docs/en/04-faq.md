# ❓ FAQ — Frequently Asked Questions

Here you will find the most common problems when using **Proxmox Extended Sensors** and their solutions.

---

# 🔐 Connection problems

## ❌ I can't log in

### ✔ Use only IP or domain
Correct:
- `192.168.1.10`  
- `pve.mydomain.com`

Incorrect:
- `http://...`
- `https://...`

---

### ✔ Do not include the port
The integration detects it automatically.

---

### ✔ Check permissions

- PVE → `PVEAdmin`  
- PBS → `Administrator`  
- They must be assigned at `/`

---

### ✔ The Token must be active
In Proxmox → API Tokens → **Enabled: Yes**

---

## ❌ “Permission denied” with Token

### ✔ Permissions at `/`
They should not be assigned to a node, but to the root.

### ✔ User without permissions
The parent user must have a valid role.

---

# 🌡️ Sensors and hardware

## ❌ Temperatures do not appear

Make sure to:


```bash
apt install lm-sensors
sensors-detect
modprobe coretemp
```

And have the service active.

---

## ❌ Disks or SMART do not appear

- The disk must support it  
- NVMe in VMs → not available  
- Some controllers do not expose data  

---

## ❌ VMs or CTs do not appear

- Check permissions (`PVEAdmin`)  
- In a cluster, use the main node  

---

## 🗄️ PBS (Backup Server)

### ❌ I don't see datastore data

### 🔒 Managed PBS (Tuxis, Hetzner…)

You will not have access to:

- Disk usage  
- Deduplication  
- Temperature  
- CPU/RAM  
- SMART  

👉 This is a provider limitation, not an integration issue.

---

## 🧠 System Insight (V3/V4)

### ❓ What is Node Score?

It is a global evaluation of the node's status based on:

- CPU  
- Load  
- IO Wait  

It allows you to quickly detect if a node is under load.

---

### ❓ What does “Node Stress” or “Overload” mean?

It indicates that the system is under pressure:

- High CPU  
- High load  
- Disk saturation  

👉 Useful for automations or alerts.

---

## 🔄 Performance

### ❓ The integration takes a long time to update

This is normal.

The integration uses an optimized system to:

- Reduce load on Proxmox  
- Avoid saturating the API  

Default interval: ~10 seconds.

---

## 🧩 General use

### ❓ Can I use multiple servers?

Yes.  
You can add multiple instances (PVE/PBS).

---

### 🔒 Is it safe?

Yes:

- Uses API Tokens  
- Does not execute remote commands  
- Does not modify configuration  
- Does not open ports  

---

## 🧹 Remove old sensors

1. Delete the integration  
2. Restart Home Assistant  
3. Add it again  

---

## 🧾 Checklist before opening an Issue

Before reporting a problem:

- ✔ Can you access Proxmox from the browser?  
- ✔ Do you use only IP or domain?  
- ✔ Is the Token active?  
- ✔ Permissions at `/`?  
- ✔ Is lm-sensors installed?  
- ✔ Did you restart Home Assistant?  
- ✔ Did you check logs?  

---

## 🚫 Known limitations

### 🔒 Managed PBS

No access to internal metrics (hardware, datastore, etc.)

---

### 🧊 Sensors in VMs

There are no real sensors in virtual machines.

---

### 📦 Disks without SMART

Some disks/controllers do not expose data.

---

### 🔐 Incorrectly assigned permissions

If they are not at `/`, the API fails.

---

### 🕒 Update intervals

There is an intentional delay to avoid load.

---

### 🧩 Proxmox Cluster

Connect to the main node.

---

### 🌐 SSL certificates

Self-signed certificates are accepted.

---