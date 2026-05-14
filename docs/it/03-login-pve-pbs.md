# 🔌 Passo 3: Installazione dell'Integrazione in Home Assistant

Per visualizzare tutti i dati (temperature, sensori hardware, dischi, PBS, VM e CT), utilizzeremo l'integrazione **Proxmox Extended Sensors**.

---

## 1. Installazione tramite HACS

Essendo un'integrazione personalizzata, devi prima aggiungerla a HACS:

1. Vai su **HACS → Integrazioni**
2. Fai clic sui **tre puntini** (in alto a destra)
3. Seleziona **Repository personalizzati**
4. Aggiungi questo repository:
   `https://github.com/Javisen/proxmox_sensors/`
5. In **Categoria**, seleziona `Integrazione`
6. Installa l'integrazione e **riavvia Home Assistant**

---

## 2. Aggiungere l'integrazione

Dopo il riavvio:

1. Vai su **Impostazioni → Dispositivi e Servizi**
2. Fai clic su **Aggiungi integrazione**
3. Cerca **Proxmox Extended Sensors**

---

## 3. Configurazione della connessione

### 🔹 Host
- **Rete locale:** `192.168.1.50`
- **Accesso esterno:** `proxmox.miodominio.com`

> Non è necessario includere `http://` o `https://`. Viene rilevato automaticamente.

---

### 🔹 Tipo di server
- **CLUSTER** → Cluster Proxmox
- **PVE** → Proxmox Virtual Environment
- **PBS** → Proxmox Backup Server

---

### 🔹 Metodo di autenticazione

- **Utente + password** → solo su PVE e Cluster
- **Token API** → Obbligatorio su PBS

---

## 🔐 Opzione A: Utente e password (solo PVE)

Campi:

- **Utente:** `utente@realm`
  - Esempio: `homeassistant@pve`
- **Password:** password dell'utente

> 💡 Dalla V3, il nodo viene rilevato automaticamente. Non è necessario inserirlo manualmente.

---

## 🔐 Opzione B: Token API (raccomandato)

Campi:

- **Utente:** `utente@realm`
- **ID Token:** solo il nome → `ha-token`
- **Segreto Token:** il segreto generato in Proxmox

> ⚠️ Non utilizzare il formato `utente@pve!token`

---

## 🧠 Selezione delle risorse (PVE)

Dopo la connessione, l'integrazione rileverà automaticamente le risorse disponibili.

Potrai selezionare:

- Macchine virtuali (VM)
- Contenitori (CT)
- Dischi fisici
- Storage

> 💡 Seleziona solo il necessario per mantenere Home Assistant pulito ed efficiente.

---

## 🧭 Guida Visiva all'Installazione

Di seguito è mostrato il processo completo con screenshot:

<details>
  <summary>🪪 Connessione al server</summary>
  <p align="center">
    <img src="../../img/install/setup_pve_1.png" alt="Connessione Proxmox" width="600">
  </p>
  <p align="center"><i>Non è necessario includere http/https.</i></p>
</details>

<details>
  <summary>🪪 Accesso con utente e password (PVE)</summary>
  <p align="center">
    <img src="../../img/install/access_passw.png" alt="Accesso utente" width="600">
  </p>
  <p align="center"><i>Utilizza il realm corretto (pam o pve).</i></p>
</details>

<details>
  <summary>🪪 Accesso con token (PVE e PBS)</summary>
  <p align="center">
    <img src="../../img/install/access_token.png" alt="Accesso con token" width="600">
  </p>
  <p align="center"><i>Inserisci solo il nome del token nell'ID Token.</i></p>
</details>

<details>
  <summary>🧠 Selezione dei nodi (V3)</summary>
  <p align="center">
    <img src="../../img/install/node_select.png" alt="Selezione nodi" width="600">
  </p>
  <p align="center"><i>I nodi vengono rilevati automaticamente e possono essere selezionati manualmente.</i></p>
</details>

<details>
  <summary>⚙️ Selezione delle risorse</summary>
  <p align="center">
    <img src="../../img/install/resources_select.png" alt="Selezione risorse" width="600">
  </p>
</details>

---

## ⚠️ Nota su PBS in ambienti gestiti

Se utilizzi un PBS **gestito o multi-tenant** (Tuxis, Hetzner, ecc.):

- Non avrai accesso ai sensori hardware
- Non vedrai temperature né dischi fisici
- Non ci saranno metriche del nodo

Questo è normale perché:

- Non hai accesso all'hardware reale
- Il fornitore restringe il sistema
- Non esistono permessi di basso livello

**Risultato:**
Verranno visualizzati solo dati limitati del datastore.

---