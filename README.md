<p align="center">
  <img src="https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/img/logo_int_v4.png" alt="Proxmox Extended Sensors Logo" width="600"/>
</p>

> **适用于 Home Assistant 的 Proxmox VE 与 PBS 高可靠、细粒度监控和控制系统。**

# 🚀 Proxmox Extended Sensors（v4）中文版

## 🚀 简介

**Proxmox Extended Sensors v4** 是原集成的一次完整演进，经过从底层重新设计，为 Home Assistant 提供工业级稳定性和更深入的系统洞察能力。

在 V3 的基础上，本集成从单纯展示原始指标，升级为提供更有意义、可解释的信息。V4 继续提供高价值传感器，例如 Node Score 和 Node Status（Excellent/Warning），让你无需逐个分析传感器，就能一眼判断系统健康状态，非常适合智能自动化和清爽的仪表盘展示。

为支撑这些智能能力，V4 引入了高性能异步架构，使用信号量和优化后的 coordinator 控制并发。即使在管理大型集群或复杂硬件时，也能保持 Home Assistant 响应稳定。它不再只是一组传感器，而是面向 Homelab 的专业管理桥接层。

---

## 🔍 V4 核心能力

*   **[新增] 集群级监控：** 为整个 Proxmox 集群提供集中式状态传感器，包括备份、失败任务、在线节点等。
*   **[新增] 高级挂载磁盘识别：** 实时检测本地磁盘、CIFS 和 NFS 挂载，并提供详细使用属性。
*   **深度硬件洞察：** 专门支持 NVMe（SMART/温度）和 CPU 温区（Intel/AMD/ACPI）。
*   **高稳定性架构：** 基于异步核心和并发控制（Semaphores），避免 API 被打满。
*   **安全认证：** PBS 强制支持 API Token，PVE 支持灵活认证方式。
*   **智能备份：** 完全集成单个或大批量备份服务，兼容 PBS 去重能力。

---

## 🧠 为什么选择 V4？

V4 升级的重点转向 **基础设施可靠性**：

*   **零卡顿性能：** 正确实现 `async/await`，避免阻塞事件循环。
*   **实体持久化：** 重新设计 Unique ID，确保传感器在重启和集群变更后仍能稳定保留。
*   **硬件多样性适配：** 清晰的命名逻辑可适配异构硬件，避免重复实体。
*   **更智能的自动化：** 为磁盘压力（IO Wait）和温度余量提供高精度属性。

---

## 📚 文档与指南

**选择语言以开始安装和配置：**

[![English](https://img.shields.io/badge/ENGLISH-blue?style=for-the-badge&logo=translate&logoColor=white)](docs/en/README.md)
[![中文](https://img.shields.io/badge/%E4%B8%AD%E6%96%87-red?style=for-the-badge&logo=translate&logoColor=white)](docs/zh/README.md)
[![Español](https://img.shields.io/badge/ESPA%C3%91OL-orange?style=for-the-badge&logo=translate&logoColor=white)](docs/es/README.md)
[![Italiano](https://img.shields.io/badge/ITALIANO-green?style=for-the-badge&logo=translate&logoColor=white)](docs/it/README.md)
[![Français](https://img.shields.io/badge/FRAN%C3%87AIS-blue?style=for-the-badge&logo=translate&logoColor=white)](docs/fr/README.md)
[![Deutsch](https://img.shields.io/badge/DEUTSCH-red?style=for-the-badge&logo=translate&logoColor=white)](docs/de/README.md)
[![Nederlands](https://img.shields.io/badge/NEDERLANDS-orange?style=for-the-badge&logo=translate&logoColor=white)](docs/nl/README.md)
[![Português](https://img.shields.io/badge/PORTUGU%C3%8AS-green?style=for-the-badge&logo=translate&logoColor=white)](docs/pt/README.md)
[![Русский](https://img.shields.io/badge/%D0%A0%D0%A3%D0%A1%D0%A1%D0%9A%D0%98%D0%99-lightgrey?style=for-the-badge&logo=translate&logoColor=white)](docs/ru/README.md)
[![Українська](https://img.shields.io/badge/%D0%A0%D0%A3%D0%A1%D0%A1%D0%9A%D0%98%D0%99-yellow?style=for-the-badge&logo=translate&logoColor=white)](docs/uk/README.md)

---

## 🧩 支持版本

- Proxmox VE 7.x / 8.x / 9.x
- Linux Kernel 6.x / 7.x
- Proxmox Backup Server 3.x / 4.x
- Home Assistant 2024.6+

---

## 📑 目录

- [V4 核心功能](#-v4-核心功能400)
- [集群监控](#-集群模块新增)
- [挂载磁盘与网络存储](#-挂载磁盘模块新增)
- [节点状态与性能](#-高级硬件洞察)
- [磁盘与硬件](#-高级硬件洞察)
- [虚拟机与容器](#️-虚拟机与容器)
- [备份服务](#-备份服务vms--cts)
- [Proxmox Backup Server（PBS）](#️-proxmox-backup-serverpbs)
- [安装](#-安装)

---

## 🔥 V4 核心功能（4.0.0）

### 🌐 集群模块（新增）
*将整个 Proxmox 基础设施作为一个整体进行监控。*
*   **全局备份统计：** 跨集群展示备份健康状态、备份年龄和任务总数。
*   **基础设施健康状态：** 在线节点、失败任务，以及聚合后的 CPU/RAM 使用情况。
*   **资源追踪：** 全局统计运行中的 VM 和 CT 数量。

### 💽 挂载磁盘模块（新增）
*深入查看节点的存储层。*
*   **动态检测：** 自动列出 `local_mounts` 和 `network_mounts`。
*   **网络存储：** 为 **CIFS/SMB** 和 **NFS** 挂载提供详细属性（服务器、共享、使用率）。
*   **挂载完整性：** 提供 `missing_mounts` 和 `all_mounted` 状态传感器。
*   **过滤视图：** 智能排除系统临时挂载（tmpfs、dev 等），只展示相关数据。

### 🧠 高级硬件洞察
*   **精准温度：** 优先使用封装级温度，缺失时回退到核心平均温度。
*   **NVMe Master：** 支持真实设备名、SMART 健康状态和多个温区（NAND/Controller）。
*   **清晰实体命名：** 节点信息写入设备注册表，而不是硬编码到传感器名称中，让 UI 更干净。

---

### 🖥️ 虚拟机与容器
- 状态、CPU/RAM/磁盘使用率（实时）。
- **单核心使用率** 和核心数量属性。
- 每个 guest 的网络 RX/TX。
- 完整控制动作：Start、Stop、Reboot、Shutdown、Pause、Hibernate。

---

## 💾 备份服务（VMs & CTs）

本集成可直接从 Home Assistant 提供专业级备份编排能力。

### 🟦 单个/批量备份（`create_vzdump_backup`）
*   **灵活目标：** 支持本地存储、NFS 或 PBS。
*   **批量模式：** 可同时备份多个 ID，例如 `101,105,110`。
*   **命名约定：** 使用 `HA-{{vmid}}-{{guestname}}`，便于识别。

### 🟩 大规模备份（`backup_all`）
*   **编排能力：** 按节点备份所有 guest，支持配置并发和延迟。
*   **自动维护：** 非常适合夜间定时自动化任务。

### 🟧 PBS 去重与兼容性
通过 HA 触发的所有备份都是 **100% 原生** 的。它们与 Proxmox GUI 一样支持 PBS 去重、增量链和 Garbage Collection。

---

## 🗄️ Proxmox Backup Server（PBS）

**专用 Datastore 监控：**
- **安全性：** V4 要求 PBS 使用 **API Token**（为了稳定性禁用密码登录）。
- **维护：** 为 Garbage Collector（GC）状态、Prune 和 Verify 任务提供专用传感器。
- **去重：** 实时展示去重率和 datastore 效率指标。

---

## 🎨 视觉组织

V4 会自动把传感器分组，从而整理你的 HA 仪表盘：
1. **Cluster**（全局状态）
2. **Node**（物理主机）
3. **Physical Disks**（SSD/NVMe 设备）
4. **Virtual Machines / Containers**
5. **Storages / Datastores**

---

## 🧩 安装

### 🔹 通过 HACS（推荐）
1. 打开 **HACS → Integrations**。
2. 点击 **Custom repositories** 并添加：`https://github.com/Javisen/proxmox_sensors`
3. 搜索 **"Proxmox Extended Sensors"** 并安装。
4. 重启 Home Assistant。

---

## 🙌 特别感谢

特别感谢社区成员在不同硬件平台上帮助测试 V4，并为以下方面提供了宝贵的错误报告、调试和修复：
- lm-sensors 兼容性
- CPU 温度检测
- DIMM/SMBIOS 解析改进
- Home Assistant 实体稳定性

你们的反馈让 V4 在异构 Proxmox 环境中变得更加稳健。

特别感谢 @CyberGWJ 在 V4 开发周期中进行了大量硬件测试，并为解析器调试做出贡献。

---

## 🤝 贡献与社区

欢迎贡献！如果你觉得这个集成有用，请考虑在 GitHub 上给项目点一个 ⭐。

**[访问 GitHub 仓库](https://github.com/Javisen/proxmox_sensors)**

---

<p align="center"><i>由 Javisen 维护 - MIT License</i></p>
