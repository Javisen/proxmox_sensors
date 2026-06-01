<p align="center">
  <img src="https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/img/logo_int_v4.png" alt="Proxmox Extended Sensors Logo" width="600"/>
</p>

> **The most robust and detailed monitoring & control system for Proxmox VE & PBS in Home Assistant.**

# 🚀 Proxmox Extended Sensors (v4)

## 🚀 Introduction

**Proxmox Extended Sensors v4** is a complete evolution of the original integration, re-engineered from the ground up to provide industrial-grade stability and the deepest system insights available for Home Assistant.

Building on the breakthrough of V3, where the focus shifted from raw metrics to meaningful, interpreted information, V4 continues to deliver high-value sensors like Node Score and Node Status (Excellent/Warning). These allow you to understand your system's health at a single glance—perfect for smart automations and clean dashboards—without needing to analyze individual sensors one by one.

To support this intelligence, V4 introduces a high-performance asynchronous architecture, utilizing semaphores and optimized coordinators. This ensures your Home Assistant remains responsive and stable, even when managing large clusters or complex hardware. It is no longer just a set of sensors; it is a professional management bridge for your homelab.

---

## 🔍 V4 Key Capabilities

*   **[NEW] Cluster-Wide Monitoring:** Centralized sensors for the entire Proxmox cluster state (backups, failed tasks, nodes online).
*   **[NEW] Advanced Mounted Disks:** Real-time detection of local disks, CIFS, and NFS mounts with detailed usage attributes.
*   **Deep Hardware Insight:** Specialized support for NVMe (SMART/Temp) and CPU thermal zones (Intel/AMD/ACPI).
*   **high-stability architecture:** Asynchronous core with concurrency control (Semaphores) to prevent API saturation.
*   **Secure Authentication:** Mandatory API Token support for PBS and flexible Auth for PVE.
*   **Intelligent Backups:** Fully integrated services for single or massive backups, compatible with PBS deduplication.

---

## 🧠 Why V4?
The v4 upgrade shifts the focus toward **Infrastructure Reliability**:

*   **Zero-Lag Performance:** Correct `async/await` implementation avoids event loop blocking.
*   **Entity Persistence:** Re-designed Unique IDs ensure sensors survive reboots and cluster changes.
*   **Hardware Diversity:** Clean naming logic that adapts to heterogeneous hardware without duplicating entities.
*   **Smarter Automations:** High-precision attributes for disk pressure (IO Wait) and thermal margins.

---

## 📚 Documentation & Guides

**Select your language to start the installation and configuration:**

[![English](https://img.shields.io/badge/ENGLISH-blue?style=for-the-badge&logo=translate&logoColor=white)](docs/en/README.md)
[![Español](https://img.shields.io/badge/ESPA%C3%91OL-orange?style=for-the-badge&logo=translate&logoColor=white)](docs/es/README.md)
[![Italiano](https://img.shields.io/badge/ITALIANO-green?style=for-the-badge&logo=translate&logoColor=white)](docs/it/README.md)
[![Français](https://img.shields.io/badge/FRAN%C3%87AIS-blue?style=for-the-badge&logo=translate&logoColor=white)](docs/fr/README.md)
[![Deutsch](https://img.shields.io/badge/DEUTSCH-red?style=for-the-badge&logo=translate&logoColor=white)](docs/de/README.md)
[![Nederlands](https://img.shields.io/badge/NEDERLANDS-orange?style=for-the-badge&logo=translate&logoColor=white)](docs/nl/README.md)
[![Português](https://img.shields.io/badge/PORTUGU%C3%8AS-green?style=for-the-badge&logo=translate&logoColor=white)](docs/pt/README.md)
[![Русский](https://img.shields.io/badge/%D0%A0%D0%A3%D0%A1%D0%A1%D0%9A%D0%98%D0%99-lightgrey?style=for-the-badge&logo=translate&logoColor=white)](docs/ru/README.md)
[![Українська](https://img.shields.io/badge/%D0%A0%D0%A3%D0%A1%D0%A1%D0%9A%D0%98%D0%99-yellow?style=for-the-badge&logo=translate&logoColor=white)](docs/uk/README.md)

---

## 🧩 Supported Versions

- Proxmox VE 7.x / 8.x / 9.x
- Linux Kernel 6.x / 7.x
- Proxmox Backup Server 3.x / 4.x  
- Home Assistant 2024.6+  

---

## 📑 Table of Contents

- [Key Features v4](#-key-features-v400)
- [Cluster Monitoring](#-cluster-module-new)
- [Mounted Disks & Network Storage](#-mounted-disks-module-new)
- [Node Status & Performance](#-node-status--performance)
- [Disks & Hardware](#-disks--smart)
- [Virtual Machines & Containers](#-virtual-machines-qemu)
- [Backup Services](#-backup-services-vms--cts)
- [Proxmox Backup Server (PBS)](#-proxmox-backup-server-pbs)
- [Installation](#-installation)

---

## 🔥 Key Features (v4.0.0)

### 🌐 Cluster Module (NEW)
*Monitor your entire Proxmox infrastructure as a single entity.*
*   **Global Backup Stats:** Backup Health, Age, and Total Jobs across the cluster.
*   **Infrastructure Health:** Nodes Online, Failed Tasks, and aggregated CPU/RAM usage.
*   **Resource Tracking:** Global count of running VMs and CTs.

### 💽 Mounted Disks Module (NEW)
*Deep visibility into your node's storage layer.*
*   **Dynamic Detection:** Automatically lists `local_mounts` and `network_mounts`.
*   **Network Storage:** Detailed attributes for **CIFS/SMB** and **NFS** mounts (Server, Share, Usage).
*   **Mount Integrity:** Sensors for `missing_mounts` and `all_mounted` status.
*   **Filtered View:** Smart exclusion of system-temp mounts (tmpfs, dev, etc.) to show only relevant data.

### 🧠 Advanced Hardware Insight
*   **Precision Thermals:** Package-level temperature priority with core-average fallback.
*   **NVMe Master:** Real device names, SMART health, and multiple thermal zone support (NAND/Controller).
*   **Clean Entity Naming:** Nodes are used in the device registry, not hardcoded into sensor names, keeping your UI clean.

---

### 🖥️ Virtual Machines & Containers
- Status, CPU/RAM/Disk usage (Real-time).
- **Per-core usage** and core count attributes.
- Network RX/TX per guest.
- Full control actions: Start, Stop, Reboot, Shutdown, Pause, Hibernate.

---

## 💾 Backup Services (VMs & CTs)

The integration provides professional-grade backup orchestration directly from Home Assistant.

### 🟦 Single/Batch Backup (`create_vzdump_backup`)
*   **Flexible Targets:** Supports local storage, NFS, or PBS.
*   **Batch Mode:** Backup multiple IDs simultaneously (e.g., `101,105,110`).
*   **Naming Convention:** `HA-{{vmid}}-{{guestname}}` for easy identification.

### 🟩 Massive Backup (`backup_all`)
*   **Orchestration:** Back up all guests on a node with configurable concurrency and delays.
*   **Auto-Maintenance:** Perfect for nightly scheduled automations.

### 🟧 PBS Deduplication & Compatibility
All backups triggered via HA are **100% native**. They support PBS deduplication, incremental chains, and Garbage Collection exactly like the Proxmox GUI.

---

## 🗄️ Proxmox Backup Server (PBS)

**Specialized Datastore Monitoring:**
- **Security:** V4 requires **API Token** for PBS (Password login disabled for stability).
- **Maintenance:** Dedicated sensors for Garbage Collector (GC) status, Prune, and Verify tasks.
- **Deduplication:** Real-time deduplication ratio and datastore efficiency metrics.

---

## 🎨 Visual Organization

V4 cleans up your HA dashboard by automatically grouping sensors into:
1. **Cluster** (Global state)
2. **Node** (Physical host)
3. **Physical Disks** (SSD/NVMe devices)
4. **Virtual Machines / Containers**
5. **Storages / Datastores**

---

## 🧩 Installation

### 🔹 Via HACS (Recommended)
1. Open **HACS → Integrations**.
2. Click **Custom repositories** and add: `https://github.com/Javisen/proxmox_sensors`
3. Search for **“Proxmox Extended Sensors”** and install.
4. Restart Home Assistant.


---

## 🙌 Special Thanks

Special thanks to community members who helped test V4 across different hardware platforms and contributed valuable bug reports, debugging, and fixes for:
- lm-sensors compatibility
- CPU thermal detection
- DIMM/SMBIOS parsing improvements
- Home Assistant entity stability

Your feedback helped make V4 significantly more robust across heterogeneous Proxmox environments.


Special thanks to @CyberGWJ for extensive hardware testing and parser debugging contributions during the V4 development cycle.


---

## 🤝 Contributing & Community
Contributions are welcome! If you find this integration useful, please consider giving the project a ⭐ on GitHub.

**[Visit GitHub Repository](https://github.com/Javisen/proxmox_sensors)**

---

<p align="center"><i>Maintained by Javisen - MIT License</i></p>