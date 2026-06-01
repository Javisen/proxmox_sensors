# 📚 Documentatie en Handleidingen

Deze handleidingen behandelen de noodzakelijke stappen om de integratie correct te configureren en te profiteren van alle functionaliteiten.

---

## 🌡️ [01. Configuratie van Hardware Sensoren](01-install-sensors.md)
Hoe installeer en configureer je **lm-sensors** op je Proxmox-knooppunt om temperatuur- en ventilatormonitoring in te schakelen.

---

## 🔑 [02. Proxmox Configuratie](02-proxmox-config.md)
Hoe maak je een veilige **gebruiker** en een **API-token** aan in Proxmox (PVE en PBS) met de minimaal benodigde rechten.

---

## ⚙️ [03. Integratie Aanmelding (PVE en PBS)](03-login-pve-pbs.md)
Stapsgewijze handleiding om de integratie vanaf Home Assistant met je servers te verbinden.

---

## ❓ [04. Veelgestelde Vragen en Probleemoplossing](04-faq.md)
Veelvoorkomende problemen, veelgestelde vragen en hoe je ze oplost.

---

<p align="center">
  <img src="https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/img/logo_int_v4.png" alt="Proxmox Extended Sensors Logo" width="600"/>
</p>

---

# 🚀 Proxmox Extended Sensors

## Introductie

**Proxmox Extended Sensors is een integratie voor Home Assistant ontworpen om geavanceerde monitoring en volledige controle over Proxmox VE en Proxmox Backup Server (PBS) te bieden.**

In tegenstelling tot oplossingen die uitsluitend op metrieken zijn gebaseerd, introduceert deze integratie een aanpak gericht op **nuttige informatie (insight)** , waardoor je niet alleen begrijpt wat er in het systeem gebeurt, maar ook hoe het daadwerkelijk presteert.

Het biedt volledige zichtbaarheid van de infrastructuur en voegt directe controlemogelijkheden toe over knooppunten, virtuele machines, containers, opslag en back-upservices.

---

## 🧠 System Insight (V3/V4)

Vanaf versie 3 is de integratie geëvolueerd van een verzameling technische metrieken naar een infrastructuurgericht observability-systeem.

V4 introduceert sensoren die de globale staat van het knooppunt kunnen interpreteren en complexe metrieken kunnen omzetten in nuttige en bruikbare informatie:

- **Proxmox-knooppunt** → globale knooppuntstatus (`Excellent`, `Warning`, `Critical`, etc.) met verrijkte infrastructuurkenmerken
- **Knooppuntscore** → numerieke evaluatie van de prestaties en algemene systeemgezondheid
- **Belastingsgemiddelde (1m / 5m / 15m)** → werkelijke hostbelasting
- **I/O-wachttijd** → detectie van schijfdruk en -verzadiging
- **CPU-gebruik per kern** → beschikbaar voor knooppunten, VM's en containers
- **Netwerktelemetrie van het knooppunt** → intelligente berekening van geaggregeerd RX/TX-verkeer van VM's en CT's
- **Geavanceerde opslaginformatie** → status, capaciteit en gedetailleerde metrieken van fysieke schijven en opslag

Deze sensoren maken het mogelijk om knelpunten te detecteren, systeemdegradatie te identificeren en veel intelligentere automatiseringen te bouwen zonder dat er extra externe hulpmiddelen nodig zijn.

---

## 🔍 Belangrijkste mogelijkheden van V4

- Globale Proxmox-clustermonitoring
- Geavanceerde detectie van gemounte schijven (CIFS/NFS/local)
- Intelligente netwerk- en opslagtelemetrie
- Geaggregeerde gezondheids- en infrastructuursensoren

### Volledige monitoring van:

- Knooppunten
- Virtuele machines (QEMU)
- Containers (LXC)
- Schijven en opslag
- Proxmox Backup Server (PBS)

### Geavanceerde functionaliteiten

- Besturingsacties vanuit Home Assistant
- Geïntegreerde back-upservices
- Volledige compatibiliteit met PBS (inclusief deduplicatie)
- Veilige authenticatie via tokens
- Schone en consistente entiteitenstructuur
- Geoptimaliseerde updates en laag resourceverbruik

---

## 🧩 Ondersteunde Versies

- Proxmox VE 7.x / 8.x / 9.x
- Compatibel met Linux Kernel 6.x / 7.x
- Proxmox Backup Server 3.x / 4.x
- Home Assistant 2024.x of nieuwer

---

## 📑 Inhoudsopgave

- [Belangrijkste Kenmerken](#-belangrijkste-kenmerken-v400)
- [Knooppuntstatus en Prestaties](#-knooppuntstatus-en-prestaties)
- [Schijven en SMART](#-schijven-en-smart)
- [Virtuele Machines (QEMU)](#-virtuele-machines-qemu)
- [Containers (LXC)](#-containers-lxc)
- [Back-updiensten](#-back-updiensten-vms-en-cts)
- [Proxmox Backup Server (PBS)](#-proxmox-backup-server-pbs)
- [Besturingsacties (PVE en PBS)](#-besturingsacties-pve-en-pbs)
- [Installatie](#-installatie)
- [Visuele Configuratiegids](#-visuele-configuratiegids)
- [Bijdragen](#-bijdragen-en-community)

---

## 🔥 Belangrijkste Kenmerken van V4

### ⚙️ Verbeterde Configuratie

- Automatische detectie van knooppunten
- Optionele handmatige selectie
- Eenvoudigere, begeleide configuratie
- Compatibiliteit met API-tokens (PVE/PBS)
- Intelligente detectie van beperkte rechten

---

### 🌐 Clustermonitoring (NIEUW)

- Globale sensoren voor het Proxmox-cluster
- Back-upstatus en mislukte taken
- Online/offline knooppunten
- Geaggregeerd CPU- en RAM-gebruik
- Globale telling van VM's en CT's

---

### 💽 Gemounte Schijven en Opslag (NIEUW)

- Automatische detectie van gemounte schijven
- Compatibiliteit met CIFS / SMB en NFS
- Sensoren voor integriteit en ontbrekende mountpoints
- Intelligente uitsluiting van tmpfs en pseudo-mounts
- Gedetailleerde gebruiks- en capaciteitsmetrieken

---

### 🌡️ Geavanceerde Hardwaremonitoring

- Real-time temperaturen (CPU, VRM, chipset, schijven)
- Ventilator- en spanningssensoren
- Intelligente filtering van geldige sensoren
- Geünificeerde temperatuursensoren (CPU + NVMe)
- Geavanceerde Intel / AMD / ACPI / NVMe-compatibiliteit

> Vereist `lm-sensors` op de Proxmox-host

---

### 🧠 Knooppuntstatus en Prestaties

- CPU, RAM, uptime, kernel en PVE-versie
- Netwerkmonitoring (RX/TX)
- Taken en systeemstatus
- Geavanceerde belastings- en prestatiemetrieken
- Knooppuntscore en globale infrastructuurstatus

---

### 💾 Schijven en SMART

- Sensoren gegroepeerd per fysieke schijf
- Totale/gebruikte ruimte en geavanceerde metrieken
- SMART-kenmerken (HDD, SSD, NVMe)
- Temperaturen per schijftype
- Geavanceerde NVMe-metrieken en gezondheidsstatus

---

### 🖥️ Virtuele Machines (QEMU)

- Status, CPU, geheugen en schijf
- Netwerk RX/TX
- Basisgegevens en uptime
- CPU-gebruik per kern
- Besturingsacties vanuit Home Assistant

---

### 📦 Containers (LXC)

- Status, CPU, geheugen en schijf
- Netwerk RX/TX
- Basisgegevens en uptime
- CPU-gebruik per kern
- Besturingsacties vanuit Home Assistant

---

## 💾 Back-updiensten (VM's en CT's)

De integratie maakt het mogelijk om back-ups rechtstreeks vanuit Home Assistant te maken, volledig compatibel met Proxmox VE en PBS.

### 🟦 Individuele Back-up

- Ondersteunt meerdere ID's (gescheiden door komma's)
- Modi: snapshot / suspend / stop
- Compressie: zstd / gzip / lzo / none
- Compatibel met PBS en deduplicatie

### 🟩 Massale Back-up

- Back-up van alle bronnen op een knooppunt
- Controle over gelijktijdigheid en timing
- Ideaal voor automatisering
- Compatibel met grote infrastructuur

Back-ups worden automatisch als volgt benoemd:

```text
HA-{{vmid}}-{{guestname}}
```

Volledig compatibel met PBS, inclusief deduplicatie en bestaande ketens.

---

## 🗄️ Proxmox Backup Server (PBS)

Geavanceerde monitoring van datastore en taken:

- Totaal, vrij en percentage gebruik
- Deduplicatieratio
- Status van laatste back-up
- Fouten en taaksamenvatting
- Status van Garbage Collector
- Gedetailleerde taakinformatie

---

## 🎛️ Besturingsacties (PVE & PBS)

**Knooppunt:**
- Uitschakelen / Herstarten / Wake-on-LAN

**Virtuele machines:**
- Starten / Stoppen / Afsluiten / Herstarten / Resetten
- Pauzeren / Hervatten / Sluimeren

**Containers:**
- Starten / Stoppen / Afsluiten / Herstarten

**PBS:**
- Garbage Collector
- Uitdunnen (Prune)
- Verifiëren
- Synchroniseren

---

## 🎨 Organisatie en structuur

- Sensoren automatisch gegroepeerd in:
  1. Cluster
  2. Knooppunt
  3. Fysieke schijven
  4. Virtuele machines
  5. Containers
  6. Opslag / Datastores
  7. PBS en taken

- Consistente en duidelijke namen om dashboards en automatiseringen te vergemakkelijken

---

## 🧩 Installatie

### 🔹 Via HACS (aanbevolen)

1. Open **HACS → Integraties**
2. Voeg aangepaste repository toe
3. Zoek naar **Proxmox Extended Sensors**
4. Installeer en herstart Home Assistant
5. Voeg de integratie toe via instellingen

### 🔹 Handmatige installatie

1. Kopieer naar `/config/custom_components/proxmox_sensors`
2. Herstart Home Assistant
3. Voeg de integratie toe

---

## 🧭 Visuele Configuratiegids

Hieronder vind je een volledige visuele walkthrough van het configuratieproces, inclusief toegangsmethoden, selectie van bronnen en installatiestappen.

<details>
  <summary>🪪 Verbinding met de Server</summary>
  <p align="center">
    <img src="../../img/install/setup_pve_1.png" alt="Proxmox Verbinding" width="600">
  </p>
  <p align="center"><i>Het is niet nodig om "http://" of "https://" toe te voegen. Dit wordt automatisch afgehandeld.</i></p>
</details>

<details>
  <summary>🪪 Aanmelden met Gebruikersnaam en Wachtwoord (alleen PVE)</summary>
  <p align="center">
    <img src="../../img/install/access_passw.png" alt="Aanmelden met gebruikersnaam en wachtwoord" width="600">
  </p>
  <p align="center"><i>Zorg ervoor dat je het juiste realm gebruikt (`pam` of `pve`).</i></p>
</details>

<details> 
  <summary>🪪 Aanmelden met Gebruiker en Token (PVE en PBS)</summary>
  <p align="center">
    <img src="../../img/install/access_token.png" alt="Aanmelden met token" width="600">
  </p>
  <p align="center"><i>In het Token_id-veld hoef je alleen de naam van de token in te voeren.</i></p>
</details>

<details>
  <summary>🧠 Knooppuntselectie (V4)</summary>
  <p align="center">
    <img src="../../img/install/node_select.png" alt="Knooppuntselectie" width="600">
  </p>
  <p align="center"><i>Selecteer de automatisch gedetecteerde knooppunten of bepaal handmatig welke je wilt opnemen.</i></p>
</details>

<details>
  <summary>⚙️ Bronselectie</summary>
  <p align="center">
    <img src="../../img/install/resources_select.png" alt="Bronselectie" width="600">
  </p>
  <p align="center"><i>Selecteer de CT's, VM's en opslag die je wilt opnemen, samen met de bijbehorende opties.</i></p>
</details>

---

**Als je deze integratie nuttig vindt, overweeg dan om een ⭐ achter te laten op GitHub.**

---

## 🤝 Bijdragen en Community

Bijdragen zijn welkom. Je kunt issues of pull requests openen.
Repository: https://github.com/Javisen/proxmox_sensors

---

<p align="center"><i>Onderhouden door Javisen - MIT-licentie</i></p>