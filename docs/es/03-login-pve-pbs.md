# 🔌 Paso 3: Instalación de la Integración en Home Assistant

Para visualizar todos los datos (temperaturas, sensores de hardware, discos, PBS, VMs y CTs), utilizaremos la integración **Proxmox Extended Sensors**.

---

## 1. Instalación mediante HACS

Al ser una integración personalizada, primero debes añadirla a HACS:

1. Ve a **HACS → Integraciones**  
2. Haz clic en los **tres puntos** (arriba a la derecha)  
3. Selecciona **Repositorios personalizados**  
4. Añade este repositorio:  
   `https://github.com/Javisen/proxmox_sensors/`  
5. En **Categoría**, selecciona `Integración`  
6. Instala la integración y **reinicia Home Assistant**

---

## 2. Añadir la integración

Tras reiniciar:

1. Ve a **Ajustes → Dispositivos y Servicios**  
2. Haz clic en **Añadir Integración**  
3. Busca **Proxmox Extended Sensors**

---

## 3. Configuración de conexión

### 🔹 Host
- **Red local:** `192.168.1.50`  
- **Acceso externo:** `proxmox.midominio.com`  

> No es necesario incluir `http://` o `https://`. Se detecta automáticamente.

---

### 🔹 Tipo de servidor
- **CLUSTER** → Proxmox Cluster
- **PVE** → Proxmox Virtual Environment  
- **PBS** → Proxmox Backup Server  

---

### 🔹 Método de autenticación

- **Usuario + contraseña** → solo en PVE y Cluster
- **API Token** → Obligatorio en PBS  

---

## 🔐 Opción A: Usuario y contraseña (solo PVE)

Campos:

- **User:** `usuario@realm`  
  - Ejemplo: `homeassistant@pve`  
- **Password:** contraseña del usuario  

> 💡 Desde la V3, el nodo se detecta automáticamente. No es necesario introducirlo manualmente.

---

## 🔐 Opción B: API Token (recomendado)

Campos:

- **User:** `usuario@realm`  
- **Token ID:** solo el nombre → `ha-token`  
- **Token Secret:** el secret generado en Proxmox  

> ⚠️ No uses el formato `usuario@pve!token`

---

## 🧠 Selección de recursos (PVE)

Tras conectar, la integración detectará automáticamente los recursos disponibles.

Podrás seleccionar:

- Máquinas virtuales (VMs)  
- Contenedores (CTs)  
- Discos físicos  
- Storages  

> 💡 Selecciona solo lo necesario para mantener Home Assistant limpio y eficiente.

---

## 🧭 Guía Visual de Instalación

A continuación se muestra el proceso completo con capturas:

<details>
  <summary>🪪 Conexión con el servidor</summary>
  <p align="center">
    <img src="../../img/install/setup_pve_1.png" alt="Conexión Proxmox" width="600">
  </p>
  <p align="center"><i>No es necesario incluir http/https.</i></p>
</details>

<details>
  <summary>🪪 Login con usuario y contraseña (PVE)</summary>
  <p align="center">
    <img src="../../img/install/access_passw.png" alt="Login usuario" width="600">
  </p>
  <p align="center"><i>Usa el realm correcto (pam o pve).</i></p>
</details>

<details>
  <summary>🪪 Login con token (PVE y PBS)</summary>
  <p align="center">
    <img src="../../img/install/access_token.png" alt="Login token" width="600">
  </p>
  <p align="center"><i>Introduce solo el nombre del token en Token ID.</i></p>
</details>

<details>
  <summary>🧠 Selección de nodos (V3)</summary>
  <p align="center">
    <img src="../../img/install/node_select.png" alt="Selección nodos" width="600">
  </p>
  <p align="center"><i>Los nodos se detectan automáticamente y pueden seleccionarse manualmente.</i></p>
</details>

<details>
  <summary>⚙️ Selección de recursos</summary>
  <p align="center">
    <img src="../../img/install/resources_select.png" alt="Selección recursos" width="600">
  </p>
</details>

---

## ⚠️ Nota sobre PBS en entornos gestionados

Si utilizas un PBS **gestionado o multi-tenant** (Tuxis, Hetzner, etc.):

- No tendrás acceso a sensores de hardware  
- No verás temperaturas ni discos físicos  
- No habrá métricas de nodo  

Esto es normal porque:

- No tienes acceso al hardware real  
- El proveedor restringe el sistema  
- No existen permisos de bajo nivel  

**Resultado:**  
Solo se mostrarán datos limitados del datastore.

---