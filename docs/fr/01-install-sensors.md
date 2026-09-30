# 🌡️ Étape 1 : Capteurs matériels et Sidecar

Cette procédure prépare un nœud Proxmox VE pour les données matérielles non exposées par l'API Proxmox standard. V5 utilise le sidecar pour les températures, la mémoire, les montages et SMART, et expose **Sidecar Status**.

## 1. Installer les paquets
```bash
apt update && apt install lm-sensors smartmontools -y
```

## 2. Détecter les capteurs
```bash
sensors-detect
```
Suivez l'assistant et activez les modules adaptés au matériel. Si l'assistant propose d'ajouter les modules à `/etc/modules`, enregistrez ceux nécessaires au redémarrage.

## 3. Vérifier
```bash
sensors
```
Pour un système Intel utilisant `coretemp`, si nécessaire :
```bash
modprobe coretemp
sensors
```
Ne forcez pas `coretemp` sur un système utilisant un autre pilote.

## 4. Installer le Sidecar

Exécutez la commande suivante sur chaque hôte PVE/PBS sur lequel vous souhaitez installer le Hardware Sidecar :

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/scripts/install-sidecar.sh)
```

Lors de l'installation, vous serez invité à saisir l'adresse ou les adresses IP de vos instances Home Assistant. Plusieurs adresses IP peuvent être saisies en les séparant par des virgules.

Seules les adresses IP spécifiées seront autorisées à accéder au Hardware Sidecar.

> **Remarque :** Si le Sidecar est déjà installé, exécutez à nouveau la même commande pour mettre à jour l'installation existante et configurer les adresses IP Home Assistant autorisées.

## 5. Vérifier le Sidecar

Vérifiez l'état du service Sidecar :

```bash
systemctl status pve-sensors.service
```

Le service devrait apparaître comme `active (running)`.

---

## 6. En cas de panne
V5 conserve si possible les dernières valeurs matérielles valides. **Sidecar Status** indique l'état de Memory, Mounts, Sensors et SMART : `ok`, `degraded`, `error` ou `unknown`.

Suivant : [02. Utilisateur et permissions Proxmox](02-proxmox-config.md)
