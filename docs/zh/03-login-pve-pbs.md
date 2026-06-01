# 🔌 步骤 3：在 Home Assistant 中安装并登录集成

要在 Home Assistant 中显示温度、硬件传感器、磁盘、PBS、虚拟机和容器数据，需要安装 **Proxmox Extended Sensors** 集成。

---

## 1. 通过 HACS 安装

这是一个自定义集成，需要先添加到 HACS：

1. 进入 **HACS → Integrations**
2. 点击右上角 **三个点**
3. 选择 **Custom repositories**
4. 添加仓库：
   `https://github.com/ha-china/proxmox_sensors_cn/`
5. **Category** 选择 `Integration`
6. 安装集成并 **重启 Home Assistant**

---

## 2. 添加集成

重启后：

1. 进入 **Settings → Devices & Services**
2. 点击 **Add Integration**
3. 搜索 **Proxmox Extended Sensors**

---

## 3. 连接配置

### 🔹 Host

- **局域网地址:** `192.168.1.50`
- **外部域名:** `proxmox.mydomain.com`

> 不需要填写 `http://` 或 `https://`，集成会自动检测。

---

### 🔹 Server type

- **PVE** → Proxmox Virtual Environment
- **PBS** → Proxmox Backup Server

---

### 🔹 Authentication method

- **Username + password** → 仅 PVE 可用
- **API Token** → 推荐方式；PBS 必须使用

---

## 🔐 方式 A：用户名和密码（仅 PVE）

字段：

- **User:** `user@realm`
  - 示例：`homeassistant@pve`
- **Password:** 用户密码

> 💡 从 V3 开始，节点会自动检测，不需要手动填写。

---

## 🔐 方式 B：API Token（推荐）

字段：

- **User:** `user@realm`
- **Token ID:** 只填写 Token 名称，例如 `ha-token`
- **Token Secret:** Proxmox 创建 Token 时生成的 Secret

> ⚠️ 不要把 Token ID 填成 `user@pve!token` 这种完整格式。

---

## 🧠 资源选择（PVE）

连接成功后，集成会自动检测可用资源。

你可以选择：

- 虚拟机（VM）
- 容器（CT）
- 物理磁盘
- 存储

> 💡 只选择你真正需要的资源，可以让 Home Assistant 更清爽，也能减少不必要的实体数量。

---

## 🧭 图形化安装指南

下面是带截图的完整流程：

<details>
  <summary>🪪 服务器连接</summary>
  <p align="center">
    <img src="../../img/install/setup_pve_1.png" alt="Proxmox Connection" width="600">
  </p>
  <p align="center"><i>不需要填写 http/https。</i></p>
</details>

<details>
  <summary>🪪 使用用户名和密码登录（PVE）</summary>
  <p align="center">
    <img src="../../img/install/access_passw.png" alt="User Login" width="600">
  </p>
  <p align="center"><i>请使用正确 realm，例如 pam 或 pve。</i></p>
</details>

<details>
  <summary>🪪 使用 Token 登录（PVE 和 PBS）</summary>
  <p align="center">
    <img src="../../img/install/access_token.png" alt="Token Login" width="600">
  </p>
  <p align="center"><i>Token ID 只填写 Token 名称。</i></p>
</details>

<details>
  <summary>🧠 节点选择（V3）</summary>
  <p align="center">
    <img src="../../img/install/node_select.png" alt="Node Selection" width="600">
  </p>
  <p align="center"><i>节点会自动检测，也可以手动选择。</i></p>
</details>

<details>
  <summary>⚙️ 资源选择</summary>
  <p align="center">
    <img src="../../img/install/resources_select.png" alt="Resource Selection" width="600">
  </p>
</details>

---

## ⚠️ 托管型 PBS 环境说明

如果你使用的是 **托管型或多租户 PBS**（例如 Tuxis、Hetzner 等）：

- 你通常无法访问硬件传感器
- 看不到温度或物理磁盘
- 没有节点级指标

这是正常现象，因为：

- 你没有底层硬件访问权限
- 服务商限制了系统能力
- 低层级权限不存在或不可用

**结果：**
通常只能显示有限的 datastore 数据。
