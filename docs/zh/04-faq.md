# ❓ FAQ — 常见问题

这里整理了使用 **Proxmox Extended Sensors** 时最常见的问题与处理方法。

---

# 🔐 连接问题

## ❌ 无法登录

### ✔ 只填写 IP 或域名

正确：

- `192.168.1.10`
- `pve.mydomain.com`

错误：

- `http://...`
- `https://...`

---

### ✔ 不要填写端口

集成会自动检测端口。

---

### ✔ 检查权限

- PVE → `PVEAdmin`
- PBS → `Administrator`
- 权限必须分配在 `/`

---

### ✔ Token 必须处于启用状态

在 Proxmox → API Tokens 中确认 **Enabled: Yes**。

---

## ❌ 使用 Token 时提示 “Permission denied”

### ✔ 权限应分配在 `/`

不要只分配到某个节点，而应分配到根路径 `/`。

### ✔ 父用户也需要权限

Token 所属的父用户必须拥有有效角色。

---

# 🌡️ 传感器与硬件

## ❌ 不显示温度

请确认已经执行：

```bash
apt install lm-sensors
sensors-detect
modprobe coretemp
```

并确认 `pve-sensors.service` 已启动。

---

## ❌ 不显示磁盘或 SMART 数据

可能原因：

- 磁盘本身不支持 SMART
- VM 内的 NVMe 通常不可用
- 部分 RAID/HBA/存储控制器不暴露这些数据

---

## ❌ 不显示 VM 或 CT

请检查：

- 权限是否为 `PVEAdmin`
- 集群环境中是否连接到了主节点或可访问完整资源的节点

---

# 🗄️ PBS（Backup Server）

## ❌ 看不到 datastore 数据

### 🔒 托管型 PBS（Tuxis、Hetzner 等）

你通常无法访问：

- 磁盘使用率
- 去重信息
- 温度
- CPU/RAM
- SMART

👉 这是服务商限制，不是集成本身的问题。

---

# 🧠 System Insight（V3/V4）

## ❓ Node Score 是什么？

它是基于节点状态计算出的全局评分，通常会考虑：

- CPU
- 系统负载
- IO Wait

它可以帮助你快速判断节点是否处于压力状态。

---

## ❓ “Node Stress” 或 “Overload” 是什么意思？

表示系统正在承受压力，例如：

- CPU 使用率高
- 系统负载高
- 磁盘 IO 饱和

👉 这些状态适合用于自动化、通知或告警。

---

# 🔄 性能

## ❓ 集成更新很慢

这是正常设计。

集成使用优化后的更新机制来：

- 降低 Proxmox 负载
- 避免打满 API

默认更新间隔大约为 10 秒。

---

# 🧩 一般使用

## ❓ 可以添加多台服务器吗？

可以。

你可以添加多个集成实例，分别连接 PVE 或 PBS。

---

## 🔒 安全吗？

相对安全：

- 使用 API Token
- 不执行远程命令
- 不修改 Proxmox 配置
- 不额外开放 Proxmox 端口

> 如果你启用了传感器 API bridge，请确保只在可信网络中使用，或自行加上网络访问控制。

---

## 🧹 如何移除旧传感器？

1. 删除集成
2. 重启 Home Assistant
3. 重新添加集成

---

## 🧾 提 Issue 前检查清单

报告问题前，请先确认：

- ✔ 浏览器能访问 Proxmox
- ✔ Host 只填写了 IP 或域名
- ✔ Token 已启用
- ✔ 权限已分配到 `/`
- ✔ 已安装 `lm-sensors`
- ✔ 已重启 Home Assistant
- ✔ 已查看 Home Assistant 日志

---

# 🚫 已知限制

## 🔒 托管型 PBS

通常无法访问内部硬件指标。

---

## 🧊 虚拟机里的传感器

虚拟机里通常没有真实硬件传感器。

---

## 📦 不支持 SMART 的磁盘

部分磁盘或控制器不会暴露 SMART 数据。

---

## 🔐 权限分配不正确

如果权限没有分配在 `/`，API 调用可能失败。

---

## 🕒 更新间隔

集成会故意保留一定更新间隔，以避免增加 Proxmox 负载。

---

## 🧩 Proxmox 集群

建议连接到可以访问完整集群资源的主节点。

---

## 🌐 SSL 证书

自签名证书可以使用。
