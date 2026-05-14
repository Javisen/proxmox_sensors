# 🔌 Stap 3: Installatie van de Integratie in Home Assistant

Om alle gegevens te visualiseren (temperaturen, hardwaresensoren, schijven, PBS, VM's en CT's), gebruiken we de integratie **Proxmox Extended Sensors**.

---

## 1. Installatie via HACS

Omdat het een aangepaste integratie betreft, moet je deze eerst toevoegen aan HACS:

1. Ga naar **HACS → Integraties**
2. Klik op de **drie puntjes** (rechtsboven)
3. Selecteer **Aangepaste repositories**
4. Voeg deze repository toe:
   `https://github.com/Javisen/proxmox_sensors/`
5. Selecteer bij **Categorie** de optie `Integratie`
6. Installeer de integratie en **herstart Home Assistant**

---

## 2. Integratie toevoegen

Na de herstart:

1. Ga naar **Instellingen → Apparaten en Services**
2. Klik op **Integratie toevoegen**
3. Zoek naar **Proxmox Extended Sensors**

---

## 3. Verbindingsconfiguratie

### 🔹 Host
- **Lokaal netwerk:** `192.168.1.50`
- **Externe toegang:** `proxmox.mijndomein.com`

> Het is niet nodig om `http://` of `https://` toe te voegen. Dit wordt automatisch gedetecteerd.

---

### 🔹 Servertype
- **CLUSTER** → Proxmox Cluster
- **PVE** → Proxmox Virtual Environment
- **PBS** → Proxmox Backup Server

---

### 🔹 Authenticatiemethode

- **Gebruiker + wachtwoord** → alleen op PVE en Cluster
- **API-token** → Verplicht op PBS

---

## 🔐 Optie A: Gebruiker en wachtwoord (alleen PVE)

Velden:

- **Gebruiker:** `gebruiker@realm`
  - Voorbeeld: `homeassistant@pve`
- **Wachtwoord:** wachtwoord van de gebruiker

> 💡 Vanaf V3 wordt het knooppunt automatisch gedetecteerd. Je hoeft het niet handmatig in te voeren.

---

## 🔐 Optie B: API-token (aanbevolen)

Velden:

- **Gebruiker:** `gebruiker@realm`
- **Token-ID:** alleen de naam → `ha-token`
- **Token Secret:** het geheim gegenereerd in Proxmox

> ⚠️ Gebruik niet het formaat `gebruiker@pve!token`

---

## 🧠 Selectie van bronnen (PVE)

Na de verbinding zal de integratie automatisch de beschikbare bronnen detecteren.

Je kunt selecteren:

- Virtuele machines (VM's)
- Containers (CT's)
- Fysieke schijven
- Opslag (Storage)

> 💡 Selecteer alleen wat nodig is om Home Assistant schoon en efficiënt te houden.

---

## 🧭 Visuele Installatiegids

Hieronder wordt het volledige proces getoond met schermafbeeldingen:

<details>
  <summary>🪪 Verbinding met de server</summary>
  <p align="center">
    <img src="../../img/install/setup_pve_1.png" alt="Proxmox Verbinding" width="600">
  </p>
  <p align="center"><i>Het is niet nodig om http/https toe te voegen.</i></p>
</details>

<details>
  <summary>🪪 Aanmelden met gebruiker en wachtwoord (PVE)</summary>
  <p align="center">
    <img src="../../img/install/access_passw.png" alt="Aanmelden gebruiker" width="600">
  </p>
  <p align="center"><i>Gebruik het juiste realm (pam of pve).</i></p>
</details>

<details>
  <summary>🪪 Aanmelden met token (PVE en PBS)</summary>
  <p align="center">
    <img src="../../img/install/access_token.png" alt="Aanmelden met token" width="600">
  </p>
  <p align="center"><i>Voer alleen de naam van het token in bij Token-ID.</i></p>
</details>

<details>
  <summary>🧠 Selectie van knooppunten (V3)</summary>
  <p align="center">
    <img src="../../img/install/node_select.png" alt="Knooppuntselectie" width="600">
  </p>
  <p align="center"><i>Knooppunten worden automatisch gedetecteerd en kunnen handmatig worden geselecteerd.</i></p>
</details>

<details>
  <summary>⚙️ Selectie van bronnen</summary>
  <p align="center">
    <img src="../../img/install/resources_select.png" alt="Bronselectie" width="600">
  </p>
</details>

---

## ⚠️ Opmerking over PBS in beheerde omgevingen

Als je een **beheerde of multi-tenant** PBS gebruikt (Tuxis, Hetzner, enz.):

- Je hebt geen toegang tot hardwaresensoren
- Je ziet geen temperaturen of fysieke schijven
- Er zullen geen knooppuntmetrieken zijn

Dit is normaal omdat:

- Je geen toegang hebt tot de echte hardware
- De provider het systeem beperkt
- Er geen laag-niveau rechten bestaan

**Resultaat:**
Er worden alleen beperkte datastore-gegevens weergegeven.

---