# 📚 Documentazione e Guide

Queste guide coprono i passaggi necessari per configurare correttamente l'integrazione e sfruttare tutte le sue funzionalità.

---

## 🌡️ [01. Configurazione dei Sensori Hardware](01-install-sensors.md)
Come installare e configurare **lm-sensors** sul tuo nodo Proxmox per abilitare il monitoraggio della temperatura e delle ventole.

---

## 🔑 [02. Configurazione di Proxmox](02-proxmox-config.md)
Come creare un **utente** e un **token API** sicuri in Proxmox (PVE e PBS) con i permessi minimi necessari.

---

## ⚙️ [03. Accesso all'Integrazione (PVE e PBS)](03-login-pve-pbs.md)
Guida passo passo per collegare l'integrazione ai tuoi server da Home Assistant.

---

## ❓ [04. Domande Frequenti e Risoluzione dei Problemi](04-faq.md)
Problemi comuni, domande frequenti e come risolverli.

---

<p align="center">
  <img src="https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/img/logo_int_v4.png" alt="Logo Proxmox Extended Sensors" width="600"/>
</p>

---

# 🚀 Proxmox Extended Sensors

## Introduzione

**Proxmox Extended Sensors è un'integrazione per Home Assistant progettata per fornire monitoraggio avanzato e controllo completo di Proxmox VE e Proxmox Backup Server (PBS).**

A differenza delle soluzioni basate esclusivamente su metriche, questa integrazione introduce un approccio incentrato su **informazioni utili (insight)** , permettendo di capire non solo cosa sta accadendo nel sistema, ma anche come sta effettivamente funzionando.

Fornisce visibilità completa dell'infrastruttura e aggiunge capacità di controllo diretto su nodi, macchine virtuali, container, storage e servizi di backup.

---

## 🧠 System Insight (V3/V4)

A partire dalla versione 3, l'integrazione si è evoluta da una raccolta di metriche tecniche a un sistema di osservabilità orientato all'infrastruttura.

V4 introduce sensori in grado di interpretare lo stato globale del nodo e trasformare metriche complesse in informazioni utili e attuabili:

- **Nodo Proxmox** → stato globale del nodo (`Excellent`, `Warning`, `Critical`, ecc.) con attributi infrastrutturali arricchiti
- **Punteggio del nodo** → valutazione numerica delle prestazioni e della salute generale del sistema
- **Carico medio (1m / 5m / 15m)** → carico effettivo dell'host
- **Attesa I/O** → rilevamento di pressione e saturazione del disco
- **Utilizzo CPU per core** → disponibile per nodi, VM e container
- **Telemetria di rete del nodo** → calcolo intelligente del traffico RX/TX aggregato da VM e CT
- **Informazioni avanzate di storage** → stato, capacità e metriche dettagliate dei dischi fisici e degli storage

Questi sensori consentono di rilevare colli di bottiglia, identificare il degrado del sistema e costruire automazioni molto più intelligenti senza bisogno di strumenti esterni aggiuntivi.

---

## 🔍 Principali capacità di V4

- Monitoraggio globale del cluster Proxmox
- Rilevamento avanzato dei dischi montati (CIFS/NFS/local)
- Telemetria intelligente di rete e storage
- Sensori aggregati di salute e infrastruttura

### Monitoraggio completo di:

- Nodi
- Macchine virtuali (QEMU)
- Container (LXC)
- Dischi e storage
- Proxmox Backup Server (PBS)

### Funzionalità avanzate

- Azioni di controllo da Home Assistant
- Servizi di backup integrati
- Compatibilità totale con PBS (inclusa la deduplicazione)
- Autenticazione sicura tramite token
- Struttura delle entità pulita e coerente
- Aggiornamenti ottimizzati e basso consumo di risorse

---

## 🧩 Versioni Supportate

- Proxmox VE 7.x / 8.x / 9.x
- Compatibile con Linux Kernel 6.x / 7.x
- Proxmox Backup Server 3.x / 4.x
- Home Assistant 2024.x o successivo

---

## 📑 Indice dei Contenuti

- [Caratteristiche Principali](#-caratteristiche-principali-v400)
- [Stato e Prestazioni del Nodo](#-stato-e-prestazioni-del-nodo)
- [Dischi e SMART](#-dischi-e-smart)
- [Macchine Virtuali (QEMU)](#-macchine-virtuali-qemu)
- [Container (LXC)](#-container-lxc)
- [Servizi di Backup](#-servizi-di-backup-vm-e-ct)
- [Proxmox Backup Server (PBS)](#-proxmox-backup-server-pbs)
- [Azioni di Controllo (PVE e PBS)](#-azioni-di-controllo-pve-e-pbs)
- [Installazione](#-installazione)
- [Guida Visiva alla Configurazione](#-guida-visiva-alla-configurazione)
- [Contributi](#-contributi-e-comunità)

---

## 🔥 Caratteristiche Principali di V4

### ⚙️ Configurazione Migliorata

- Rilevamento automatico dei nodi
- Selezione manuale opzionale
- Configurazione più semplice e guidata
- Compatibilità con token API (PVE/PBS)
- Rilevamento intelligente dei permessi limitati

---

### 🌐 Monitoraggio del Cluster (NUOVO)

- Sensori globali del cluster Proxmox
- Stato dei backup e delle attività fallite
- Nodi online/offline
- Utilizzo aggregato di CPU e RAM
- Conteggio globale di VM e CT

---

### 💽 Dischi Montati e Storage (NUOVO)

- Rilevamento automatico dei dischi montati
- Compatibilità con CIFS / SMB e NFS
- Sensori di integrità e mount mancanti
- Esclusione intelligente di tmpfs e pseudo-mount
- Metriche dettagliate di utilizzo e capacità

---

### 🌡️ Monitoraggio Hardware Avanzato

- Temperature in tempo reale (CPU, VRM, chipset, dischi)
- Sensori di ventole e tensioni
- Filtraggio intelligente dei sensori validi
- Sensori di temperatura unificati (CPU + NVMe)
- Compatibilità avanzata Intel / AMD / ACPI / NVMe

> Richiede `lm-sensors` sull'host Proxmox

---

### 🧠 Stato e Prestazioni del Nodo

- CPU, RAM, uptime, kernel e versione PVE
- Monitoraggio di rete (RX/TX)
- Attività e stato del sistema
- Metriche avanzate di carico e prestazioni
- Punteggio del nodo e stato globale dell'infrastruttura

---

### 💾 Dischi e SMART

- Sensori raggruppati per disco fisico
- Spazio totale/usato e metriche avanzate
- Attributi SMART (HDD, SSD, NVMe)
- Temperature per tipo di disco
- Metriche NVMe avanzate e stato di salute

---

### 🖥️ Macchine Virtuali (QEMU)

- Stato, CPU, memoria e disco
- Rete RX/TX
- Informazioni di base e uptime
- Utilizzo CPU per core
- Azioni di controllo da Home Assistant

---

### 📦 Container (LXC)

- Stato, CPU, memoria e disco
- Rete RX/TX
- Informazioni di base e uptime
- Utilizzo CPU per core
- Azioni di controllo da Home Assistant

---

## 💾 Servizi di Backup (VM e CT)

L'integrazione consente di creare backup direttamente da Home Assistant, completamente compatibili con Proxmox VE e PBS.

### 🟦 Backup Individuale

- Supporta ID multipli (separati da virgola)
- Modalità: snapshot / suspend / stop
- Compressione: zstd / gzip / lzo / none
- Compatibile con PBS e deduplicazione

### 🟩 Backup Massivo

- Backup di tutte le risorse di un nodo
- Controllo della concorrenza e dei tempi
- Ideale per l'automazione
- Compatibile con grandi infrastrutture

I backup vengono nominati automaticamente come:

```text
HA-{{vmid}}-{{guestname}}
```

Completamente compatibili con PBS, inclusa la deduplicazione e le catene esistenti.

---

## 🗄️ Proxmox Backup Server (PBS)

Monitoraggio avanzato del datastore e delle attività:

- Utilizzo totale, libero e percentuale
- Tasso di deduplicazione
- Stato dell'ultimo backup
- Errori e riepilogo delle attività
- Stato del Garbage Collector
- Informazioni dettagliate delle attività

---

## 🎛️ Azioni di Controllo (PVE & PBS)

**Nodo:**
- Spegnimento / Riavvio / Wake-on-LAN

**Macchine Virtuali:**
- Avvio / Arresto / Spegnimento / Riavvio / Reset
- Pausa / Ripresa / Ibernazione

**Container:**
- Avvio / Arresto / Spegnimento / Riavvio

**PBS:**
- Garbage Collector
- Potatura (Prune)
- Verifica
- Sincronizzazione

---

## 🎨 Organizzazione e struttura

- Sensori automaticamente raggruppati in:
  1. Cluster
  2. Nodo
  3. Dischi fisici
  4. Macchine virtuali
  5. Container
  6. Storage / Datastore
  7. PBS e attività

- Nomi coerenti e chiari per facilitare dashboard e automazioni

---

## 🧩 Installazione

### 🔹 Tramite HACS (raccomandato)

1. Aprire **HACS → Integrazioni**
2. Aggiungere repository personalizzato
3. Cercare **Proxmox Extended Sensors**
4. Installare e riavviare Home Assistant
5. Aggiungere l'integrazione dalle impostazioni

### 🔹 Installazione manuale

1. Copiare in `/config/custom_components/proxmox_sensors`
2. Riavviare Home Assistant
3. Aggiungere l'integrazione

---

## 🧭 Guida Visiva alla Configurazione

Di seguito troverai un percorso visivo completo del processo di configurazione, inclusi i metodi di accesso, la selezione delle risorse e i passaggi di installazione.

<details>
  <summary>🪪 Connessione al Server</summary>
  <p align="center">
    <img src="../../img/install/setup_pve_1.png" alt="Connessione Proxmox" width="600">
  </p>
  <p align="center"><i>Non è necessario includere "http://" o "https://". Viene gestito automaticamente.</i></p>
</details>

<details>
  <summary>🪪 Accesso con Nome Utente e Password (solo PVE)</summary>
  <p align="center">
    <img src="../../img/install/access_passw.png" alt="Accesso nome utente e password" width="600">
  </p>
  <p align="center"><i>Assicurati di utilizzare il realm corretto (`pam` o `pve`).</i></p>
</details>

<details> 
  <summary>🪪 Accesso con Utente e Token (PVE e PBS)</summary>
  <p align="center">
    <img src="../../img/install/access_token.png" alt="Accesso con token" width="600">
  </p>
  <p align="center"><i>Nel campo Token_id devi inserire solo il nome del token.</i></p>
</details>

<details>
  <summary>🧠 Selezione dei Nodi (V4)</summary>
  <p align="center">
    <img src="../../img/install/node_select.png" alt="Selezione nodi" width="600">
  </p>
  <p align="center"><i>Seleziona i nodi rilevati automaticamente o definisci manualmente quali includere.</i></p>
</details>

<details>
  <summary>⚙️ Selezione delle Risorse</summary>
  <p align="center">
    <img src="../../img/install/resources_select.png" alt="Selezione risorse" width="600">
  </p>
  <p align="center"><i>Seleziona i CT, le VM e gli storage che desideri includere, insieme alle opzioni corrispondenti.</i></p>
</details>

---

**Se trovi utile questa integrazione, considera di lasciare una ⭐ su GitHub.**

---

## 🤝 Contributi e Comunità

I contributi sono benvenuti. Puoi aprire issue o pull request.
Repository: https://github.com/Javisen/proxmox_sensors

---

<p align="center"><i>Mantenuto da Javisen - Licenza MIT</i></p>