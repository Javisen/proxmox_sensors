# 🌡️ Крок 1: Апаратні датчики та Sidecar

Посібник готує вузол Proxmox VE до апаратних даних, яких немає у стандартному API Proxmox. V5 використовує sidecar для температур, пам'яті, mounts і SMART та додає **Sidecar Status**.

## 1. Встановити пакети
```bash
apt update && apt install lm-sensors smartmontools -y
```

## 2. Виявити датчики
```bash
sensors-detect
```
Дотримуйтесь майстра та активуйте відповідні модулі. Якщо пропонується запис до `/etc/modules`, збережіть необхідні модулі для завантаження після перезапуску.

## 3. Перевірити
```bash
sensors
```
Для Intel із `coretemp`, якщо потрібно:
```bash
modprobe coretemp
sensors
```
Не використовуйте `coretemp` примусово на системах з іншим драйвером.

---

## 4. Встановлення Sidecar

Виконайте наступну команду на кожному хості PVE/PBS, на якому ви хочете встановити Hardware Sidecar:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/scripts/install-sidecar.sh)
```

Під час встановлення вам буде запропоновано ввести IP-адресу або IP-адреси ваших екземплярів Home Assistant. Кілька IP-адрес можна вказати через кому.

Доступ до Hardware Sidecar буде дозволено лише з указаних IP-адрес.

> **Примітка:** Якщо Sidecar уже встановлено, виконайте ту саму команду ще раз, щоб оновити наявну інсталяцію та налаштувати дозволені IP-адреси Home Assistant.

## 5. Перевірка Sidecar

Перевірте стан служби Sidecar:

```bash
systemctl status pve-sensors.service
```

Служба повинна відображатися як `active (running)`.

---

## 6. При збої
V5 за можливості зберігає останні коректні апаратні значення. **Sidecar Status** показує Memory, Mounts, Sensors і SMART як `ok`, `degraded`, `error` або `unknown`.

Далі: [02. Користувач і дозволи Proxmox](02-proxmox-config.md)
