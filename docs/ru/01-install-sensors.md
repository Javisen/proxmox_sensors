# 🌡️ Шаг 1: Аппаратные датчики и Sidecar

Руководство подготавливает узел Proxmox VE к чтению аппаратных данных, которых нет в стандартном API Proxmox. V5 использует sidecar для температур, памяти, mounts и SMART и добавляет **Sidecar Status**.

## 1. Установить пакеты
```bash
apt update && apt install lm-sensors smartmontools -y
```

## 2. Обнаружить датчики
```bash
sensors-detect
```
Следуйте мастеру и включите подходящие модули. Если предлагается запись в `/etc/modules`, сохраните необходимые модули для загрузки после перезапуска.

## 3. Проверить
```bash
sensors
```
Для Intel с `coretemp`, если требуется:
```bash
modprobe coretemp
sensors
```
Не используйте `coretemp` принудительно на системах с другим драйвером.

## 4. Установка Sidecar

Выполните следующую команду на каждом хосте PVE/PBS, на котором вы хотите установить Hardware Sidecar:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/scripts/install-sidecar.sh)
```

Во время установки вам будет предложено ввести IP-адрес или IP-адреса ваших экземпляров Home Assistant. Несколько IP-адресов можно указать через запятую.

Доступ к Hardware Sidecar будет разрешён только с указанных IP-адресов.

> **Примечание:** Если Sidecar уже установлен, выполните ту же команду ещё раз, чтобы обновить существующую установку и настроить разрешённые IP-адреса Home Assistant.

## 5. Проверка Sidecar

Проверьте состояние службы Sidecar:

```bash
systemctl status pve-sensors.service
```

Служба должна отображаться как `active (running)`.

## 6. При сбое
V5 по возможности сохраняет последние корректные аппаратные значения. **Sidecar Status** показывает Memory, Mounts, Sensors и SMART как `ok`, `degraded`, `error` или `unknown`.

Далее: [02. Пользователь и права Proxmox](02-proxmox-config.md)
