# ❓ FAQ — Häufig gestellte Fragen

Hier findest du die häufigsten Probleme bei der Verwendung von **Proxmox Extended Sensors** und deren Lösungen.

---

# 🔐 Verbindungsprobleme

## ❌ Ich kann mich nicht anmelden

### ✔ Verwende nur IP oder Domain
Richtig:
- `192.168.1.10`  
- `pve.meinedomain.com`

Falsch:
- `http://...`
- `https://...`

---

### ✔ Füge keinen Port hinzu
Die Integration erkennt ihn automatisch.

---

### ✔ Überprüfe die Berechtigungen

- PVE → `PVEAdmin`  
- PBS → `Administrator`  
- Sie müssen unter `/` zugewiesen sein

---

### ✔ Der Token muss aktiv sein
In Proxmox → API Tokens → **Enabled: Yes**

---

## ❌ „Permission denied“ mit Token

### ✔ Berechtigungen unter `/`
Sie sollten nicht einem Knoten, sondern dem Root zugewiesen werden.

### ✔ Benutzer ohne Berechtigungen
Der übergeordnete Benutzer muss eine gültige Rolle haben.

---

# 🌡️ Sensoren und Hardware

## ❌ Temperaturen werden nicht angezeigt

Stelle sicher, dass:


```bash
apt install lm-sensors
sensors-detect
modprobe coretemp
```

Und der Dienst aktiv ist.

---

## ❌ Festplatten oder SMART werden nicht angezeigt

- Die Festplatte muss es unterstützen  
- NVMe in VMs → nicht verfügbar  
- Manche Controller geben keine Daten preis  

---

## ❌ VMs oder CTs werden nicht angezeigt

- Überprüfe die Berechtigungen (`PVEAdmin`)  
- Verwende im Cluster den Hauptknoten  

---

## 🗄️ PBS (Backup Server)

### ❌ Ich sehe keine Datastore-Daten

### 🔒 Verwalteter PBS (Tuxis, Hetzner…)

Du hast keinen Zugriff auf:

- Festplattennutzung  
- Deduplizierung  
- Temperatur  
- CPU/RAM  
- SMART  

👉 Dies ist eine Einschränkung des Anbieters, nicht der Integration.

---

## 🧠 System Insight (V3/V4)

### ❓ Was ist der Node Score?

Es ist eine globale Bewertung des Knotenstatus basierend auf:

- CPU  
- Load  
- IO Wait  

Es ermöglicht dir, schnell zu erkennen, ob ein Knoten unter Last steht.

---

### ❓ Was bedeutet „Node Stress“ oder „Overload“?

Zeigt an, dass das System unter Druck steht:

- Hohe CPU  
- Hohe Last  
- Festplattenauslastung  

👉 Nützlich für Automatisierungen oder Benachrichtigungen.

---

## 🔄 Leistung

### ❓ Die Integration braucht lange zum Aktualisieren

Das ist normal.

Die Integration verwendet ein optimiertes System, um:

- Die Last auf Proxmox zu reduzieren  
- Eine Überlastung der API zu vermeiden  

Standardintervall: ~10 Sekunden.

---

## 🧩 Allgemeine Verwendung

### ❓ Kann ich mehrere Server verwenden?

Ja.  
Du kannst mehrere Instanzen hinzufügen (PVE/PBS).

---

### 🔒 Ist es sicher?

Ja:

- Verwendet API-Token  
- Führt keine Remote-Befehle aus  
- Ändert keine Konfiguration  
- Öffnet keine Ports  

---

## 🧹 Alte Sensoren entfernen

1. Lösche die Integration  
2. Starte Home Assistant neu  
3. Füge sie erneut hinzu  

---

## 🧾 Checkliste vor dem Erstellen eines Issues

Bevor du ein Problem meldest:

- ✔ Kannst du über den Browser auf Proxmox zugreifen?  
- ✔ Verwendest du nur IP oder Domain?  
- ✔ Ist der Token aktiv?  
- ✔ Berechtigungen unter `/`?  
- ✔ Ist lm-sensors installiert?  
- ✔ Hast du Home Assistant neu gestartet?  
- ✔ Hast du die Logs überprüft?  

---

## 🚫 Bekannte Einschränkungen

### 🔒 Verwalteter PBS

Kein Zugriff auf interne Metriken (Hardware, Datastore, etc.)

---

### 🧊 Sensoren in VMs

In virtuellen Maschinen gibt es keine echten Sensoren.

---

### 📦 Festplatten ohne SMART

Manche Festplatten/Controller geben keine Daten preis.

---

### 🔐 Falsch zugewiesene Berechtigungen

Wenn sie nicht unter `/` liegen, schlägt die API fehl.

---

### 🕒 Aktualisierungsintervalle

Es gibt eine bewusste Verzögerung, um Last zu vermeiden.

---

### 🧩 Proxmox-Cluster

Verbinde dich mit dem Hauptknoten.

---

### 🌐 SSL-Zertifikate

Selbstsignierte Zertifikate werden akzeptiert.

---