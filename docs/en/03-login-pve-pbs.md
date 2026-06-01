# 🔌 Step 3: Installing the Integration in Home Assistant

To visualize all data (temperatures, hardware sensors, disks, PBS, VMs and CTs), we will use the **Proxmox Extended Sensors** integration.

---

## 1. Installation via HACS

As this is a custom integration, you must first add it to HACS:

1. Go to **HACS → Integrations**  
2. Click the **three dots** (top right)  
3. Select **Custom repositories**  
4. Add this repository:  
   `https://github.com/Javisen/proxmox_sensors/`  
5. In **Category**, select `Integration`  
6. Install the integration and **restart Home Assistant**

---

## 2. Adding the integration

After restarting:

1. Go to **Settings → Devices & Services**  
2. Click **Add Integration**  
3. Search for **Proxmox Extended Sensors**

---

## 3. Connection configuration

### 🔹 Host
- **Local network:** `192.168.1.50`  
- **External access:** `proxmox.mydomain.com`  

> It is not necessary to include `http://` or `https://`. This is detected automatically.

---

### 🔹 Server type
- **PVE** → Proxmox Virtual Environment  
- **PBS** → Proxmox Backup Server  

---

### 🔹 Authentication method

- **Username + password** → PVE only  
- **API Token** → Recommended and mandatory for PBS  

---

## 🔐 Option A: Username and password (PVE only)

Fields:

- **User:** `user@realm`  
  - Example: `homeassistant@pve`  
- **Password:** user password  

> 💡 Since V3, the node is detected automatically. Manual entry is not required.

---

## 🔐 Option B: API Token (recommended)

Fields:

- **User:** `user@realm`  
- **Token ID:** only the name → `ha-token`  
- **Token Secret:** the secret generated in Proxmox  

> ⚠️ Do not use the format `user@pve!token`

---

## 🧠 Resource selection (PVE)

After connecting, the integration will automatically detect available resources.

You can select:

- Virtual machines (VMs)  
- Containers (CTs)  
- Physical disks  
- Storages  

> 💡 Select only what you need to keep Home Assistant clean and efficient.

---

## 🧭 Visual Installation Guide

Below is the complete process with screenshots:

<details>
  <summary>🪪 Server connection</summary>
  <p align="center">
    <img src="../../img/install/setup_pve_1.png" alt="Proxmox Connection" width="600">
  </p>
  <p align="center"><i>It is not necessary to include http/https.</i></p>
</details>

<details>
  <summary>🪪 Login with username and password (PVE)</summary>
  <p align="center">
    <img src="../../img/install/access_passw.png" alt="User Login" width="600">
  </p>
  <p align="center"><i>Use the correct realm (pam or pve).</i></p>
</details>

<details>
  <summary>🪪 Login with token (PVE and PBS)</summary>
  <p align="center">
    <img src="../../img/install/access_token.png" alt="Token Login" width="600">
  </p>
  <p align="center"><i>Enter only the token name in Token ID.</i></p>
</details>

<details>
  <summary>🧠 Node selection (V3)</summary>
  <p align="center">
    <img src="../../img/install/node_select.png" alt="Node Selection" width="600">
  </p>
  <p align="center"><i>Nodes are detected automatically and can be manually selected.</i></p>
</details>

<details>
  <summary>⚙️ Resource selection</summary>
  <p align="center">
    <img src="../../img/install/resources_select.png" alt="Resource Selection" width="600">
  </p>
</details>

---

## ⚠️ Note about PBS in managed environments

If you are using a **managed or multi-tenant PBS** (Tuxis, Hetzner, etc.):

- You will not have access to hardware sensors  
- You will not see temperatures or physical disks  
- There will be no node metrics  

This is normal because:

- You do not have access to the actual hardware  
- The provider restricts the system  
- Low-level permissions do not exist  

**Result:**  
Only limited datastore data will be displayed.

--- 