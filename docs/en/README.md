# 📚 Documentation and Guides

These guides cover the necessary steps to correctly configure the integration and take advantage of all its functionalities.

---

## 🌡️ [01. Hardware Sensors Configuration](01-install-sensors.md)
How to install and configure **lm-sensors** on your Proxmox node to enable temperature and fan monitoring.

---

## 🔑 [02. Proxmox Configuration](02-proxmox-config.md)
How to create a secure **user** and **API Token** in Proxmox (PVE and PBS) with the minimum necessary permissions.

---

## ⚙️ [03. Integration Login (PVE and PBS)](03-login-pve-pbs.md)
Step-by-step guide to connect the integration with your servers from Home Assistant.

---

## ❓ [04. Frequently Asked Questions and Troubleshooting](04-faq.md)
Common problems, frequent questions, and how to solve them.

---

<p align="center">
  <img src="https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/img/logo_int_v4.png" alt="Proxmox Extended Sensors Logo" width="600"/>
</p>

---

# 🚀 Proxmox Extended Sensors

## Introduction

**Proxmox Extended Sensors is an integration for Home Assistant designed to provide advanced monitoring and complete control of Proxmox VE and Proxmox Backup Server (PBS).**

Unlike solutions based solely on metrics, this integration introduces an approach centered on **useful information (insight)**, allowing you to understand not only what is happening in the system, but also how it is actually performing.

It provides complete visibility of the infrastructure and adds direct control capabilities over nodes, virtual machines, containers, storage, and backup services.

---

## 🧠 System Insight (V3/V4)

Starting from version 3, the integration evolved from a collection of technical metrics to an infrastructure-oriented observability system.

V4 introduces sensors capable of interpreting the global state of the node and transforming complex metrics into useful and actionable information:

- **Proxmox Node** → global node state (`Excellent`, `Warning`, `Critical`, etc.) with enriched infrastructure attributes
- **Node Score** → numerical evaluation of system performance and overall health
- **Load Average (1m / 5m / 15m)** → actual host load
- **IO Wait** → detection of disk pressure and saturation
- **CPU usage per core** → available for nodes, VMs and containers
- **Node network telemetry** → intelligent calculation of aggregated RX/TX traffic from VMs and CTs
- **Advanced storage information** → status, capacity and detailed metrics of physical disks and storages

These sensors make it possible to detect bottlenecks, identify system degradation and build much smarter automations without the need for additional external tools.

---

## 🔍 Main capabilities of V4

- Global Proxmox cluster monitoring
- Advanced detection of mounted disks (CIFS/NFS/local)
- Intelligent network and storage telemetry
- Aggregated health and infrastructure sensors

### Complete monitoring of:

- Nodes
- Virtual machines (QEMU)
- Containers (LXC)
- Disks and storage
- Proxmox Backup Server (PBS)

### Advanced functionalities

- Control actions from Home Assistant
- Integrated backup services
- Full compatibility with PBS (including deduplication)
- Secure token-based authentication
- Clean and consistent entity structure
- Optimized updates and low resource consumption

---

## 🧩 Supported Versions

- Proxmox VE 7.x / 8.x / 9.x
- Compatible with Linux Kernel 6.x / 7.x
- Proxmox Backup Server 3.x / 4.x
- Home Assistant 2024.x or later

---

## 📑 Table of Contents

- [Key Features](#-key-features-v400)
- [Node Status and Performance](#-node-status-and-performance)
- [Disks and SMART](#-disks-and-smart)
- [Virtual Machines (QEMU)](#-virtual-machines-qemu)
- [Containers (LXC)](#-containers-lxc)
- [Backup Services](#-backup-services-vms-and-cts)
- [Proxmox Backup Server (PBS)](#-proxmox-backup-server-pbs)
- [Control Actions (PVE and PBS)](#-control-actions-pve-and-pbs)
- [Installation](#-installation)
- [Visual Configuration Guide](#-visual-configuration-guide)
- [Contributions](#-contributions-and-community)

---

## 🔥 Key Features of V4

### ⚙️ Enhanced Configuration

- Automatic node discovery
- Optional manual selection
- Simpler, guided configuration
- API Token compatibility (PVE/PBS)
- Intelligent detection of limited permissions

---

### 🌐 Cluster Monitoring (NEW)

- Global Proxmox cluster sensors
- Backup status and failed tasks
- Online/offline nodes
- Aggregated CPU and RAM usage
- Global count of VMs and CTs

---

### 💽 Mounted Disks and Storage (NEW)

- Automatic detection of mounted disks
- Compatibility with CIFS / SMB and NFS
- Integrity and missing mounts sensors
- Intelligent exclusion of tmpfs and pseudo-mounts
- Detailed usage and capacity metrics

---

### 🌡️ Advanced Hardware Monitoring

- Real-time temperatures (CPU, VRM, chipset, disks)
- Fan and voltage sensors
- Intelligent filtering of valid sensors
- Unified temperature sensors (CPU + NVMe)
- Advanced Intel / AMD / ACPI / NVMe compatibility

> Requires `lm-sensors` on the Proxmox host

---

### 🧠 Node Status and Performance

- CPU, RAM, uptime, kernel and PVE version
- Network monitoring (RX/TX)
- Tasks and system status
- Advanced load and performance metrics
- Node Score and global infrastructure status

---

### 💾 Disks and SMART

- Sensors grouped by physical disk
- Total/used space and advanced metrics
- SMART attributes (HDD, SSD, NVMe)
- Temperatures by disk type
- Advanced NVMe metrics and health status

---

### 🖥️ Virtual Machines (QEMU)

- Status, CPU, memory and disk
- Network RX/TX
- Basic information and uptime
- CPU usage per core
- Control actions from Home Assistant

---

### 📦 Containers (LXC)

- Status, CPU, memory and disk
- Network RX/TX
- Basic information and uptime
- CPU usage per core
- Control actions from Home Assistant

---

## 💾 Backup Services (VMs and CTs)

The integration allows creating backups directly from Home Assistant, fully compatible with Proxmox VE and PBS.

### 🟦 Individual Backup

- Supports multiple IDs (comma separated)
- Modes: snapshot / suspend / stop
- Compression: zstd / gzip / lzo / none
- Compatible with PBS and deduplication

### 🟩 Mass Backup

- Backup of all resources on a node
- Concurrency and timing control
- Ideal for automation
- Compatible with large infrastructures

Backups are automatically named as:

```text
HA-{{vmid}}-{{guestname}}
```

Fully compatible with PBS, including deduplication and existing chains.

---

## 🗄️ Proxmox Backup Server (PBS)

Advanced datastore and task monitoring:

- Total, free and percentage usage
- Deduplication ratio
- Last backup status
- Errors and task summary
- Garbage Collector status
- Detailed task information

---

## 🎛️ Control Actions (PVE & PBS)

**Node:**
- Shutdown / Reboot / Wake-on-LAN

**Virtual Machines:**
- Start / Stop / Shutdown / Reboot / Reset
- Pause / Resume / Hibernate

**Containers:**
- Start / Stop / Shutdown / Reboot

**PBS:**
- Garbage Collector
- Prune
- Verify
- Sync

---

## 🎨 Organization and structure

- Sensors automatically grouped into:
  1. Cluster
  2. Node
  3. Physical disks
  4. Virtual machines
  5. Containers
  6. Storage / Datastores
  7. PBS and tasks

- Consistent and clear names to facilitate dashboards and automations

---

## 🧩 Installation

### 🔹 Via HACS (recommended)

1. Open **HACS → Integrations**
2. Add custom repository
3. Search for **Proxmox Extended Sensors**
4. Install and restart Home Assistant
5. Add the integration from settings

### 🔹 Manual installation

1. Copy to `/config/custom_components/proxmox_sensors`
2. Restart Home Assistant
3. Add the integration

---

## 🧭 Visual Configuration Guide

Below you will find a complete visual walkthrough of the configuration process, including access methods, resource selection and installation steps.

<details>
  <summary>🪪 Server Connection</summary>
  <p align="center">
    <img src="../../img/install/setup_pve_1.png" alt="Proxmox Connection" width="600">
  </p>
  <p align="center"><i>It is not necessary to include "http://" or "https://". This is handled automatically.</i></p>
</details>

<details>
  <summary>🪪 Login with Username and Password (PVE only)</summary>
  <p align="center">
    <img src="../../img/install/access_passw.png" alt="Username and password login" width="600">
  </p>
  <p align="center"><i>Make sure to use the correct realm (`pam` or `pve`).</i></p>
</details>

<details> 
  <summary>🪪 Login with User and Token (PVE and PBS)</summary>
  <p align="center">
    <img src="../../img/install/access_token.png" alt="Token login" width="600">
  </p>
  <p align="center"><i>In the Token_id field you only need to enter the token name.</i></p>
</details>

<details>
  <summary>🧠 Node Selection (V4)</summary>
  <p align="center">
    <img src="../../img/install/node_select.png" alt="Node selection" width="600">
  </p>
  <p align="center"><i>Select the automatically detected nodes or manually define which ones to include.</i></p>
</details>

<details>
  <summary>⚙️ Resource Selection</summary>
  <p align="center">
    <img src="../../img/install/resources_select.png" alt="Resource selection" width="600">
  </p>
  <p align="center"><i>Select the CTs, VMs and storages you wish to include, along with the corresponding options.</i></p>
</details>

---

**If you find this integration useful, consider leaving a ⭐ on GitHub.**

---

## 🤝 Contributions and Community

Contributions are welcome. You can open issues or pull requests.
Repository: https://github.com/Javisen/proxmox_sensors

---

<p align="center"><i>Maintained by Javisen - MIT License</i></p>