# 📚 文档与指南

这些指南介绍如何正确配置 **Proxmox Extended Sensors** 集成，并使用它在 Home Assistant 中监控 Proxmox VE 与 Proxmox Backup Server（PBS）。

---

## 🌡️ [01. 硬件传感器配置](01-install-sensors.md)
介绍如何在 Proxmox 节点上安装并配置 **lm-sensors** 与 SMART 工具，以启用温度、风扇和磁盘健康监控。

---

## 🔑 [02. Proxmox 用户与权限配置](02-proxmox-config.md)
介绍如何在 Proxmox（PVE 和 PBS）中创建安全的专用用户与 **API Token**，并授予集成所需的权限。

---

## ⚙️ [03. 在 Home Assistant 中安装并登录集成](03-login-pve-pbs.md)
从 HACS 安装集成，并在 Home Assistant 中连接 PVE 或 PBS 的逐步说明。

---

## ❓ [04. 常见问题与故障排查](04-faq.md)
常见连接、权限、传感器、PBS 与性能问题，以及对应处理方法。

---

<p align="center">
  <img src="https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/img/logo_int_v4.png" alt="Proxmox Extended Sensors Logo" width="600"/>
</p>

---


## 🆕 本次中文文档升级

本次升级为项目补齐中文说明与安装配置文档，让中文用户可以不依赖英文文档完成完整部署流程。

新增内容包括：

- 根目录 `README.md` 新增中文项目说明与中文文档入口。
- `docs/zh/README.md` 作为中文文档导航页。
- `01-install-sensors.md`：硬件传感器、SMART 与 sensor API bridge 配置。
- `02-proxmox-config.md`：PVE/PBS 专用用户、角色、权限与 API Token 配置。
- `03-login-pve-pbs.md`：Home Assistant / HACS 安装以及 PVE/PBS 登录流程。
- `04-faq.md`：常见连接、权限、PBS、硬件指标和性能问题排查。

这次文档升级只补充说明和中文指南，不改变集成本身的运行逻辑或 Home Assistant 实体行为。

---

# 🚀 Proxmox Extended Sensors

## 简介

**Proxmox Extended Sensors 是一个 Home Assistant 自定义集成，用于对 Proxmox VE 和 Proxmox Backup Server（PBS）进行高级监控与基础控制。**

它不只是简单暴露原始指标，而是强调 **有用的信息洞察（System Insight）**：让你快速理解系统当前是否健康、是否存在压力，以及是否需要自动化告警或人工处理。

该集成可提供对节点、虚拟机、容器、存储、硬盘、备份任务和 PBS 数据的可视化，并支持部分控制能力。

---

## 🧠 System Insight（V3/V4）

从 V3 开始，集成从“技术指标集合”演进为面向基础设施状态的观测系统。

V4 进一步提供可解释的全局状态传感器，把复杂指标转换成更容易理解和自动化处理的状态：

- **Proxmox Node** → 节点整体状态（`Excellent`、`Warning`、`Critical` 等）
- **Node Score** → 综合健康评分
- **Node Stress / Overload** → 基于 CPU、负载、IO Wait 等压力指标判断节点是否过载
- **Backup Health** → 备份任务是否健康、是否失败或过期

这些状态非常适合用于 Home Assistant 仪表盘、通知和自动化。

---

## 🔍 主要能力

- **集群级监控**：汇总 Proxmox 集群状态、节点在线情况、失败任务和备份健康度。
- **挂载磁盘与网络存储**：识别本地挂载、CIFS、NFS 等存储，并提供使用率属性。
- **硬件传感器**：支持 CPU 温度、主板/芯片组传感器、风扇和 NVMe/SMART 数据。
- **虚拟机与容器监控**：显示 VM/CT 的运行状态与资源使用情况。
- **PBS 支持**：连接 Proxmox Backup Server，查看 datastore 和备份相关数据。
- **稳定异步架构**：使用异步协调器与并发控制，避免过度打满 Proxmox API。
- **安全认证**：推荐使用专用用户与 API Token；PBS 必须使用 API Token。

---

## 🧩 支持版本

- Proxmox VE 7.x / 8.x / 9.x
- Linux Kernel 6.x / 7.x
- Proxmox Backup Server 3.x / 4.x
- Home Assistant 2024.6+

---

## 🚀 建议安装顺序

1. 先在 Proxmox 节点上安装并验证硬件传感器：[`01-install-sensors.md`](01-install-sensors.md)
2. 再创建专用用户、角色权限和 API Token：[`02-proxmox-config.md`](02-proxmox-config.md)
3. 最后在 Home Assistant 中通过 HACS 安装并登录：[`03-login-pve-pbs.md`](03-login-pve-pbs.md)
4. 如果遇到问题，查看常见问题：[`04-faq.md`](04-faq.md)

---

## ⚠️ 重要说明

- Proxmox 官方 API 不暴露所有硬件传感器，因此硬件温度/风扇等数据需要额外的 sensor API bridge。
- 托管型或多租户 PBS（例如 Tuxis、Hetzner 等）通常无法提供底层硬件传感器、SMART 或真实磁盘指标。
- 推荐只在可信局域网或受控网络中暴露额外传感器服务。
- API Token 的 Secret 只会显示一次，请妥善保存。
