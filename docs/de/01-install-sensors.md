# 🚀 Schritt 1: Installation und Konfiguration der Sensoren

Diese Anleitung erklärt, wie der Proxmox-Knoten vorbereitet wird, um Hardware-Daten bereitzustellen und es Home Assistant zu ermöglichen, Temperaturen, physische Sensoren und SMART-Attribute der Festplatten zu erfassen.

Diese Daten werden von der Integration genutzt, um **erweiterte Überwachung und System Insight (V3/V4)** bereitzustellen.

---

## 1. Installation der Abhängigkeiten

Um alle Hardware- und SMART-Sensoren zu aktivieren, installiere:

- **lm-sensors** → CPU, Mainboard, Chipsatz, VRM, Lüfter
- **smartmontools** → SMART-Informationen von HDD, SSD und NVMe

apt update && apt install lm-sensors smartmontools -y

## 2. Hardware-Erkennung

* **Führe den Assistenten aus:**

```bash
sensors-detect
```

Antworte mit **YES** (oder drücke Enter) auf alle Fragen.

Nach Abschluss erkennt das System die erforderlichen Module (zum Beispiel: coretemp bei Intel-CPUs).

## 3. Module dauerhaft laden

Am Ende des Prozesses erscheint diese Frage:

Do you want to add these lines automatically to /etc/modules? (yes/NO)

> [!CAUTION]
> **Du musst manuell `yes` eingeben und Enter drücken.** Drückst du nur Enter, wird standardmäßig `NO` ausgewählt und die Sensoren werden nach einem Neustart nicht geladen.

## 4. Sofortige Überprüfung

Um die Sensoren ohne Neustart zu aktivieren:

```bash
modprobe coretemp
sensors
```

## 🚀 Schritt 5: Installation des Sensor-Servers (API Bridge)

Die offizielle Proxmox-API legt nicht alle Hardware-Sensoren offen.
Daher verwendet diese Integration einen kleinen Dienst, der als Brücke fungiert.

5.1. **Skript herunterladen und installieren**
Führe diese Befehle auf dem Terminal deines Proxmox-Servers aus:

```bash
wget https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/scripts/pve-sensors-api.py -O /usr/local/bin/pve-sensors-api.py
chmod +x /usr/local/bin/pve-sensors-api.py
```

5.2. **Als Systemdienst konfigurieren**

Erstelle die Dienstdatei:
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
5.3. **Aktivierung**

```bash
systemctl daemon-reload
systemctl enable --now pve-sensors.service
```


5.4. **Abschließende Überprüfung**
Öffne im Browser:
```
http://DEINE_PROXMOX_IP:9000/sensors
```
Wenn ein JSON mit Temperaturen und Sensoren erscheint, funktioniert der Dienst korrekt.

## ✔ Fazit

Sobald:
- sensors korrekt Daten zurückgibt
- der Dienst pve-sensors.service aktiv ist

kann Home Assistant alle Hardware-Daten automatisch abrufen, ohne zusätzliche Konfiguration.
