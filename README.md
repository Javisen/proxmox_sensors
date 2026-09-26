<p align="center">
  <img src="https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/img/logo_int.png" alt="Proxmox Extended Sensors Logo" width="600"/>
</p>

> **Advanced Proxmox VE & PBS monitoring, control and dashboard integration for Home Assistant.**

# 🚀 Proxmox Extended Sensors

## 📚 Documentation & Guides

**Select your language to start the installation and configuration:**

[![English](https://img.shields.io/badge/ENGLISH-blue?style=for-the-badge&logo=translate&logoColor=white)](docs/en/README.md)
[![中文](https://img.shields.io/badge/%E4%B8%AD%E6%96%87-blue?style=for-the-badge&logo=translate&logoColor=white)](docs/zh/README.md)
[![Español](https://img.shields.io/badge/ESPA%C3%91OL-orange?style=for-the-badge&logo=translate&logoColor=white)](docs/es/README.md)
[![Italiano](https://img.shields.io/badge/ITALIANO-green?style=for-the-badge&logo=translate&logoColor=white)](docs/it/README.md)
[![Français](https://img.shields.io/badge/FRAN%C3%87AIS-blue?style=for-the-badge&logo=translate&logoColor=white)](docs/fr/README.md)
[![Deutsch](https://img.shields.io/badge/DEUTSCH-red?style=for-the-badge&logo=translate&logoColor=white)](docs/de/README.md)
[![Nederlands](https://img.shields.io/badge/NEDERLANDS-orange?style=for-the-badge&logo=translate&logoColor=white)](docs/nl/README.md)
[![Português](https://img.shields.io/badge/PORTUGU%C3%8AS-green?style=for-the-badge&logo=translate&logoColor=white)](docs/pt/README.md)
[![Русский](https://img.shields.io/badge/%D0%A0%D0%A3%D0%A1%D0%A1%D0%9A%D0%98%D0%99-lightgrey?style=for-the-badge&logo=translate&logoColor=white)](docs/ru/README.md)
[![Українська](https://img.shields.io/badge/%D0%A3%D0%9A%D0%A0%D0%90%D0%87%D0%9D%D0%A1%D0%AC%D0%9A%D0%90-yellow?style=for-the-badge&logo=translate&logoColor=white)](docs/uk/README.md)

---

## 📑 Table of Contents

- [Introduction](#-introduction)
- [Core Features](#-core-features)
- [PVE & CLUSTER Association](#-pve--cluster-association)
- [Dynamic Proxmox Dashboard](#-dynamic-proxmox-dashboard)
- [Migration-Safe VM & LXC Monitoring](#-migration-safe-vm--lxc-monitoring)
- [Resilient Monitoring & Fault Isolation](#%EF%B8%8F-resilient-monitoring--fault-isolation)
- [PVE Replication Status](#-pve-replication-status)
- [Proxmox Backup Server (PBS)](#%EF%B8%8F-proxmox-backup-server-pbs)
- [Remote / Hosted PBS](#%EF%B8%8F-remote--hosted-pbs)
- [Multi-PBS Support](#-multi-pbs-support)
- [Sidecar Status](#%EF%B8%8F-sidecar-status)
- [Cluster Monitoring](#-cluster-monitoring)
- [Mounted Disks & Network Storage](#-mounted-disks--network-storage)
- [Hardware & Node Monitoring](#-hardware--node-monitoring)
- [Physical Wake-on-LAN](#-physical-wake-on-lan)
- [Virtual Machines & Containers](#%EF%B8%8F-virtual-machines--containers)
- [Backup Services](#-backup-services-vms--cts)
- [Supported Versions](#-supported-versions)
- [Installation](#-installation)

---

## 🚀 Introduction

**Proxmox Extended Sensors** brings detailed Proxmox VE, Proxmox Backup Server and cluster monitoring into Home Assistant, with stable entity identity, hardware telemetry, backup and replication information, maintenance actions and an optional dynamic Lovelace dashboard.

The integration is designed for both standalone Proxmox nodes and multi-node environments. It isolates partial API failures, preserves valid data during temporary outages and tracks VM/LXC guests across correctly associated cluster nodes without tying their logical Home Assistant identity to the physical node currently hosting them.

---

## ✨ Core Features

- 🔗 **PVE ↔ CLUSTER association** — configure a PVE node as standalone or associate it with its corresponding CLUSTER entry.
- 🔄 **Migration-safe VM/LXC identity** — guests can keep their Home Assistant identity when moving between correctly associated nodes.
- 🛡️ **Partial-failure resilience** — a failing API section does not unnecessarily invalidate unrelated data.
- 🔁 **PVE Replication monitoring** — global status plus per-job runtime information.
- 🗄️ **PBS monitoring and maintenance** — datastore usage, backups, deduplication, GC, Prune, Verify and Sync where available.
- ☁️ **Remote / hosted PBS connectivity** — standard PBS API connections can also be used with hosted services when the provider exposes the required permissions.
- ❤️ **Sidecar Status** — diagnostic health for Memory, Mounts, Sensors and SMART endpoints.
- 🌡️ **Hardware monitoring** — CPU, temperatures, voltages, fans, NVMe, SMART, DIMM/SMBIOS and Raspberry Pi CPU temperature where exposed.
- ⚡ **Physical Wake-on-LAN** — wake a configured physical PVE node directly from the integration, even while the node is offline.
- 📊 **VM/LXC resource monitoring** — including CT memory/disk and VM memory percentages.
- 🎨 **Dynamic Proxmox Dashboard** — PVE, PBS and CLUSTER dashboards generated from the resources available in Home Assistant.

> [!CAUTION]
> **Upgrading from an older installation?**  
> Keep the sidecar script updated on every PVE node so its endpoints remain aligned with the integration.

<details>
<summary>Update <code>pve-sensors-api.py</code></summary>

```bash
wget https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/scripts/pve-sensors-api.py -O /usr/local/bin/pve-sensors-api.py
chmod +x /usr/local/bin/pve-sensors-api.py
systemctl restart pve-sensors.service
```

</details>

---

## 🔗 PVE & CLUSTER Association

A PVE connection can operate as an **independent node** or be explicitly associated with a configured **CLUSTER** entry.

The association uses a persistent internal scope instead of relying only on node or cluster names. This keeps separate Proxmox environments isolated and gives the integration a stable context for guest identity and reconciliation.

When configuring a new PVE entry, choose the matching CLUSTER when the node belongs to a cluster already configured in Home Assistant. Choose standalone mode when the PVE node should be managed independently.

Existing installations are handled conservatively: legacy identities are preserved where required instead of being forcibly converted when the association cannot be determined safely.

---

## 🎨 Dynamic Proxmox Dashboard

The optional dashboard system builds a complete Lovelace starting point from the entities and resources discovered in your installation.

### Available dashboard types

- **PVE** — node health, temperatures, node information, storage, CTs, VMs, diagnostics and replication.
- **PBS** — server/datastore information, backups, maintenance, tasks and actions.
- **CLUSTER** — cluster health, resources, system state, backup health and replication.

When multiple PBS or CLUSTER instances are configured, the dashboard keeps each instance in its **own separate view**. Resources from different PBS servers or clusters are not combined simply because they have the same visible names. PVE views can also reflect their explicit CLUSTER association.

Only dashboard types backed by real resources are offered. The dashboard is optional and the integration works normally without installing it.

<details>
<summary><b>📦 Dashboard requirements & installation</b></summary>

### Requirements

- Proxmox Extended Sensors
- [Card Mod](https://github.com/thomasloven/lovelace-card-mod)

### Installation

1. Install **Card Mod** from HACS if it is not already installed.
2. Add the following Lovelace resource as a **JavaScript Module**:

   ```text
   /proxmox_sensors/proxmox-dashboard.js
   ```

3. Reload the browser.
4. Create a new dashboard from **Settings → Dashboards → Add dashboard → Community**.
5. Select **Proxmox Extended Sensors**.
6. Choose one of the dashboard types offered for your installation: **PVE**, **PBS** or **CLUSTER**.

The generated dashboard remains strategy-driven until you choose **Take Control**.

</details>

<details>
<summary><b>🛠️ What happens when I use Take Control?</b></summary>

Home Assistant converts the generated dashboard into a normal editable Lovelace configuration. You can then reorganize the layout, remove cards, add your own entities and combine Proxmox information with anything else in Home Assistant.

The integration does not overwrite a dashboard that you have taken control of.

</details>

## 📸 Dashboard screenshots

<details>
<summary><b>PVE</b></summary>

<br>
<img src="https://github.com/Javisen/test_javisen/raw/refs/heads/main/img/Dashb_Node.png" alt="PVE dashboard" width="100%">

</details>

<details>
<summary><b>PBS</b></summary>

<br>
<img src="https://github.com/Javisen/test_javisen/raw/refs/heads/main/img/Dashb_PBS.png" alt="PBS dashboard" width="100%">

</details>

<details>
<summary><b>CLUSTER</b></summary>

<br>
<img src="https://github.com/Javisen/test_javisen/raw/refs/heads/main/img/Dashb_Cluster.png" alt="CLUSTER dashboard" width="100%">

</details>

---

## 🔄 Migration-Safe VM & LXC Monitoring

For PVE nodes correctly associated with the same configured cluster scope, VM/LXC identity is independent of the physical node currently hosting the guest.

When a guest migrates between those nodes, the integration reconciles it at its new location while keeping the same logical Home Assistant identity. This is designed to preserve the entities referenced by history, dashboards, automations and areas instead of creating a replacement guest simply because its Proxmox node changed.

Guest controls follow the reconciled VM/LXC to its current node.

> Migration reconciliation is progressive. Immediately after a move, the source device can remain temporarily empty while sensors and cleanup converge over subsequent coordinator cycles.

---

## 🛡️ Resilient Monitoring & Fault Isolation

The integration isolates API work so one failing subsystem does not unnecessarily invalidate the rest of the installation.

- Independent API task timeouts.
- Controlled concurrency to avoid API saturation.
- Preservation of last valid data for affected sections.
- Automatic recovery when communication returns.
- Safer cleanup during partial refreshes.
- PBS inventory preservation during temporary connection failures.
- Storage reconciliation only removes resources when current data confirms they have disappeared.

---

## 🔁 PVE Replication Status

Native monitoring for Proxmox VE replication jobs includes:

- **Replication Jobs** — number and inventory of configured replication jobs.
- **Replication Status** — global replication state and failed-job details.
- Duration, last/next replication, source and target, guest type, failure count and runtime freshness.

Replication identity is based on the Proxmox replication job rather than only the physical node, allowing replication information to remain associated with a migrated guest.

---

## 🗄️ Proxmox Backup Server (PBS)

PBS monitoring includes datastore usage, backups, deduplication and maintenance information.

### Maintenance actions

- **Garbage Collection (GC)** — direct datastore action.
- **Prune** — runs the configured Prune Job for the datastore.
- **Verify** — runs the configured Verify Job.
- **Sync** — runs the configured Sync Job when available.

Actions launched from Home Assistant are tracked using the exact **UPID** returned by PBS, allowing their real progression to be represented as:

**Started → Running → OK / Error**

When no Home Assistant-triggered UPID is available, the integration can fall back to the most recent matching PBS job for operations launched directly from PBS or by schedule.

Backup Job, Backup Age and Backup Health information is handled conservatively: when fresh task information is unavailable, stale restored data is not presented as current healthy state.

---

## ☁️ Remote / Hosted PBS

Proxmox Extended Sensors connects to PBS through the standard HTTPS API, so the PBS server does not need to be on the same local network as Home Assistant.

This has been successfully tested with a **hosted Proxmox Backup Server from Tuxis**, including datastore monitoring and authorized maintenance operations. Available information and actions depend on the permissions exposed by the hosting provider. Server-level hardware information may not be available on a hosted service.

### API token examples

A typical self-hosted PBS configuration can use a short token name:

```text
User:     homeassistant@realm
Token ID: home
Token:    <API token secret>
```

A hosted provider may require the complete token identifier. For example, Tuxis uses a format such as:

```text
Host:     https://pbs005.tuxis.nl
User:     FL000XX_USUARIO@pbs
Token ID: FL000XX@pbs!home
Token:    <API token secret>
```

If **Token ID** already contains `!`, the integration uses it as the complete API token identifier. If a short Token ID is supplied, the integration builds the identifier from `User!Token ID`.

> Never publish or share the API token secret.

---

## 🧩 Multi-PBS Support

Multiple PBS connections can be configured in Home Assistant. Each PBS entry receives a persistent server identity so server, datastore and maintenance information remains associated with the correct PBS instance.

PBS instances remain isolated even when different servers use **datastores with the same name**. Re-added PBS instances can recover their previous server identity, and historical server IDs are not immediately reused for unrelated servers.

The dashboard follows the same separation and gives each configured PBS instance its own view instead of mixing resources from different servers.

---

## ❤️ Sidecar Status

Each PVE node exposes a single **Sidecar Status** diagnostic sensor summarizing the health of:

- Memory
- Mounts
- Sensors
- SMART

Possible states are `ok`, `degraded`, `error` and `unknown`.

When a sidecar endpoint fails, previously valid hardware values can be preserved instead of disappearing immediately.

---

## 🌐 Cluster Monitoring

Monitor the Proxmox cluster as a whole with dedicated entities for:

- Nodes online
- CPU and RAM usage
- Running VMs and CTs
- Storage usage
- Firewall state
- Failed tasks
- Backup jobs, backup age and backup health
- Replication jobs and replication status

---

## 💽 Mounted Disks & Network Storage

Deep visibility into each node's storage layer:

- Automatic discovery of local and network mounts.
- CIFS/SMB and NFS information.
- Usage and mount details.
- Detection of missing mounts.
- Filtering of irrelevant temporary/system mounts.

---

## 🧠 Hardware & Node Monitoring

Hardware information is collected through Proxmox and the optional sidecar/lm-sensors path where supported.

- CPU and system health information.
- CPU Package/Core thermal monitoring where available.
- CPU core temperatures exposed as attributes of the CPU temperature entity.
- Raspberry Pi / ARM CPU temperature through `cpu_thermal` when x86 Package/Core labels are not available.
- Temperature, voltage and fan channel classification from lm-sensors data.
- Chipset and NVMe temperatures.
- NVMe SMART and health information.
- DIMM/SMBIOS information where supported by the sidecar.
- I/O Wait and network traffic.
- KSM information.
- Node update information.

The sensor classifier distinguishes common hwmon channels such as `tempN_input`, `inN_input` and `fanN_input`, preventing CPU voltage channels such as Vcore from occupying the CPU temperature sensor when real CPU temperature data is available.

---

## ⚡ Physical Wake-on-LAN

Physical PVE nodes can be started from Home Assistant with the integration's **Wake** button when a valid MAC address is configured.

Wake-on-LAN is sent **directly by Proxmox Extended Sensors** as a UDP magic packet. It does not depend on Home Assistant's optional `wake_on_lan.send_magic_packet` action or on the PVE API being reachable at that moment.

Because the magic packet is generated locally by the integration, the **Wake button remains available while the PVE node is offline**. Actions that require the Proxmox API, such as Shutdown or Reboot, remain unavailable while the node cannot be reached.

The target hardware, firmware and network must support Wake-on-LAN and be configured to accept the magic packet. Virtualized PBS/PVE systems depend on the capabilities of their virtual network interface and host; a virtual NIC such as VirtIO should not be assumed to provide physical Wake-on-LAN behavior.

---

## 🖥️ Virtual Machines & Containers

VM and LXC monitoring includes guest state and resource information exposed by Proxmox and the integration, including:

- CT memory percentage
- CT disk percentage
- VM memory percentage
- `onboot`, expected state and state/onboot matching information
- Cluster-aware migration continuity for correctly associated nodes

> VM disk percentage is not exposed because the integration does not currently have a sufficiently reliable source metric for it.

---

## 💾 Backup Services (VMs & CTs)

The integration provides backup orchestration directly from Home Assistant.

### 🟦 Single/Batch Backup (`create_vzdump_backup`)

- Supports local storage, NFS and PBS targets.
- Multiple guest IDs can be backed up in one operation.
- Native Proxmox backup execution preserves compatibility with PBS deduplication.

### 🟩 Massive Backup (`backup_all`)

- Back up all guests on a node.
- Configurable concurrency and delays.
- Suitable for scheduled Home Assistant automations.

---

## 🧩 Supported Versions

- Proxmox VE 7.x / 8.x / 9.x
- Proxmox Backup Server 3.x / 4.x
- Home Assistant 2026.5+

---

## 🧩 Installation

### 🔹 Via HACS (Recommended)

[![Open your Home Assistant instance and open Proxmox Extended Sensors in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Javisen&repository=proxmox_sensors&category=integration)

**Proxmox Extended Sensors is available in the default HACS repository — no custom repository is required.**

1. Open **HACS → Integrations**.
2. Search for **Proxmox Extended Sensors**.
3. Click **Download**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & Services → Add Integration**.
6. Search for **Proxmox Extended Sensors** and configure your PVE, PBS and/or CLUSTER connection.

> The optional Proxmox Dashboard is installed separately. See [Dynamic Proxmox Dashboard](#-dynamic-proxmox-dashboard).

---

## 🙌 Special Thanks

Special thanks to the community members who test the integration across different hardware and Proxmox environments and contribute bug reports, diagnostics, code and validation.

Thank you to everyone who reports issues, tests fixes and helps make the integration more reliable. ❤️

---

## 🤝 Contributing

Contributions, testing and bug reports are welcome.

Please use the GitHub issue tracker for reproducible problems and include relevant Home Assistant / Proxmox logs where appropriate.

---

## 📄 License

MIT License

Copyright (c) Javisen
