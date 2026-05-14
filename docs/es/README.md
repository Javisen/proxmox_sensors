# 📚 Documentación y Guías

Estas guías cubren los pasos necesarios para configurar correctamente la integración y aprovechar todas sus funcionalidades.

---

## 🌡️ [01. Configuración de Sensores de Hardware](01-install-sensors.md)
Cómo instalar y configurar **lm-sensors** en tu nodo Proxmox para habilitar el monitoreo de temperatura y ventiladores.

---

## 🔑 [02. Configuración de Proxmox](02-proxmox-config.md)
Cómo crear un **usuario** y un **API Token** seguros en Proxmox (PVE y PBS) con los permisos mínimos necesarios.

---

## ⚙️ [03. Inicio de Sesión de la Integración (PVE y PBS)](03-login-pve-pbs.md)
Guía paso a paso para conectar la integración con tus servidores desde Home Assistant.

---

## ❓ [04. Preguntas Frecuentes y Solución de Problemas](04-faq.md)
Problemas comunes, dudas frecuentes y cómo resolverlos.

---

<p align="center">
  <img src="https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/img/logo_int_v4.png" alt="Proxmox Extended Sensors Logo" width="600"/>
</p>

---

# 🚀 Proxmox Extended Sensors

## Introducción

**Proxmox Extended Sensors es una integración para Home Assistant diseñada para proporcionar monitorización avanzada y control completo de Proxmox VE y Proxmox Backup Server (PBS).**

A diferencia de soluciones basadas únicamente en métricas, esta integración introduce un enfoque centrado en **información útil (insight)**, permitiendo entender no solo qué está ocurriendo en el sistema, sino también cómo está funcionando realmente.

Proporciona visibilidad completa de la infraestructura y añade capacidades de control directo sobre nodos, máquinas virtuales, contenedores, almacenamiento y servicios de backup.

---

## 🧠 System Insight (V3/V4)

A partir de la versión 3, la integración evolucionó desde una colección de métricas técnicas hacia un sistema de observabilidad orientado a infraestructura.

V4 introduce sensores capaces de interpretar el estado global del nodo y transformar métricas complejas en información útil y accionable:

- **Proxmox Node** → estado global del nodo (`Excellent`, `Warning`, `Critical`, etc.) con atributos enriquecidos de infraestructura  
- **Node Score** → evaluación numérica del rendimiento y salud general del sistema  
- **Load Average (1m / 5m / 15m)** → carga real del host  
- **IO Wait** → detección de presión y saturación de disco  
- **Uso de CPU por núcleo** → disponible para nodos, VMs y contenedores  
- **Telemetría de red del nodo** → cálculo inteligente de tráfico RX/TX agregado desde VMs y CTs  
- **Información avanzada de almacenamiento** → estado, capacidad y métricas detalladas de discos físicos y storages  

Estos sensores permiten detectar cuellos de botella, identificar degradación del sistema y construir automatizaciones mucho más inteligentes sin necesidad de herramientas externas adicionales.

---

## 🔍 Capacidades principales de V4

- Monitorización global de clúster Proxmox  
- Detección avanzada de discos montados (CIFS/NFS/local)  
- Telemetría inteligente de red y almacenamiento  
- Sensores agregados de salud e infraestructura  

### Monitorización completa de:

- Nodos  
- Máquinas virtuales (QEMU)  
- Contenedores (LXC)  
- Discos y almacenamiento  
- Proxmox Backup Server (PBS)  

### Funcionalidades avanzadas

- Acciones de control desde Home Assistant  
- Servicios de backup integrados  
- Compatibilidad total con PBS (incluyendo deduplicación)  
- Autenticación segura mediante tokens  
- Estructura limpia y consistente de entidades  
- Actualizaciones optimizadas y bajo consumo de recursos  

---

## 🧩 Versiones Soportadas

- Proxmox VE 7.x / 8.x / 9.x
- Compatible con Linux Kernel 6.x / 7.x
- Proxmox Backup Server 3.x / 4.x
- Home Assistant 2024.x o posterior

---

## 📑 Tabla de Contenidos

- [Características Clave](#-características-clave-v400)
- [Estado y Rendimiento del Nodo](#-estado-y-rendimiento-del-nodo)
- [Discos y SMART](#-discos-y-smart)
- [Máquinas Virtuales (QEMU)](#-máquinas-virtuales-qemu)
- [Contenedores (LXC)](#-contenedores-lxc)
- [Servicios de Backup](#-servicios-de-backup-vms-y-cts)
- [Proxmox Backup Server (PBS)](#-proxmox-backup-server-pbs)
- [Acciones de Control (PVE y PBS)](#-acciones-de-control-pve-y-pbs)
- [Instalación](#-instalación)
- [Guía Visual de Configuración](#-guía-visual-de-configuración)
- [Contribuciones](#-contribuciones-y-comunidad)

---

## 🔥 Características Clave de V4

### ⚙️ Configuración Mejorada

- Descubrimiento automático de nodos  
- Selección manual opcional  
- Configuración más simple y guiada  
- Compatibilidad con API Tokens (PVE/PBS)  
- Detección inteligente de permisos limitados  

---

### 🌐 Monitorización de Clúster (NUEVO)

- Sensores globales del clúster Proxmox  
- Estado de backups y tareas fallidas  
- Nodos online/offline  
- Uso agregado de CPU y RAM  
- Conteo global de VMs y CTs  

---

### 💽 Discos Montados y Almacenamiento (NUEVO)

- Detección automática de discos montados  
- Compatibilidad con CIFS / SMB y NFS  
- Sensores de integridad y mounts faltantes  
- Exclusión inteligente de tmpfs y pseudo-mounts  
- Métricas detalladas de uso y capacidad  

---

### 🌡️ Monitorización Avanzada de Hardware

- Temperaturas en tiempo real (CPU, VRM, chipset, discos)  
- Sensores de ventiladores y voltajes  
- Filtrado inteligente de sensores válidos  
- Sensores unificados de temperatura (CPU + NVMe)  
- Compatibilidad avanzada Intel / AMD / ACPI / NVMe 

> Requiere `lm-sensors` en el host Proxmox

---

### 🧠 Estado y Rendimiento del Nodo

- CPU, RAM, uptime, kernel y versión de PVE  
- Monitorización de red (RX/TX)  
- Tareas y estado del sistema  
- Métricas avanzadas de carga y rendimiento  
- Node Score y estado global de infraestructura  

---

### 💾 Discos y SMART

- Sensores agrupados por disco físico  
- Espacio total/usado y métricas avanzadas  
- Atributos SMART (HDD, SSD, NVMe)  
- Temperaturas por tipo de disco  
- Métricas NVMe avanzadas y estado de salud  

---

### 🖥️ Máquinas Virtuales (QEMU)

- Estado, CPU, memoria y disco  
- Red RX/TX  
- Información básica y uptime  
- Uso de CPU por núcleo  
- Acciones de control desde Home Assistant  

---

### 📦 Contenedores (LXC)

- Estado, CPU, memoria y disco  
- Red RX/TX  
- Información básica y uptime  
- Uso de CPU por núcleo  
- Acciones de control desde Home Assistant  

---

## 💾 Servicios de Backup (VMs y CTs)

La integración permite crear backups directamente desde Home Assistant, totalmente compatibles con Proxmox VE y PBS.

### 🟦 Backup Individual

- Soporta múltiples IDs (coma separada)  
- Modos: snapshot / suspend / stop  
- Compresión: zstd / gzip / lzo / none  
- Compatible con PBS y deduplicación  

### 🟩 Backup Masivo

- Backup de todos los recursos de un nodo  
- Control de concurrencia y tiempos  
- Ideal para automatización  
- Compatible con grandes infraestructuras  

Los backups se nombran automáticamente como:

```text
HA-{{vmid}}-{{guestname}}
```

Totalmente compatibles con PBS, incluyendo deduplicación y cadenas existentes.

---

## 🗄️ Proxmox Backup Server (PBS)

Monitorización avanzada de datastore y tareas:

- Uso total, libre y porcentaje  
- Ratio de deduplicación  
- Estado del último backup  
- Errores y resumen de tareas  
- Estado del Garbage Collector  
- Información detallada de tareas  

---

## 🎛️ Acciones de Control (PVE & PBS)

**Nodo:**
- Apagar / Reiniciar / Wake-on-LAN  

**Máquinas virtuales:**
- Start / Stop / Shutdown / Reboot / Reset  
- Pause / Resume / Hibernate  

**Contenedores:**
- Start / Stop / Shutdown / Reboot  

**PBS:**
- Garbage Collector  
- Prune  
- Verify  
- Sync  

---

## 🎨 Organización y estructura

- Sensores agrupados automáticamente en:
  1. Cluster
  2. Nodo
  3. Discos físicos
  4. Máquinas virtuales
  5. Contenedores
  6. Almacenamiento / Datastores
  7. PBS y tareas

- Nombres consistentes y claros para facilitar dashboards y automatizaciones  

---

## 🧩 Instalación

### 🔹 Via HACS (recomendado)

1. Abrir **HACS → Integraciones**  
2. Añadir repositorio personalizado  
3. Buscar **Proxmox Extended Sensors**  
4. Instalar y reiniciar Home Assistant  
5. Añadir la integración desde ajustes  

### 🔹 Instalación manual

1. Copiar en `/config/custom_components/proxmox_sensors`  
2. Reiniciar Home Assistant  
3. Añadir la integración  

---

## 🧭 Guía Visual de Configuración

A continuación encontrarás un recorrido visual completo del proceso de configuración, incluyendo métodos de acceso, selección de recursos y pasos de instalación.

<details>
  <summary>🪪 Conexión con el Servidor</summary>
  <p align="center">
    <img src="../../img/install/setup_pve_1.png" alt="Conexión Proxmox" width="600">
  </p>
  <p align="center"><i>No es necesario incluir "http://" o "https://". Se gestiona automáticamente.</i></p>
</details>

<details>
  <summary>🪪 Inicio de sesión con Usuario y Contraseña (solo PVE)</summary>
  <p align="center">
    <img src="../../img/install/access_passw.png" alt="Login usuario y contraseña" width="600">
  </p>
  <p align="center"><i>Asegúrate de usar el realm correcto (`pam` o `pve`).</i></p>
</details>

<details> 
  <summary>🪪 Inicio de sesión con Usuario y Token (PVE y PBS)</summary>
  <p align="center">
    <img src="../../img/install/access_token.png" alt="Login con token" width="600">
  </p>
  <p align="center"><i>En el campo Token_id solo debes introducir el nombre del token.</i></p>
</details>

<details>
  <summary>🧠 Selección de Nodos (V4)</summary>
  <p align="center">
    <img src="../../img/install/node_select.png" alt="Selección de nodos" width="600">
  </p>
  <p align="center"><i>Selecciona los nodos detectados automáticamente o define manualmente cuáles incluir.</i></p>
</details>

<details>
  <summary>⚙️ Selección de Recursos</summary>
  <p align="center">
    <img src="../../img/install/resources_select.png" alt="Selección de recursos" width="600">
  </p>
  <p align="center"><i>Selecciona los CTs, VMs y storages que deseas incluir, junto con las opciones correspondientes.</i></p>
</details>

---

**Si esta integración te resulta útil, considera dejar una ⭐ en GitHub.**

---

## 🤝 Contribuciones y Comunidad

Las contribuciones son bienvenidas. Puedes abrir issues o pull requests.  
Repositorio: https://github.com/Javisen/proxmox_sensors

---

<p align="center"><i>Mantenido por Javisen - Licencia MIT</i></p>
