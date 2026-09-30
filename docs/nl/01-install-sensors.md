# 🌡️ Stap 1: Hardwaresensoren en Sidecar

Deze handleiding bereidt een Proxmox VE-node voor op hardwaredata die niet via de standaard Proxmox-API beschikbaar is. V5 gebruikt de sidecar voor temperaturen, geheugen, mounts en SMART en voegt **Sidecar Status** toe.

## 1. Pakketten installeren
```bash
apt update && apt install lm-sensors smartmontools -y
```

## 2. Sensoren detecteren
```bash
sensors-detect
```
Volg de wizard en activeer passende modules. Als `/etc/modules` wordt aangeboden, zorg dat benodigde modules na reboot blijven laden.

## 3. Controleren
```bash
sensors
```
Voor Intel met `coretemp`, indien nodig:
```bash
modprobe coretemp
sensors
```
Forceer `coretemp` niet op systemen met een andere driver.

---

## 4. De Sidecar installeren

Voer de volgende opdracht uit op elke PVE/PBS-host waarop je de Hardware Sidecar wilt installeren:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/scripts/install-sidecar.sh)
```

Tijdens de installatie wordt je gevraagd om het IP-adres of de IP-adressen van je Home Assistant-instantie(s) in te voeren. Meerdere IP-adressen kunnen worden ingevoerd, gescheiden door komma's.

Alleen de opgegeven IP-adressen krijgen toegang tot de Hardware Sidecar.

> **Opmerking:** Als de Sidecar al is geïnstalleerd, voer dan dezelfde opdracht opnieuw uit om de bestaande installatie bij te werken en de toegestane Home Assistant-IP-adressen te configureren.

## 5. De Sidecar controleren

Controleer de status van de Sidecar-service:

```bash
systemctl status pve-sensors.service
```

De service zou als `active (running)` moeten worden weergegeven.

---

## 6. Bij storing
V5 bewaart waar mogelijk de laatste geldige hardwarewaarden. **Sidecar Status** toont Memory, Mounts, Sensors en SMART als `ok`, `degraded`, `error` of `unknown`.

Volgende: [02. Proxmox-gebruiker en rechten](02-proxmox-config.md)
