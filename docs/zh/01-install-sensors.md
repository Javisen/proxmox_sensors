# 🚀 步骤 1：传感器安装与配置

本指南说明如何准备 Proxmox 节点，让 Home Assistant 能够获取硬件数据，包括温度、物理传感器和 SMART 磁盘属性。

这些数据会被集成用于提供 **高级监控与 System Insight（V3/V4）**。

---

## 1. 安装依赖

为了启用硬件传感器和 SMART 数据，请在 Proxmox 节点上安装：

- **lm-sensors** → CPU、主板、芯片组、VRM、风扇等传感器
- **smartmontools** → HDD、SSD 和 NVMe 的 SMART 信息

```bash
apt update && apt install lm-sensors smartmontools -y
```

---

## 2. 硬件检测

运行检测向导：

```bash
sensors-detect
```

对所有问题回答 **YES**，或者按提示直接回车接受建议。

完成后，系统会检测所需模块，例如 Intel CPU 常见的 `coretemp`。

---

## 3. 模块持久化

检测结束时，你会看到类似提示：

```text
Do you want to add these lines automatically to /etc/modules? (yes/NO)
```

> [!CAUTION]
> **这里必须手动输入 `yes` 并按 Enter。** 如果只是直接按 Enter，会选择默认的 `NO`，重启后传感器模块可能不会自动加载。

---

## 4. 立即验证

如果不想重启，可以先手动加载模块并查看传感器：

```bash
modprobe coretemp
sensors
```

如果能看到温度、风扇或电压等信息，说明基础传感器已经可用。

---

## 5. 安装传感器服务（API Bridge）

Proxmox 官方 API 不暴露所有硬件传感器。因此，本集成使用一个小型服务作为桥接，让 Home Assistant 能够读取这些数据。

### 5.1 下载并安装脚本

在 Proxmox 服务器终端执行：

```bash
wget https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/scripts/pve-sensors-api.py -O /usr/local/bin/pve-sensors-api.py
chmod +x /usr/local/bin/pve-sensors-api.py
```

### 5.2 配置为 systemd 服务

创建服务文件：

```bash
cat <<EOF > /etc/systemd/system/pve-sensors.service
[Unit]
Description=PVE Sensors API (User Mode)
After=network.target

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/pve-sensors-api.py
Restart=always
RestartSec=10s

NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=full

[Install]
WantedBy=default.target
EOF
```

### 5.3 启用服务

```bash
systemctl daemon-reload
systemctl enable --now pve-sensors.service
```

### 5.4 最终验证

在浏览器中打开：

```text
http://YOUR_PROXMOX_IP:9000/sensors
```

如果返回包含温度和传感器信息的 JSON，说明服务工作正常。

---

## ✔ 结论

当满足以下条件后：

- `sensors` 能正确返回硬件数据
- `pve-sensors.service` 处于 active/running 状态
- `/sensors` HTTP 接口能返回 JSON

Home Assistant 就可以通过集成自动获取硬件传感器数据。
