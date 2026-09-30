# 🌡️ Schritt 1: Hardware-Sensoren und Sidecar

Diese Anleitung bereitet einen Proxmox-VE-Knoten für Hardwaredaten vor, die nicht über die Standard-Proxmox-API verfügbar sind. V5 nutzt den Sidecar unter anderem für Temperaturen, Speicherinformationen, Mounts und SMART und stellt zusätzlich **Sidecar Status** bereit.

## 1. Pakete installieren
```bash
apt update && apt install lm-sensors smartmontools -y
```
`lm-sensors` liefert unterstützte CPU-, Mainboard-, Chipsatz-, VRM- und Lüfterdaten; `smartmontools` SMART-Daten für HDD, SSD und unterstützte NVMe-Geräte.

## 2. Sensoren erkennen
```bash
sensors-detect
```
Folge dem Assistenten und aktiviere die für deine Hardware passenden Module. Werden Einträge für `/etc/modules` angeboten, stelle sicher, dass die benötigten Module für Neustarts gespeichert werden.

## 3. Prüfen
```bash
sensors
```
Bei Intel-Systemen mit `coretemp` kann bei Bedarf getestet werden:
```bash
modprobe coretemp
sensors
```
`coretemp` nicht auf Systemen erzwingen, die einen anderen Treiber verwenden.

## 4. Sidecar installieren

Führe den folgenden Befehl auf jedem PVE/PBS-Host aus, auf dem du den Hardware-Sidecar installieren möchtest:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/scripts/install-sidecar.sh)
```

Während der Installation wirst du aufgefordert, die IP-Adresse(n) deiner Home-Assistant-Instanz(en) einzugeben. Mehrere IP-Adressen können durch Kommas getrennt angegeben werden.

Nur die angegebenen IP-Adressen dürfen auf den Hardware-Sidecar zugreifen.

> **Hinweis:** Wenn der Sidecar bereits installiert ist, führe denselben Befehl erneut aus, um die bestehende Installation zu aktualisieren und die autorisierten Home-Assistant-IP-Adressen zu konfigurieren.

## 5. Sidecar prüfen

Überprüfe den Status des Sidecar-Dienstes:

```bash
systemctl status pve-sensors.service
```

Der Dienst sollte als `active (running)` angezeigt werden.

## 6. Verhalten bei Sidecar-Ausfall
V5 behält nach Möglichkeit die letzten gültigen Hardwarewerte. **Sidecar Status** zeigt pro PVE-Knoten den Zustand von Memory, Mounts, Sensors und SMART als `ok`, `degraded`, `error` oder `unknown`.

Weiter: [02. Proxmox-Benutzer und Berechtigungen](02-proxmox-config.md)
