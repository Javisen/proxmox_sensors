<p align="center">
  <img src="https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/img/logo_int_v4.png" alt="Proxmox Extended Sensors Logo" width="600"/>
</p>

> **面向 Home Assistant 的 Proxmox VE 与 Proxmox Backup Server（PBS）高稳定性监控与控制集成。**

# 🚀 Proxmox Extended Sensors（v4）

## 🚀 项目介绍

**Proxmox Extended Sensors v4** 是一个 Home Assistant 自定义集成，用于把 Proxmox VE 与 Proxmox Backup Server（PBS）的基础设施状态接入 Home Assistant。它不仅展示 CPU、内存、磁盘、网络、虚拟机和容器等原始指标，还会把这些指标整理成更容易理解的健康状态、评分和告警信号。

在 V3 中，项目重点已经从“单纯采集指标”转向“输出有意义的系统洞察”。V4 延续这个方向，继续提供 **Node Score**、**Node Status**（例如 Excellent / Warning）等高价值传感器，让你无需逐项分析每个实体，也能一眼判断节点是否健康，适合用于清晰的仪表盘和自动化通知。

为了支撑这些能力，V4 引入了高性能异步架构，使用信号量与优化后的协调器来控制并发，避免压垮 Proxmox API。即使在大型集群或复杂硬件环境中，也能尽量保持 Home Assistant 响应稳定。它不只是“一组传感器”，而是一个面向 Homelab 的专业管理桥梁。

---

## 🔍 V4 核心能力

- **[新增] 集群级监控**：集中查看整个 Proxmox 集群状态，包括备份、失败任务、在线节点等。
- **[新增] 高级挂载磁盘监控**：实时识别本地磁盘、CIFS 与 NFS 挂载，并提供详细使用率属性。
- **深度硬件洞察**：针对 NVMe（SMART / 温度）和 CPU 温区（Intel / AMD / ACPI）提供专门支持。
- **高稳定性架构**：异步核心配合并发控制（Semaphores），减少 API 饱和风险。
- **安全认证**：PBS 强制使用 API Token；PVE 支持灵活认证方式。
- **智能备份**：内置单个、批量和大规模备份服务，并兼容 PBS 去重机制。

---

## 🧠 为什么选择 V4？

V4 的升级重点是 **基础设施可靠性（Infrastructure Reliability）**：

- **低延迟性能**：正确使用 `async/await`，避免阻塞 Home Assistant 事件循环。
- **实体持久化**：重新设计 Unique ID，让传感器在重启、节点变化和集群调整后更稳定。
- **硬件多样性适配**：清晰的命名逻辑可适配异构硬件，减少重复实体和混乱命名。
- **更聪明的自动化**：通过 IO Wait、温度裕量、备份健康度等高精度属性触发通知和自动化。

---

## 🇨🇳 本次中文文档升级

本次升级为项目补齐中文项目说明与完整中文文档目录，让中文用户可以不依赖英文文档完成部署、授权、登录和故障排查。

新增内容包括：

- 中文文档首页：[`docs/zh/README.md`](docs/zh/README.md)
- 硬件传感器配置指南：[`docs/zh/01-install-sensors.md`](docs/zh/01-install-sensors.md)
- Proxmox 用户、角色和 API Token 配置指南：[`docs/zh/02-proxmox-config.md`](docs/zh/02-proxmox-config.md)
- Home Assistant 中安装并登录 PVE/PBS 的指南：[`docs/zh/03-login-pve-pbs.md`](docs/zh/03-login-pve-pbs.md)
- 中文常见问题与故障排查：[`docs/zh/04-faq.md`](docs/zh/04-faq.md)
- 根 README 增加中文项目说明与中文语言入口。

这次升级只补充文档与说明，不改变集成本身的运行逻辑或 Home Assistant 实体行为。

---

## 📚 文档与指南

**请选择语言开始安装和配置：**

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

- [V4 核心功能](#-v4-核心功能v400)
- [集群监控](#-集群模块新增)
- [挂载磁盘与网络存储](#-挂载磁盘模块新增)
- [节点状态与性能](#-节点状态与性能)
- [磁盘与硬件](#-磁盘与硬件)
- [虚拟机与容器](#-虚拟机与容器)
- [备份服务](#-备份服务vm--ct)
- [Proxmox Backup Server（PBS）](#-proxmox-backup-serverpbs)
- [安装](#-安装)

---

## 🔥 V4 核心功能（v4.0.0）

### 🌐 集群模块（新增）

*把整个 Proxmox 基础设施作为一个整体来监控。*

- **全局备份统计**：跨集群统计备份健康度、备份时间和任务总数。
- **基础设施健康状态**：节点在线数量、失败任务、聚合 CPU / RAM 使用率。
- **资源追踪**：统计正在运行的 VM 与 CT 数量。

### 💽 挂载磁盘模块（新增）

*深入查看节点存储层。*

- **动态检测**：自动列出 `local_mounts` 与 `network_mounts`。
- **网络存储**：为 **CIFS / SMB** 与 **NFS** 挂载提供服务器、共享路径、使用率等属性。
- **挂载完整性**：提供 `missing_mounts` 与 `all_mounted` 状态传感器。
- **过滤视图**：智能排除 tmpfs、dev 等系统临时挂载，只展示真正有用的存储数据。

### 🧠 高级硬件洞察

- **精确温度**：优先使用 Package 级温度，必要时回退到核心平均温度。
- **NVMe Master**：真实设备名、SMART 健康状态、多温区支持（NAND / Controller）。
- **清晰实体命名**：节点用于设备注册表，而不是硬编码到传感器名称中，让 UI 更整洁。

---

### 🖥️ 虚拟机与容器

- 状态、CPU / RAM / 磁盘实时使用率。
- **每核心使用率** 与核心数量属性。
- 每个 Guest 的网络 RX / TX。
- 完整控制动作：启动、停止、重启、关机、暂停、休眠。

---

## 💾 备份服务（VM / CT）

该集成直接在 Home Assistant 中提供专业级备份编排能力。

### 🟦 单个/批量备份（`create_vzdump_backup`）

- **灵活目标**：支持本地存储、NFS 或 PBS。
- **批量模式**：可同时备份多个 ID，例如 `101,105,110`。
- **命名规则**：使用 `HA-{{vmid}}-{{guestname}}`，便于识别。

### 🟩 大规模备份（`backup_all`）

- **编排能力**：可按节点备份所有 Guest，并配置并发数和延迟。
- **智能批处理**：减少 Proxmox API 压力。
- **Home Assistant 原生服务**：可通过脚本、自动化或仪表盘按钮触发。

### 🟧 PBS 去重与兼容性

- 支持 Proxmox Backup Server 作为备份目标。
- 与 PBS 去重机制兼容，减少重复数据占用。
- 可结合备份健康度传感器监控备份是否过期或失败。

---

## 🗄️ Proxmox Backup Server（PBS）

- 监控 datastore 状态、使用率和维护模式。
- 查看备份摘要、任务状态和相关属性。
- 适合将 PBS 状态汇入 Home Assistant 统一仪表盘。
- PBS 推荐并通常要求使用 API Token 登录。

---

## 🎨 可视化组织

该集成适合在 Home Assistant 中构建清晰的 Proxmox 仪表盘：

- 节点总体健康度与评分。
- VM / CT 运行状态与资源占用。
- 存储、挂载、磁盘健康和温度。
- 备份健康度、PBS datastore 状态和失败任务。

你可以基于这些实体创建 Lovelace 仪表盘、告警通知和自动化策略。

---

## 🧩 安装

### 🔹 通过 HACS（推荐）

1. 打开 Home Assistant 的 HACS。
2. 添加或搜索 Proxmox Extended Sensors 集成。
3. 安装后重启 Home Assistant。
4. 前往 **设置 → 设备与服务 → 添加集成**。
5. 按向导填写 Proxmox VE 或 PBS 的地址、用户和 API Token。

更完整的中文步骤见：[`docs/zh/03-login-pve-pbs.md`](docs/zh/03-login-pve-pbs.md)。

---

## 🙌 特别鸣谢

感谢原始集成作者与社区贡献者。这个项目在多个版本中持续演进，吸收了 Proxmox、Home Assistant 和 Homelab 用户的真实使用反馈。

同时也感谢所有测试、反馈、翻译和提交问题的用户，这些反馈帮助项目不断提升稳定性、兼容性和可用性。

---

## 🤝 贡献与社区

欢迎提交 Issue、功能建议、文档改进和翻译修正。提交问题时建议包含：

- Home Assistant 版本。
- Proxmox VE / PBS 版本。
- 集成版本。
- 相关日志或错误信息。
- 你的认证方式（用户密码 / API Token）和目标类型（PVE / PBS）。

如果你要补充文档或翻译，请尽量保持不同语言目录的文件结构一致。
