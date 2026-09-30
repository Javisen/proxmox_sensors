# 🌡️ Passo 1: Sensori hardware e Sidecar

Questa guida prepara un nodo Proxmox VE per i dati hardware non esposti dalla normale API Proxmox. V5 usa il sidecar per temperature, memoria, mount e SMART e aggiunge **Sidecar Status**.

## 1. Installa i pacchetti
```bash
apt update && apt install lm-sensors smartmontools -y
```

## 2. Rileva i sensori
```bash
sensors-detect
```
Segui la procedura e abilita i moduli adatti all'hardware. Se viene proposto di salvarli in `/etc/modules`, assicurati che quelli necessari siano persistenti dopo il riavvio.

## 3. Verifica
```bash
sensors
```
Su Intel con `coretemp`, se necessario:
```bash
modprobe coretemp
sensors
```
Non forzare `coretemp` su sistemi che usano un driver diverso.

## 4. Installare il Sidecar

Esegui il seguente comando su ogni host PVE/PBS su cui desideri installare l'Hardware Sidecar:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/scripts/install-sidecar.sh)
```

Durante l'installazione, ti verrà richiesto di inserire l'indirizzo o gli indirizzi IP delle tue istanze Home Assistant. È possibile inserire più indirizzi IP separandoli con delle virgole.

Solo gli indirizzi IP specificati saranno autorizzati ad accedere all'Hardware Sidecar.

> **Nota:** Se il Sidecar è già installato, esegui nuovamente lo stesso comando per aggiornare l'installazione esistente e configurare gli indirizzi IP Home Assistant autorizzati.

## 5. Verificare il Sidecar

Controlla lo stato del servizio Sidecar:

```bash
systemctl status pve-sensors.service
```

Il servizio dovrebbe risultare `active (running)`.

## 6. Guasto del sidecar
V5 conserva quando possibile gli ultimi valori hardware validi. **Sidecar Status** mostra Memory, Mounts, Sensors e SMART come `ok`, `degraded`, `error` o `unknown`.

Avanti: [02. Utente e permessi Proxmox](02-proxmox-config.md)
