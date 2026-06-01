# 🚀 Шаг 1: Установка и настройка датчиков

**В данном руководстве объясняется, как подготовить узел Proxmox для передачи данных об оборудовании и обеспечить доступность показаний температуры и данных SMART для Home Assistant.**


## 1. Установка зависимостей

*Чтобы интеграция могла считывать данные со всех аппаратных датчиков и атрибуты SMART дисков, необходимо установить в Proxmox следующие инструменты:*

- **lm-sensors** → Датчики процессора, материнской платы, чипсета, VRM, вентиляторов…**
- **smartmontools** → Информация SMART для HDD, SSD и NVMe**


```bash

apt update && apt install lm-sensors smartmontools -y

```

## 2. Определение оборудования

* **Запустите мастер определения для поиска необходимых модулей:**


```bash

sensors-detect

```

**Отвечайте YES (или нажимайте Enter) на все вопросы. По завершении система определит необходимые модули (например, `coretemp` для процессоров Intel).**


## 3. Автозагрузка модулей

**Чтобы датчики активировались автоматически при перезагрузке сервера, мастер `sensors-detect` задаст важный вопрос в конце процесса:**


`Do you want to add these lines automatically to /etc/modules? (yes/NO)`



> [!CAUTION]
> **Вы должны вручную написать `yes` и нажать Enter.** Если вы просто нажмете Enter, ничего не написав, система выберет `NO` по умолчанию. В этом случае датчики не будут загружаться после перезагрузки, и Home Assistant перестанет получать данные о температуре.



## 4. Немедленная проверка

**Чтобы активировать датчики прямо сейчас без перезагрузки, выполните:**



```bash

# Загрузка определенных модулей (пример для Intel)

modprobe coretemp

# Проверка отображения температуры

sensors

```

## 🚀 Шаг 5: Установка сервера датчиков (API Bridge)
**Официальный API Proxmox не передает данные всех аппаратных датчиков, поэтому необходимо установить небольшой скрипт, который будет служить мостом между Proxmox и Home Assistant.**

1. **Загрузка и установка скрипта**
Выполните эти команды в терминале вашего сервера Proxmox:
```bash
# Скачивание скрипта из репозитория
wget https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/scripts/pve-sensors-api.py -O /usr/local/bin/pve-sensors-api.py

# Предоставление прав на выполнение
chmod +x /usr/local/bin/pve-sensors-api.py
```
2. **Настройка в качестве системной службы**
Создайте файл службы:
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

3. **Немедленная активация**

```bash
systemctl daemon-reload
systemctl enable --now pve-sensors
```

4. **Финальная проверка**
Откройте в браузере:
```
http://IP_ВАШЕГО_PROXMOX:9000/sensors
```

Если появится JSON-ответ с температурами и датчиками, значит сервер работает правильно.

## ✔ Заключение

**Как только команда sensors начнет возвращать показания, а служба pve-sensors станет активной, Home Assistant сможет получать все данные об оборудовании без необходимости дополнительной настройки.**
