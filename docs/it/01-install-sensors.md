# 🚀 Passaggio 1: Installazione e configurazione dei sensori

**Questa guida spiega come preparare il nodo Proxmox affinché esponga i dati hardware e assicuri che le letture della temperatura e i dati Smart siano disponibili per Home Assistant.**


## 1. Installazione delle dipendenze

*Affinché l'integrazione possa leggere tutti i sensori hardware e gli attributi SMART dei dischi, è necessario installare i seguenti strumenti su Proxmox:*

- **lm-sensors** → Sensori di CPU, scheda madre, chipset, VRM, ventole…**
- **smartmontools** → Informazioni SMART di HDD, SSD e NVMe**


```bash

apt update && apt install lm-sensors smartmontools -y

```

## 2. Rilevamento hardware

* **Esegui l'assistente di rilevamento per identificare i moduli necessari:**


```bash

sensors-detect

```

**Rispondi YES (o premi Invio) a tutte le domande. Al termine, il sistema identificherà i moduli necessari (ad esempio: `coretemp` per CPU Intel).**


## 3. Persistenza dei moduli

**Affinché i sensori si attivino automaticamente al riavvio del server, l'assistente `sensors-detect` ti porrà una domanda chiave alla fine del processo:**


`Do you want to add these lines automatically to /etc/modules? (yes/NO)`



> [!CAUTION]
> **Devi scrivere `yes` manualmente e premere Invio.** Se premi solo Invio senza scrivere nulla, il sistema selezionerà `NO` per impostazione predefinita. Se ciò accade, i sensori non verranno caricati dopo un riavvio e Home Assistant smetterà di ricevere i dati sulla temperatura.



## 4. Verifica immediata

**Per attivare i sensori subito senza dover riavviare, esegui:**



```bash

# Carica i moduli rilevati (esempio per Intel)

modprobe coretemp

# Verifica che vengano visualizzate le temperature

sensors

```

## 🚀 Passaggio 5: Installazione del Server dei Sensori (API Bridge)
**L'API ufficiale di Proxmox non espone tutti i sensori hardware, quindi è necessario installare un piccolo script che funga da ponte tra Proxmox e Home Assistant.**

1. **Download e installazione dello script**
Esegui questi comandi nel terminale del tuo server Proxmox:
```bash
# Scarica lo script dal repository
wget https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/scripts/pve-sensors-api.py -O /usr/local/bin/pve-sensors-api.py

# Assegna i permessi di esecuzione
chmod +x /usr/local/bin/pve-sensors-api.py
```
2. **Configurazione come servizio di sistema**
Crea il file di servizio:
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

3. **Attivazione immediata**

```bash
systemctl daemon-reload
systemctl enable --now pve-sensors
```

4. **Verifica finale**
Apri nel tuo browser:
```
http://TUO_IP_PROXMOX:9000/sensors
```

Se appare un JSON con temperature e sensori, il server funziona correttamente.

## ✔ Conclusione

**Una volta che il comando sensors restituisce le letture e il servizio pve-sensors è attivo, Home Assistant sarà in grado di ottenere tutti i dati hardware senza necessità di configurazioni aggiuntive.**
