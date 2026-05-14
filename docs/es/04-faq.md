# ❓ FAQ — Preguntas Frecuentes

Aquí encontrarás los problemas más comunes al usar **Proxmox Extended Sensors** y sus soluciones.

---

# 🔐 Problemas de conexión

## ❌ No puedo iniciar sesión

### ✔ Usa solo IP o dominio
Correcto:
- `192.168.1.10`  
- `pve.midominio.com`

Incorrecto:
- `http://...`
- `https://...`

---

### ✔ No incluyas el puerto
La integración lo detecta automáticamente.

---

### ✔ Revisa permisos

- PVE → `PVEAdmin`  
- PBS → `Administrator`  
- Deben estar asignados en `/`

---

### ✔ El Token debe estar activo
En Proxmox → API Tokens → **Enabled: Yes**

---

## ❌ “Permiso denegado” con Token

### ✔ Permisos en `/`
No deben asignarse a un nodo, sino a la raíz.

### ✔ Usuario sin permisos
El usuario padre debe tener rol válido.

---

# 🌡️ Sensores y hardware

## ❌ No aparecen temperaturas

Asegúrate de:


```bash
apt install lm-sensors
sensors-detect
modprobe coretemp
```

Y tener el servicio activo.

---

## ❌ No aparecen discos o SMART

- El disco debe soportarlo  
- NVMe en VMs → no disponible  
- Algunas controladoras no exponen datos  

---

## ❌ No aparecen VMs o CTs

- Revisa permisos (`PVEAdmin`)  
- En clúster, usa el nodo principal  

---

## 🗄️ PBS (Backup Server)

### ❌ No veo datos del datastore

### 🔒 PBS gestionado (Tuxis, Hetzner…)

No tendrás acceso a:

- Uso de disco  
- Deduplicación  
- Temperatura  
- CPU/RAM  
- SMART  

👉 Es una limitación del proveedor, no de la integración.

---

## 🧠 System Insight (V3/V4)

### ❓ ¿Qué es Node Score?

Es una evaluación global del estado del nodo basada en:

- CPU  
- Load  
- IO Wait  

Permite detectar rápidamente si un nodo está bajo carga.

---

### ❓ ¿Qué significa “Node Stress” o “Overload”?

Indica que el sistema está bajo presión:

- CPU alta  
- Carga elevada  
- Disco saturado  

👉 Útil para automatizaciones o alertas.

---

## 🔄 Rendimiento

### ❓ La integración tarda en actualizar

Es normal.

La integración usa un sistema optimizado para:

- Reducir carga en Proxmox  
- Evitar saturar la API  

Intervalo por defecto: ~10 segundos.

---

## 🧩 Uso general

### ❓ ¿Puedo usar varios servidores?

Sí.  
Puedes añadir múltiples instancias (PVE/PBS).

---

### 🔒 ¿Es seguro?

Sí:

- Usa API Tokens  
- No ejecuta comandos remotos  
- No modifica configuración  
- No abre puertos  

---

## 🧹 Eliminar sensores antiguos

1. Elimina la integración  
2. Reinicia Home Assistant  
3. Añádela de nuevo  

---

## 🧾 Checklist antes de abrir un Issue

Antes de reportar un problema:

- ✔ ¿Accedes a Proxmox desde el navegador?  
- ✔ ¿Usas solo IP o dominio?  
- ✔ ¿Token activo?  
- ✔ ¿Permisos en `/`?  
- ✔ ¿lm-sensors instalado?  
- ✔ ¿Reiniciaste Home Assistant?  
- ✔ ¿Revisaste logs?  

---

## 🚫 Limitaciones conocidas

### 🔒 PBS gestionado

Sin acceso a métricas internas (hardware, datastore, etc.)

---

### 🧊 Sensores en VMs

No existen sensores reales en máquinas virtuales.

---

### 📦 Discos sin SMART

Algunos discos/controladoras no exponen datos.

---

### 🔐 Permisos mal asignados

Si no están en `/`, la API falla.

---

### 🕒 Intervalos de actualización

Hay un retardo intencionado para evitar carga.

---

### 🧩 Clúster Proxmox

Conéctate al nodo principal.

---

### 🌐 Certificados SSL

Los certificados autofirmados son aceptados.
