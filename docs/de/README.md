# 📚 Dokumentation und Anleitungen

Diese Anleitungen decken die notwendigen Schritte ab, um die Integration korrekt zu konfigurieren und alle ihre Funktionen voll auszuschöpfen.

---

## 🌡️ [01. Konfiguration von Hardware-Sensoren](01-install-sensors.md)
So installieren und konfigurieren Sie **lm-sensors** auf Ihrem Proxmox-Knoten, um die Überwachung von Temperatur und Lüftern zu aktivieren.

---

## 🔑 [02. Konfiguration von Proxmox](02-proxmox-config.md)
So erstellen Sie einen sicheren **Benutzer** und ein **API-Token** in Proxmox (PVE und PBS) mit den minimal erforderlichen Berechtigungen.

---

## ⚙️ [03. Anmeldung bei der Integration (PVE und PBS)](03-login-pve-pbs.md)
Schritt-für-Schritt-Anleitung zum Verbinden der Integration mit Ihren Servern von Home Assistant aus.

---

## ❓ [04. Häufig gestellte Fragen und Problemlösungen](04-faq.md)
Häufige Probleme, oft gestellte Fragen und deren Lösungen.

---

<p align="center">
  <img src="https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/img/logo_int_v4.png" alt="Proxmox Extended Sensors Logo" width="600"/>
</p>

---

# 🚀 Proxmox Extended Sensors

## Einführung

**Proxmox Extended Sensors ist eine Integration für Home Assistant, die entwickelt wurde, um erweiterte Überwachung und vollständige Kontrolle über Proxmox VE und Proxmox Backup Server (PBS) zu bieten.**

Im Gegensatz zu rein metrikbasierten Lösungen führt diese Integration einen Ansatz ein, der auf **nützlichen Informationen (Insight)** zentriert ist. So können Sie nicht nur verstehen, was im System passiert, sondern auch, wie es tatsächlich funktioniert.

Sie bietet vollständige Transparenz über die Infrastruktur und fügt direkte Steuerungsmöglichkeiten für Knoten, virtuelle Maschinen, Container, Speicher und Backup-Dienste hinzu.

---

## 🧠 System Insight (V3/V4)

Ab Version 3 hat sich die Integration von einer Sammlung technischer Metriken zu einem auf Infrastruktur ausgerichteten Observability-System weiterentwickelt.

V4 führt Sensoren ein, die den Gesamtzustand des Knotens interpretieren und komplexe Metriken in nützliche und umsetzbare Informationen umwandeln können:

- **Proxmox-Knoten** → Gesamtzustand des Knotens (`Excellent`, `Warning`, `Critical`, etc.) mit angereicherten Infrastrukturattributen
- **Knoten-Score** → numerische Bewertung der Leistung und des allgemeinen Systemzustands
- **Lastdurchschnitt (1m / 5m / 15m)** → tatsächliche Host-Last
- **E/A-Wartezeit** → Erkennung von Druck und Sättigung der Festplatte
- **CPU-Auslastung pro Kern** → verfügbar für Knoten, VMs und Container
- **Netzwerktelemetrie des Knotens** → intelligente Berechnung des aggregierten RX/TX-Verkehrs von VMs und CTs
- **Erweiterte Speicherinformationen** → Zustand, Kapazität und detaillierte Metriken physischer Festplatten und Speicher

Diese Sensoren ermöglichen es, Engpässe zu erkennen, Systemverschlechterungen zu identifizieren und viel intelligentere Automatisierungen aufzubauen, ohne dass zusätzliche externe Werkzeuge erforderlich sind.

---

## 🔍 Hauptfunktionen von V4

- Globale Überwachung des Proxmox-Clusters
- Erweiterte Erkennung eingebundener Festplatten (CIFS/NFS/local)
- Intelligente Netzwerk- und Speichertelemetrie
- Aggregierte Zustands- und Infrastruktursensoren

### Vollständige Überwachung von:

- Knoten
- Virtuellen Maschinen (QEMU)
- Containern (LXC)
- Festplatten und Speicher
- Proxmox Backup Server (PBS)

### Erweiterte Funktionen

- Steuerungsaktionen von Home Assistant aus
- Integrierte Backup-Dienste
- Volle Kompatibilität mit PBS (einschließlich Deduplizierung)
- Sichere Authentifizierung mittels Tokens
- Saubere und konsistente Entitätsstruktur
- Optimierte Aktualisierungen und geringer Ressourcenverbrauch

---

## 🧩 Unterstützte Versionen

- Proxmox VE 7.x / 8.x / 9.x
- Kompatibel mit Linux Kernel 6.x / 7.x
- Proxmox Backup Server 3.x / 4.x
- Home Assistant 2024.x oder neuer

---

## 📑 Inhaltsverzeichnis

- [Hauptfunktionen](#-hauptfunktionen-v400)
- [Knotenzustand und -leistung](#-knotenzustand-und-leistung)
- [Festplatten und SMART](#-festplatten-und-smart)
- [Virtuelle Maschinen (QEMU)](#-virtuelle-maschinen-qemu)
- [Container (LXC)](#-container-lxc)
- [Backup-Dienste](#-backup-dienste-vms-und-cts)
- [Proxmox Backup Server (PBS)](#-proxmox-backup-server-pbs)
- [Steuerungsaktionen (PVE und PBS)](#-steuerungsaktionen-pve-und-pbs)
- [Installation](#-installation)
- [Visuelle Konfigurationsanleitung](#-visuelle-konfigurationsanleitung)
- [Beiträge](#-beiträge-und-community)

---

## 🔥 Hauptfunktionen von V4

### ⚙️ Verbesserte Konfiguration

- Automatische Knotenerkennung
- Optionale manuelle Auswahl
- Einfachere, geführte Konfiguration
- Kompatibilität mit API-Tokens (PVE/PBS)
- Intelligente Erkennung eingeschränkter Berechtigungen

---

### 🌐 Cluster-Überwachung (NEU)

- Globale Sensoren für den Proxmox-Cluster
- Status von Backups und fehlgeschlagenen Aufgaben
- Knoten online/offline
- Aggregierte CPU- und RAM-Auslastung
- Globale Anzahl von VMs und CTs

---

### 💽 Eingebundene Festplatten und Speicher (NEU)

- Automatische Erkennung eingebundener Festplatten
- Kompatibilität mit CIFS / SMB und NFS
- Sensoren für Integrität und fehlende Einhängepunkte
- Intelligenter Ausschluss von tmpfs und Pseudo-Einhängungen
- Detaillierte Nutzungs- und Kapazitätsmetriken

---

### 🌡️ Erweiterte Hardware-Überwachung

- Echtzeit-Temperaturen (CPU, VRM, Chipsatz, Festplatten)
- Lüfter- und Spannungssensoren
- Intelligente Filterung gültiger Sensoren
- Vereinheitlichte Temperatursensoren (CPU + NVMe)
- Erweiterte Intel-/AMD-/ACPI-/NVMe-Kompatibilität

> Erfordert `lm-sensors` auf dem Proxmox-Host

---

### 🧠 Knotenzustand und -leistung

- CPU, RAM, Uptime, Kernel und PVE-Version
- Netzwerküberwachung (RX/TX)
- Aufgaben und Systemstatus
- Erweiterte Last- und Leistungsmetriken
- Knoten-Score und globaler Infrastrukturzustand

---

### 💾 Festplatten und SMART

- Nach physischer Festplatte gruppierte Sensoren
- Gesamt-/genutzter Speicherplatz und erweiterte Metriken
- SMART-Attribute (HDD, SSD, NVMe)
- Temperaturen nach Festplattentyp
- Erweiterte NVMe-Metriken und Gesundheitszustand

---

### 🖥️ Virtuelle Maschinen (QEMU)

- Zustand, CPU, Arbeitsspeicher und Festplatte
- Netzwerk RX/TX
- Basisinformationen und Uptime
- CPU-Auslastung pro Kern
- Steuerungsaktionen von Home Assistant aus

---

### 📦 Container (LXC)

- Zustand, CPU, Arbeitsspeicher und Festplatte
- Netzwerk RX/TX
- Basisinformationen und Uptime
- CPU-Auslastung pro Kern
- Steuerungsaktionen von Home Assistant aus

---

## 💾 Backup-Dienste (VMs und CTs)

Die Integration ermöglicht es, Backups direkt von Home Assistant aus zu erstellen, die vollständig mit Proxmox VE und PBS kompatibel sind.

### 🟦 Einzelnes Backup

- Unterstützt mehrere IDs (kommagetrennt)
- Modi: snapshot / suspend / stop
- Komprimierung: zstd / gzip / lzo / none
- Kompatibel mit PBS und Deduplizierung

### 🟩 Massen-Backup

- Backup aller Ressourcen eines Knotens
- Steuerung der Gleichzeitigkeit und Zeitvorgaben
- Ideal für Automatisierung
- Kompatibel mit großen Infrastrukturen

Die Backups werden automatisch wie folgt benannt:

```text
HA-{{vmid}}-{{guestname}}
```

Vollständig kompatibel mit PBS, einschließlich Deduplizierung und vorhandenen Ketten.

---

## 🗄️ Proxmox Backup Server (PBS)

Erweiterte Überwachung von Datastore und Aufgaben:

- Gesamt-, freier Speicherplatz und Prozentsatz
- Deduplizierungsrate
- Status des letzten Backups
- Fehler und Aufgabenzusammenfassung
- Status der Garbage Collection
- Detaillierte Aufgabeninformationen

---

## 🎛️ Steuerungsaktionen (PVE & PBS)

**Knoten:**
- Ausschalten / Neustarten / Wake-on-LAN

**Virtuelle Maschinen:**
- Starten / Stoppen / Herunterfahren / Neustarten / Zurücksetzen
- Anhalten / Fortsetzen / Ruhezustand

**Container:**
- Starten / Stoppen / Herunterfahren / Neustarten

**PBS:**
- Garbage Collection
- Bereinigen (Prune)
- Verifizieren
- Synchronisieren

---

## 🎨 Organisation und Struktur

- Sensoren automatisch gruppiert in:
  1. Cluster
  2. Knoten
  3. Physische Festplatten
  4. Virtuelle Maschinen
  5. Container
  6. Speicher / Datastores
  7. PBS und Aufgaben

- Konsistente und klare Namen zur Erleichterung von Dashboards und Automatisierungen

---

## 🧩 Installation

### 🔹 Über HACS (empfohlen)

1. **HACS → Integrationen** öffnen
2. Benutzerdefiniertes Repository hinzufügen
3. Nach **Proxmox Extended Sensors** suchen
4. Installieren und Home Assistant neu starten
5. Integration über die Einstellungen hinzufügen

### 🔹 Manuelle Installation

1. Nach `/config/custom_components/proxmox_sensors` kopieren
2. Home Assistant neu starten
3. Integration hinzufügen

---

## 🧭 Visuelle Konfigurationsanleitung

Im Folgenden finden Sie eine vollständige visuelle Schritt-für-Schritt-Anleitung des Konfigurationsprozesses, einschließlich Zugriffsmethoden, Ressourcenauswahl und Installationsschritten.

<details>
  <summary>🪪 Verbindung mit dem Server</summary>
  <p align="center">
    <img src="../../img/install/setup_pve_1.png" alt="Proxmox Verbindung" width="600">
  </p>
  <p align="center"><i>Es ist nicht nötig, "http://" oder "https://" anzugeben. Dies wird automatisch verwaltet.</i></p>
</details>

<details>
  <summary>🪪 Anmeldung mit Benutzername und Passwort (nur PVE)</summary>
  <p align="center">
    <img src="../../img/install/access_passw.png" alt="Anmeldung mit Benutzername und Passwort" width="600">
  </p>
  <p align="center"><i>Stellen Sie sicher, dass Sie den richtigen Realm verwenden (`pam` oder `pve`).</i></p>
</details>

<details> 
  <summary>🪪 Anmeldung mit Benutzer und Token (PVE und PBS)</summary>
  <p align="center">
    <img src="../../img/install/access_token.png" alt="Anmeldung mit Token" width="600">
  </p>
  <p align="center"><i>Im Feld Token_id müssen Sie nur den Namen des Tokens eingeben.</i></p>
</details>

<details>
  <summary>🧠 Knotenauswahl (V4)</summary>
  <p align="center">
    <img src="../../img/install/node_select.png" alt="Knotenauswahl" width="600">
  </p>
  <p align="center"><i>Wählen Sie die automatisch erkannten Knoten aus oder legen Sie manuell fest, welche einbezogen werden sollen.</i></p>
</details>

<details>
  <summary>⚙️ Ressourcenauswahl</summary>
  <p align="center">
    <img src="../../img/install/resources_select.png" alt="Ressourcenauswahl" width="600">
  </p>
  <p align="center"><i>Wählen Sie die CTs, VMs und Speicherorte aus, die Sie einbeziehen möchten, zusammen mit den entsprechenden Optionen.</i></p>
</details>

---

**Wenn Ihnen diese Integration gefällt, ziehen Sie bitte in Betracht, ein ⭐ auf GitHub zu hinterlassen.**

---

## 🤝 Beiträge und Community

Beiträge sind willkommen. Sie können Issues oder Pull Requests erstellen.
Repository: https://github.com/Javisen/proxmox_sensors

---

<p align="center"><i>Gepflegt von Javisen - MIT-Lizenz</i></p>