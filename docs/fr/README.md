# 📚 Documentation et Guides

Ces guides couvrent les étapes nécessaires pour configurer correctement l'intégration et profiter de toutes ses fonctionnalités.

---

## 🌡️ [01. Configuration des Capteurs Matériels](01-install-sensors.md)
Comment installer et configurer **lm-sensors** sur votre nœud Proxmox pour activer la surveillance de la température et des ventilateurs.

---

## 🔑 [02. Configuration de Proxmox](02-proxmox-config.md)
Comment créer un **utilisateur** et un **jeton API** sécurisés dans Proxmox (PVE et PBS) avec les autorisations minimales nécessaires.

---

## ⚙️ [03. Connexion de l'Intégration (PVE et PBS)](03-login-pve-pbs.md)
Guide pas à pas pour connecter l'intégration à vos serveurs depuis Home Assistant.

---

## ❓ [04. Foire Aux Questions et Dépannage](04-faq.md)
Problèmes courants, questions fréquentes et comment les résoudre.

---

<p align="center">
  <img src="https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/img/logo_int_v4.png" alt="Logo Proxmox Extended Sensors" width="600"/>
</p>

---

# 🚀 Proxmox Extended Sensors

## Introduction

**Proxmox Extended Sensors est une intégration pour Home Assistant conçue pour fournir une surveillance avancée et un contrôle complet de Proxmox VE et de Proxmox Backup Server (PBS).**

Contrairement aux solutions basées uniquement sur des métriques, cette intégration introduit une approche centrée sur les **informations utiles (insight)** , permettant de comprendre non seulement ce qui se passe dans le système, mais aussi comment il fonctionne réellement.

Elle offre une visibilité complète de l'infrastructure et ajoute des capacités de contrôle direct sur les nœuds, les machines virtuelles, les conteneurs, le stockage et les services de sauvegarde.

---

## 🧠 System Insight (V3/V4)

À partir de la version 3, l'intégration est passée d'une collection de métriques techniques à un système d'observabilité orienté infrastructure.

V4 introduit des capteurs capables d'interpréter l'état global du nœud et de transformer des métriques complexes en informations utiles et exploitables :

- **Nœud Proxmox** → état global du nœud (`Excellent`, `Warning`, `Critical`, etc.) avec attributs d'infrastructure enrichis
- **Score du nœud** → évaluation numérique des performances et de la santé générale du système
- **Charge moyenne (1m / 5m / 15m)** → charge réelle de l'hôte
- **Attente E/S** → détection de la pression et de la saturation du disque
- **Utilisation CPU par cœur** → disponible pour les nœuds, les VM et les conteneurs
- **Télémétrie réseau du nœud** → calcul intelligent du trafic RX/TX agrégé depuis les VM et les CT
- **Informations avancées de stockage** → état, capacité et métriques détaillées des disques physiques et des stockages

Ces capteurs permettent de détecter les goulots d'étranglement, d'identifier la dégradation du système et de construire des automatisations beaucoup plus intelligentes sans nécessiter d'outils externes supplémentaires.

---

## 🔍 Principales capacités de V4

- Surveillance globale du cluster Proxmox
- Détection avancée des disques montés (CIFS/NFS/local)
- Télémétrie intelligente du réseau et du stockage
- Capteurs agrégés de santé et d'infrastructure

### Surveillance complète de :

- Nœuds
- Machines virtuelles (QEMU)
- Conteneurs (LXC)
- Disques et stockage
- Proxmox Backup Server (PBS)

### Fonctionnalités avancées

- Actions de contrôle depuis Home Assistant
- Services de sauvegarde intégrés
- Compatibilité totale avec PBS (incluant la déduplication)
- Authentification sécurisée par jetons
- Structure d'entités propre et cohérente
- Mises à jour optimisées et faible consommation de ressources

---

## 🧩 Versions supportées

- Proxmox VE 7.x / 8.x / 9.x
- Compatible avec Linux Kernel 6.x / 7.x
- Proxmox Backup Server 3.x / 4.x
- Home Assistant 2024.x ou ultérieur

---

## 📑 Table des matières

- [Fonctionnalités clés](#-fonctionnalités-clés-v400)
- [État et performance du nœud](#-état-et-performance-du-nœud)
- [Disques et SMART](#-disques-et-smart)
- [Machines virtuelles (QEMU)](#-machines-virtuelles-qemu)
- [Conteneurs (LXC)](#-conteneurs-lxc)
- [Services de sauvegarde](#-services-de-sauvegarde-vms-et-cts)
- [Proxmox Backup Server (PBS)](#-proxmox-backup-server-pbs)
- [Actions de contrôle (PVE et PBS)](#-actions-de-contrôle-pve-et-pbs)
- [Installation](#-installation)
- [Guide visuel de configuration](#-guide-visuel-de-configuration)
- [Contributions](#-contributions-et-communauté)

---

## 🔥 Fonctionnalités clés de V4

### ⚙️ Configuration améliorée

- Découverte automatique des nœuds
- Sélection manuelle optionnelle
- Configuration plus simple et guidée
- Compatibilité avec les jetons API (PVE/PBS)
- Détection intelligente des autorisations limitées

---

### 🌐 Surveillance du cluster (NOUVEAU)

- Capteurs globaux du cluster Proxmox
- État des sauvegardes et des tâches échouées
- Nœuds en ligne/hors ligne
- Utilisation agrégée du CPU et de la RAM
- Comptage global des VM et des CT

---

### 💽 Disques montés et stockage (NOUVEAU)

- Détection automatique des disques montés
- Compatibilité avec CIFS / SMB et NFS
- Capteurs d'intégrité et de montages manquants
- Exclusion intelligente de tmpfs et des pseudo-montages
- Métriques détaillées d'utilisation et de capacité

---

### 🌡️ Surveillance matérielle avancée

- Températures en temps réel (CPU, VRM, chipset, disques)
- Capteurs de ventilateurs et de tensions
- Filtrage intelligent des capteurs valides
- Capteurs de température unifiés (CPU + NVMe)
- Compatibilité avancée Intel / AMD / ACPI / NVMe

> Nécessite `lm-sensors` sur l'hôte Proxmox

---

### 🧠 État et performance du nœud

- CPU, RAM, uptime, noyau et version PVE
- Surveillance réseau (RX/TX)
- Tâches et état du système
- Métriques avancées de charge et de performance
- Score du nœud et état global de l'infrastructure

---

### 💾 Disques et SMART

- Capteurs regroupés par disque physique
- Espace total/utilisé et métriques avancées
- Attributs SMART (HDD, SSD, NVMe)
- Températures par type de disque
- Métriques NVMe avancées et état de santé

---

### 🖥️ Machines virtuelles (QEMU)

- État, CPU, mémoire et disque
- Réseau RX/TX
- Informations de base et uptime
- Utilisation CPU par cœur
- Actions de contrôle depuis Home Assistant

---

### 📦 Conteneurs (LXC)

- État, CPU, mémoire et disque
- Réseau RX/TX
- Informations de base et uptime
- Utilisation CPU par cœur
- Actions de contrôle depuis Home Assistant

---

## 💾 Services de sauvegarde (VM et CT)

L'intégration permet de créer des sauvegardes directement depuis Home Assistant, entièrement compatibles avec Proxmox VE et PBS.

### 🟦 Sauvegarde individuelle

- Supporte plusieurs ID (séparés par des virgules)
- Modes : snapshot / suspend / stop
- Compression : zstd / gzip / lzo / none
- Compatible avec PBS et la déduplication

### 🟩 Sauvegarde massive

- Sauvegarde de toutes les ressources d'un nœud
- Contrôle de la concurrence et du timing
- Idéal pour l'automatisation
- Compatible avec les grandes infrastructures

Les sauvegardes sont automatiquement nommées comme suit :

```text
HA-{{vmid}}-{{guestname}}
```

Entièrement compatibles avec PBS, incluant la déduplication et les chaînes existantes.

---

## 🗄️ Proxmox Backup Server (PBS)

Surveillance avancée du datastore et des tâches :

- Utilisation totale, libre et pourcentage
- Taux de déduplication
- État de la dernière sauvegarde
- Erreurs et résumé des tâches
- État du Garbage Collector
- Informations détaillées des tâches

---

## 🎛️ Actions de contrôle (PVE & PBS)

**Nœud :**
- Éteindre / Redémarrer / Wake-on-LAN

**Machines virtuelles :**
- Démarrer / Arrêter / Éteindre / Redémarrer / Réinitialiser
- Pause / Reprendre / Hiberner

**Conteneurs :**
- Démarrer / Arrêter / Éteindre / Redémarrer

**PBS :**
- Garbage Collector
- Élaguer (Prune)
- Vérifier
- Synchroniser

---

## 🎨 Organisation et structure

- Capteurs automatiquement regroupés en :
  1. Cluster
  2. Nœud
  3. Disques physiques
  4. Machines virtuelles
  5. Conteneurs
  6. Stockage / Datastores
  7. PBS et tâches

- Noms cohérents et clairs pour faciliter les tableaux de bord et les automatisations

---

## 🧩 Installation

### 🔹 Via HACS (recommandé)

1. Ouvrir **HACS → Intégrations**
2. Ajouter un dépôt personnalisé
3. Rechercher **Proxmox Extended Sensors**
4. Installer et redémarrer Home Assistant
5. Ajouter l'intégration depuis les paramètres

### 🔹 Installation manuelle

1. Copier dans `/config/custom_components/proxmox_sensors`
2. Redémarrer Home Assistant
3. Ajouter l'intégration

---

## 🧭 Guide visuel de configuration

Vous trouverez ci-dessous un parcours visuel complet du processus de configuration, incluant les méthodes d'accès, la sélection des ressources et les étapes d'installation.

<details>
  <summary>🪪 Connexion au serveur</summary>
  <p align="center">
    <img src="../../img/install/setup_pve_1.png" alt="Connexion Proxmox" width="600">
  </p>
  <p align="center"><i>Il n'est pas nécessaire d'inclure "http://" ou "https://". Cela est géré automatiquement.</i></p>
</details>

<details>
  <summary>🪪 Connexion avec nom d'utilisateur et mot de passe (PVE uniquement)</summary>
  <p align="center">
    <img src="../../img/install/access_passw.png" alt="Connexion nom d'utilisateur et mot de passe" width="600">
  </p>
  <p align="center"><i>Assurez-vous d'utiliser le bon domaine (`pam` ou `pve`).</i></p>
</details>

<details> 
  <summary>🪪 Connexion avec utilisateur et jeton (PVE et PBS)</summary>
  <p align="center">
    <img src="../../img/install/access_token.png" alt="Connexion par jeton" width="600">
  </p>
  <p align="center"><i>Dans le champ Token_id, vous devez uniquement saisir le nom du jeton.</i></p>
</details>

<details>
  <summary>🧠 Sélection des nœuds (V4)</summary>
  <p align="center">
    <img src="../../img/install/node_select.png" alt="Sélection des nœuds" width="600">
  </p>
  <p align="center"><i>Sélectionnez les nœuds détectés automatiquement ou définissez manuellement lesquels inclure.</i></p>
</details>

<details>
  <summary>⚙️ Sélection des ressources</summary>
  <p align="center">
    <img src="../../img/install/resources_select.png" alt="Sélection des ressources" width="600">
  </p>
  <p align="center"><i>Sélectionnez les CT, VM et stockages que vous souhaitez inclure, ainsi que les options correspondantes.</i></p>
</details>

---

**Si cette intégration vous est utile, pensez à laisser une ⭐ sur GitHub.**

---

## 🤝 Contributions et communauté

Les contributions sont les bienvenues. Vous pouvez ouvrir des issues ou des pull requests.
Dépôt : https://github.com/Javisen/proxmox_sensors

---

<p align="center"><i>Maintenu par Javisen - Licence MIT</i></p>