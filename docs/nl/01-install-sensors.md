# 🚀 Stap 1: Installatie en configuratie van sensoren

**Deze handleiding legt uit hoe u de Proxmox-node voorbereidt om hardwaregegevens vrij te geven en ervoor te zorgen dat temperatuurmetingen en Smart-gegevens beschikbaar zijn voor Home Assistant.**


## 1. Installatie van afhankelijkheden

*Om ervoor te zorgen dat de integratie alle hardwaresensoren en SMART-attributen van de schijven kan lezen, is het noodzakelijk om de volgende tools op Proxmox te installeren:*

- **lm-sensors** → Sensoren voor CPU, moederbord, chipset, VRM, ventilatoren…**
- **smartmontools** → SMART-informatie van HDD, SSD en NVMe**


```bash

apt update && apt install lm-sensors smartmontools -y

```

## 2. Hardware detectie

* **Voer de detectie-assistent uit om de benodigde modules te identificeren:**


```bash

sensors-detect

```

**Antwoord YES (of druk op Enter) op alle vragen. Aan het einde zal het systeem de benodigde modules identificeren (bijvoorbeeld: `coretemp` voor Intel CPU's).**


## 3. Persistentie van modules

**Om ervoor te zorgen dat de sensoren automatisch worden geactiveerd bij het herstarten van de server, stelt de `sensors-detect` assistent u aan het einde van het proces een belangrijke vraag:**


`Do you want to add these lines automatically to /etc/modules? (yes/NO)`



> [!CAUTION]
> **U moet handmatig `yes` typen en op Enter drukken.** Als u alleen op Enter drukt zonder iets te typen, selecteert het systeem standaard `NO`. Als dit gebeurt, worden de sensoren na een herstart niet geladen en ontvangt Home Assistant geen temperatuurgegevens meer.


## 4. Onmiddellijke verificatie

**Om de sensoren nu direct te activeren zonder te herstarten, voert u het volgende uit:**



```bash

# Laad de gedetecteerde modules (voorbeeld voor Intel)

modprobe coretemp

# Controleer of de temperaturen worden weergegeven

sensors

```

## 🚀 Stap 5: Installatie van de Sensorserver (API Bridge)
**De officiële Proxmox API geeft niet alle hardwaresensoren vrij, daarom is het noodzakelijk om een klein script te installeren dat fungeert als brug tussen Proxmox en Home Assistant.**

1. **Download en installatie van het script**
Voer deze commando's uit in de terminal van uw Proxmox-server:
```bash
# Download het script uit de repository
wget https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/scripts/pve-sensors-api.py -O /usr/local/bin/pve-sensors-api.py

# Geef uitvoeringsrechten
chmod +x /usr/local/bin/pve-sensors-api.py
```
2. **Configuratie als systeemdienst**
Maak het servicebestand aan:
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

3. **Onmiddellijke activering**

```bash
systemctl daemon-reload
systemctl enable --now pve-sensors
```

4. **Eindcontrole**
Open in uw browser:
```
http://UW_PROXMOX_IP:9000/sensors
```

Als er een JSON verschijnt met temperaturen en sensoren, werkt de server correct.

## ✔ Conclusie

**Zodra het sensors-commando metingen retourneert en de pve-sensors service actief is, kan Home Assistant alle hardwaregegevens ophalen zonder dat er extra configuraties nodig zijn.**
