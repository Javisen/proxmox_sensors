# 🔐 步骤 2：用户与权限配置

为了让 Home Assistant 安全地访问 Proxmox，建议 **不要直接使用 root 用户**。

更稳妥的方式是创建一个专用用户，并把集成需要的权限分配给它。

---

> ⚠️ **重要**
>
> 由于该集成支持 VM/CT 控制、备份、PBS 操作、节点和磁盘信息读取等高级功能，需要在 Proxmox 中授予较高权限。
>
> 这些权限允许：
>
> - 控制虚拟机和容器
> - 执行单个或批量备份
> - 读取节点、磁盘和任务信息
> - 与 Proxmox Backup Server（PBS）交互
>
> 虽然权限范围较广，但使用 **专用用户 + API Token** 可以让访问边界更加清晰、可控。

---

## 1. PVE 与 PBS 的区别

### 🖥️ Proxmox VE（PVE）

PVE 支持以下认证方式：

- 用户名 / 密码
- API Token

该用户需要具备 **PVEAdmin** 角色。

---

### 🗄️ Proxmox Backup Server（PBS）

PBS 要求使用 **API Token**，并且该用户需要具备 **Administrator** 角色。

目前没有一个更低权限的中间角色可以完整兼容该集成的所有功能。

---

## 2. 创建用户

1. 进入 **Datacenter → Permissions → Users**
2. 点击 **Add**
3. 配置：

- **User:** `homeassistant`
- **Realm:** `pve`
- **Password:** 如果你准备在 PVE 中使用密码登录，则填写密码

4. 保存修改

---

## 3. 分配权限

1. 进入 **Datacenter → Permissions**
2. 点击 **Add → User Permission**

### ✔ Proxmox VE（PVE）

- **Path:** `/`
- **User:** `homeassistant@pve`
- **Role:** `PVEAdmin`

### ✔ Proxmox Backup Server（PBS）

- **Path:** `/`
- **User:** `homeassistant@pve`
- **Role:** `Administrator`

> 💡 **为什么使用 `/` 全局路径？**
>
> 集成需要访问整个基础设施，包括节点、虚拟机、容器、磁盘、存储和任务。如果只授权到某个节点或资源，部分功能可能无法正常工作。

---

## 4. 创建 API Token

1. 进入 **Datacenter → Permissions → API Tokens**
2. 点击 **Add**
3. 配置：

- **User:** `homeassistant@pve`
- **Token ID:** `ha-token`
- **Privilege Separation:** ❌ 不勾选
- **Expire:** Never

---

### 🔍 为什么要关闭 “Privilege Separation”？

因为该 Token 需要继承父用户的完整权限。

如果启用该选项：

- Token 会只有受限权限
- 备份、控制和 PBS 相关功能可能无法正常工作

---

4. 创建 Token 时，Proxmox 会显示：

- **Token ID**
- **Secret**（只显示一次）

> [!WARNING]
> 请把 **Secret** 安全保存下来。
> 关闭窗口后将无法再次查看这个 Secret。

---

> [!TIP]
> ### 忘记复制 Secret 怎么办？
>
> 不需要删除 Token：
>
> 1. 在 Token 列表中选中它
> 2. 点击 **Regenerate**
> 3. 立即生成新的 Secret
>
> ⚠️ 记得同时更新 Home Assistant 中保存的 Token Secret。

---

## ✔ 结论

完成以下配置后：

- 已创建专用用户
- 已正确分配权限
- 已创建 API Token

集成就可以以相对安全、可控的方式连接到 Proxmox，并使用完整功能。
