# 🔌 Schritt 3: Installation der Integration in Home Assistant

Um alle Daten (Temperaturen, Hardware-Sensoren, Festplatten, PBS, VMs und CTs) anzuzeigen, verwenden wir die Integration **Proxmox Extended Sensors**.

---

## 1. Installation über HACS

Da es sich um eine benutzerdefinierte Integration handelt, musst du sie zuerst zu HACS hinzufügen:

1. Gehe zu **HACS → Integrationen**  
2. Klicke auf die **drei Punkte** (oben rechts)  
3. Wähle **Benutzerdefinierte Repositories**  
4. Füge dieses Repository hinzu:  
   `https://github.com/Javisen/proxmox_sensors/`  
5. Wähle als **Kategorie** `Integration`  
6. Installiere die Integration und **starte Home Assistant neu**

---

## 2. Integration hinzufügen

Nach dem Neustart:

1. Gehe zu **Einstellungen → Geräte & Dienste**  
2. Klicke auf **Integration hinzufügen**  
3. Suche nach **Proxmox Extended Sensors**

---

## 3. Verbindungskonfiguration

### 🔹 Host
- **Lokales Netzwerk:** `192.168.1.50`  
- **Externer Zugriff:** `proxmox.meinedomain.com`  

> Es ist nicht erforderlich, `http://` oder `https://` anzugeben. Dies wird automatisch erkannt.

---

### 🔹 Servertyp
- **PVE** → Proxmox Virtual Environment  
- **PBS** → Proxmox Backup Server  

---

### 🔹 Authentifizierungsmethode

- **Benutzername + Passwort** → nur für PVE  
- **API-Token** → Empfohlen und für PBS obligatorisch  

---

## 🔐 Option A: Benutzername und Passwort (nur PVE)

Felder:

- **User:** `benutzer@realm`  
  - Beispiel: `homeassistant@pve`  
- **Password:** Passwort des Benutzers  

> 💡 Ab V3 wird der Knoten automatisch erkannt. Eine manuelle Eingabe ist nicht erforderlich.

---

## 🔐 Option B: API-Token (empfohlen)

Felder:

- **User:** `benutzer@realm`  
- **Token ID:** nur der Name → `ha-token`  
- **Token Secret:** das in Proxmox generierte Secret  

> ⚠️ Verwende nicht das Format `benutzer@pve!token`

---

## 🧠 Ressourcenauswahl (PVE)

Nach der Verbindung erkennt die Integration automatisch die verfügbaren Ressourcen.

Du kannst auswählen:

- Virtuelle Maschinen (VMs)  
- Container (CTs)  
- Physische Festplatten  
- Speicher (Storages)  

> 💡 Wähle nur das Nötigste aus, um Home Assistant sauber und effizient zu halten.

---

## 🧭 Visuelle Installationsanleitung

Im Folgenden wird der vollständige Prozess mit Screenshots dargestellt:

<details>
  <summary>🪪 Serververbindung</summary>
  <p align="center">
    <img src="../../img/install/setup_pve_1.png" alt="Proxmox Verbindung" width="600">
  </p>
  <p align="center"><i>Es ist nicht erforderlich, http/https anzugeben.</i></p>
</details>

<details>
  <summary>🪪 Anmeldung mit Benutzername und Passwort (PVE)</summary>
  <p align="center">
    <img src="../../img/install/access_passw.png" alt="Benutzeranmeldung" width="600">
  </p>
  <p align="center"><i>Verwende den richtigen Realm (pam oder pve).</i></p>
</details>

<details>
  <summary>🪪 Anmeldung mit Token (PVE und PBS)</summary>
  <p align="center">
    <img src="../../img/install/access_token.png" alt="Token-Anmeldung" width="600">
  </p>
  <p align="center"><i>Gib nur den Token-Namen bei Token ID ein.</i></p>
</details>

<details>
  <summary>🧠 Knotenauswahl (V3)</summary>
  <p align="center">
    <img src="../../img/install/node_select.png" alt="Knotenauswahl" width="600">
  </p>
  <p align="center"><i>Die Knoten werden automatisch erkannt und können manuell ausgewählt werden.</i></p>
</details>

<details>
  <summary>⚙️ Ressourcenauswahl</summary>
  <p align="center">
    <img src="../../img/install/resources_select.png" alt="Ressourcenauswahl" width="600">
  </p>
</details>

---

## ⚠️ Hinweis zu PBS in verwalteten Umgebungen

Wenn du einen **verwalteten oder Multi-Tenant-PBS** (Tuxis, Hetzner, etc.) verwendest:

- Du hast keinen Zugriff auf Hardware-Sensoren  
- Du wirst keine Temperaturen oder physischen Festplatten sehen  
- Es gibt keine Knoten-Metriken  

Das ist normal, weil:

- Du keinen Zugriff auf die tatsächliche Hardware hast  
- Der Anbieter das System einschränkt  
- Es keine Berechtigungen auf niedriger Ebene gibt  

**Ergebnis:**  
Es werden nur begrenzte Datastore-Daten angezeigt.

---