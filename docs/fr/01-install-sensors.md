# 🚀 Étape 1 : Installation et configuration des capteurs

**Ce guide explique comment préparer le nœud Proxmox pour qu'il expose les données matérielles et garantisse que les lectures de température et les données Smart soient disponibles pour Home Assistant.**


## 1. Installation des dépendances

*Pour que l'intégration puisse lire tous les capteurs matériels et les attributs SMART des disques, il est nécessaire d'installer les outils suivants sur Proxmox :*

- **lm-sensors** → Capteurs de CPU, carte mère, chipset, VRM, ventilateurs…**
- **smartmontools** → Informations SMART des HDD, SSD et NVMe**


```bash

apt update && apt install lm-sensors smartmontools -y

```

## 2. Détection du matériel

* **Exécutez l'assistant de détection pour identifier les modules nécessaires :**


```bash

sensors-detect

```

**Répondez YES (ou appuyez sur Entrée) à toutes les questions. À la fin, le système identifiera les modules nécessaires (par exemple : `coretemp` pour les processeurs Intel).**


## 3. Persistance des modules

**Pour que les capteurs s'activent automatiquement au redémarrage du serveur, l'assistant `sensors-detect` vous posera une question clé à la fin du processus :**


`Do you want to add these lines automatically to /etc/modules? (yes/NO)`



> [!CAUTION]
> **Vous devez écrire `yes` manuellement et appuyer sur Entrée.** Si vous appuyez simplement sur Entrée sans rien écrire, le système sélectionnera `NO` par défaut. Si cela se produit, les capteurs ne seront pas chargés après un redémarrage et Home Assistant cessera de recevoir les données de température.



## 4. Vérification immédiate

**Pour activer les capteurs dès maintenant sans avoir à redémarrer, exécutez :**



```bash

# Charge les modules détectés (exemple pour Intel)

modprobe coretemp

# Vérifie que les températures s'affichent

sensors

```

## 🚀 Étape 5 : Installation du Serveur de Capteurs (API Bridge)
**L'API officielle de Proxmox n'expose pas tous les capteurs matériels, il est donc nécessaire d'installer un petit script qui agit comme un pont entre Proxmox et Home Assistant.**

1. **Téléchargement et installation du script**
Exécutez ces commandes dans le terminal de votre serveur Proxmox :
```bash
# Télécharger le script depuis le dépôt
wget https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/scripts/pve-sensors-api.py -O /usr/local/bin/pve-sensors-api.py

# Donner les permissions d'exécution
chmod +x /usr/local/bin/pve-sensors-api.py
```
2. **Configuration en tant que service du système**
Créez le fichier de service :
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

3. **Activation immédiate**

```bash
systemctl daemon-reload
systemctl enable --now pve-sensors
```

4. **Vérification finale**
Ouvrez dans votre navigateur :
```
http://VOTRE_IP_PROXMOX:9000/sensors
```

Si un JSON avec les températures et les capteurs apparaît, le serveur fonctionne correctement.

## ✔ Conclusion

**Une fois que la commande sensors renvoie des lectures et que le service pve-sensors est actif, Home Assistant pourra obtenir toutes les données matérielles sans configurations supplémentaires.**
