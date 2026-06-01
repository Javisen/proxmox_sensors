# 🚀 Paso 1: Instalación y configuración de sensores

Esta guía explica cómo preparar el nodo Proxmox para exponer datos de hardware y permitir que Home Assistant obtenga temperaturas, sensores físicos y atributos SMART de los discos.

Estos datos son utilizados por la integración para ofrecer **monitorización avanzada y System Insight (V3)**.

---

## 1. Instalación de dependencias

Para habilitar todos los sensores de hardware y SMART, instala:

- **lm-sensors** → CPU, placa base, chipset, VRM, ventiladores  
- **smartmontools** → Información SMART de HDD, SSD y NVMe  

```bash
apt update && apt install lm-sensors smartmontools -y

```

## 2. Detección de hardware

* **Ejecuta el asistente:**


```bash

sensors-detect

```

Responde **YES** (o pulsa Enter) a todas las preguntas.

Al finalizar, el sistema detectará los módulos necesarios (por ejemplo: ``coretemp`` en CPUs Intel).


## 3. Persistencia de módulos

Al final del proceso, aparecerá esta pregunta:


`Do you want to add these lines automatically to /etc/modules? (yes/NO)`



> [!CAUTION]
> **Debes escribir `yes` manualmente y pulsar Enter.** Si solo pulsas Enter, se seleccionará `NO` por defecto y los sensores no se cargarán tras reiniciar



## 4. Verificación inmediata

Para activar los sensores sin reiniciar:


```bash

modprobe coretemp
sensors

```

## 🚀 Paso 5: Instalación del Servidor de Sensores (API Bridge)
La API oficial de Proxmox no expone todos los sensores de hardware.
Por ello, esta integración utiliza un pequeño servicio que actúa como puente.

5.1. **Descarga e instalación del script**
Ejecuta estos comandos en la terminal de tu servidor Proxmox:

```bash
wget https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/scripts/pve-sensors-api.py -O /usr/local/bin/pve-sensors-api.py

chmod +x /usr/local/bin/pve-sensors-api.py
```

5.2. **Configuración como servicio del sistema**

Crea el archivo de servicio:

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

5.3. **Activación**

```bash

systemctl daemon-reload
systemctl enable --now pve-sensors.service

```

5.4. **Verificación final**
Abre en tu navegador:

```
http://TU_IP_PROXMOX:9000/sensors

```

Si aparece un JSON con temperaturas y sensores, el servicio está funcionando correctamente.

## ✔ Conclusión

Una vez que:
- `sensors` devuelve datos correctamente
- El servicio pve-sensors.service está activo


Home Assistant podrá obtener todos los datos de hardware automáticamente, sin configuraciones adicionales.
