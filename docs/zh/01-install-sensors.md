# 🌡️ 第 1 步：硬件传感器与 Sidecar

本指南用于准备 Proxmox VE 节点，以读取标准 Proxmox API 未提供的硬件数据。V5 使用 sidecar 获取温度、内存、mount 和 SMART 数据，并提供 **Sidecar Status**。

## 1. 安装软件包
```bash
apt update && apt install lm-sensors smartmontools -y
```

## 2. 检测传感器
```bash
sensors-detect
```
按照向导启用适合硬件的模块。如果提示写入 `/etc/modules`，请确保所需模块在重启后仍会加载。

## 3. 验证
```bash
sensors
```
Intel 系统使用 `coretemp` 时，如有需要：
```bash
modprobe coretemp
sensors
```
不要在使用其他驱动的系统上强制加载 `coretemp`。

## 4. 安装 Sidecar

在每个需要安装 Hardware Sidecar 的 PVE/PBS 主机上运行以下命令：

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/scripts/install-sidecar.sh)
```

安装过程中，系统会提示你输入 Home Assistant 实例的 IP 地址。可以输入多个 IP 地址，并使用逗号分隔。

只有指定的 IP 地址才允许访问 Hardware Sidecar。

> **注意：** 如果已经安装了 Sidecar，请再次运行相同的命令以更新现有安装，并配置允许访问的 Home Assistant IP 地址。

## 5. 检查 Sidecar

检查 Sidecar 服务的状态：

```bash
systemctl status pve-sensors.service
```

服务应显示为 `active (running)`。

## 6. Sidecar 故障时
V5 会尽可能保留最后一次有效硬件值。**Sidecar Status** 将 Memory、Mounts、Sensors 和 SMART 显示为 `ok`、`degraded`、`error` 或 `unknown`。

下一步：[02. Proxmox 用户与权限](02-proxmox-config.md)
