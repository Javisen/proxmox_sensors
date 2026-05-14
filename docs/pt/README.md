# 📚 Documentação e Guias

Estes guias cobrem os passos necessários para configurar corretamente a integração e aproveitar todas as suas funcionalidades.

---

## 🌡️ [01. Configuração de Sensores de Hardware](01-install-sensors.md)
Como instalar e configurar o **lm-sensors** no seu nó Proxmox para ativar a monitorização de temperatura e ventoinhas.

---

## 🔑 [02. Configuração do Proxmox](02-proxmox-config.md)
Como criar um **utilizador** e um **Token de API** seguros no Proxmox (PVE e PBS) com as permissões mínimas necessárias.

---

## ⚙️ [03. Início de Sessão da Integração (PVE e PBS)](03-login-pve-pbs.md)
Guia passo a passo para conectar a integração aos seus servidores a partir do Home Assistant.

---

## ❓ [04. Perguntas Frequentes e Resolução de Problemas](04-faq.md)
Problemas comuns, dúvidas frequentes e como resolvê-los.

---

<p align="center">
  <img src="https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/img/logo_int_v4.png" alt="Logótipo Proxmox Extended Sensors" width="600"/>
</p>

---

# 🚀 Proxmox Extended Sensors

## Introdução

**Proxmox Extended Sensors é uma integração para Home Assistant concebida para fornecer monitorização avançada e controlo completo do Proxmox VE e do Proxmox Backup Server (PBS).**

Ao contrário de soluções baseadas apenas em métricas, esta integração introduz uma abordagem centrada em **informação útil (insight)** , permitindo compreender não só o que está a acontecer no sistema, mas também como está realmente a funcionar.

Fornece visibilidade completa da infraestrutura e adiciona capacidades de controlo direto sobre nós, máquinas virtuais, contentores, armazenamento e serviços de backup.

---

## 🧠 System Insight (V3/V4)

A partir da versão 3, a integração evoluiu de uma coleção de métricas técnicas para um sistema de observabilidade orientado para a infraestrutura.

A V4 introduz sensores capazes de interpretar o estado global do nó e transformar métricas complexas em informação útil e acionável:

- **Nó Proxmox** → estado global do nó (`Excellent`, `Warning`, `Critical`, etc.) com atributos de infraestrutura enriquecidos
- **Pontuação do Nó** → avaliação numérica do desempenho e saúde geral do sistema
- **Carga Média (1m / 5m / 15m)** → carga real do host
- **Espera de E/S** → deteção de pressão e saturação do disco
- **Uso de CPU por núcleo** → disponível para nós, VMs e contentores
- **Telemetria de rede do nó** → cálculo inteligente do tráfego RX/TX agregado de VMs e CTs
- **Informação avançada de armazenamento** → estado, capacidade e métricas detalhadas de discos físicos e armazenamentos

Estes sensores permitem detetar gargalos, identificar degradação do sistema e construir automações muito mais inteligentes sem necessidade de ferramentas externas adicionais.

---

## 🔍 Principais capacidades da V4

- Monitorização global do cluster Proxmox
- Deteção avançada de discos montados (CIFS/NFS/local)
- Telemetria inteligente de rede e armazenamento
- Sensores agregados de saúde e infraestrutura

### Monitorização completa de:

- Nós
- Máquinas virtuais (QEMU)
- Contentores (LXC)
- Discos e armazenamento
- Proxmox Backup Server (PBS)

### Funcionalidades avançadas

- Ações de controlo a partir do Home Assistant
- Serviços de backup integrados
- Compatibilidade total com PBS (incluindo desduplicação)
- Autenticação segura mediante tokens
- Estrutura de entidades limpa e consistente
- Atualizações otimizadas e baixo consumo de recursos

---

## 🧩 Versões Suportadas

- Proxmox VE 7.x / 8.x / 9.x
- Compatível com Linux Kernel 6.x / 7.x
- Proxmox Backup Server 3.x / 4.x
- Home Assistant 2024.x ou posterior

---

## 📑 Índice

- [Características Principais](#-características-principais-v400)
- [Estado e Desempenho do Nó](#-estado-e-desempenho-do-nó)
- [Discos e SMART](#-discos-e-smart)
- [Máquinas Virtuais (QEMU)](#-máquinas-virtuais-qemu)
- [Contentores (LXC)](#-contentores-lxc)
- [Serviços de Backup](#-serviços-de-backup-vms-e-cts)
- [Proxmox Backup Server (PBS)](#-proxmox-backup-server-pbs)
- [Ações de Controlo (PVE e PBS)](#-ações-de-controlo-pve-e-pbs)
- [Instalação](#-instalação)
- [Guia Visual de Configuração](#-guia-visual-de-configuração)
- [Contribuições](#-contribuições-e-comunidade)

---

## 🔥 Características Principais da V4

### ⚙️ Configuração Melhorada

- Descoberta automática de nós
- Seleção manual opcional
- Configuração mais simples e guiada
- Compatibilidade com Tokens de API (PVE/PBS)
- Deteção inteligente de permissões limitadas

---

### 🌐 Monitorização de Cluster (NOVO)

- Sensores globais do cluster Proxmox
- Estado de backups e tarefas falhadas
- Nós online/offline
- Uso agregado de CPU e RAM
- Contagem global de VMs e CTs

---

### 💽 Discos Montados e Armazenamento (NOVO)

- Deteção automática de discos montados
- Compatibilidade com CIFS / SMB e NFS
- Sensores de integridade e montagens em falta
- Exclusão inteligente de tmpfs e pseudo-montagens
- Métricas detalhadas de uso e capacidade

---

### 🌡️ Monitorização Avançada de Hardware

- Temperaturas em tempo real (CPU, VRM, chipset, discos)
- Sensores de ventoinhas e tensões
- Filtragem inteligente de sensores válidos
- Sensores de temperatura unificados (CPU + NVMe)
- Compatibilidade avançada Intel / AMD / ACPI / NVMe

> Requer `lm-sensors` no host Proxmox

---

### 🧠 Estado e Desempenho do Nó

- CPU, RAM, uptime, kernel e versão do PVE
- Monitorização de rede (RX/TX)
- Tarefas e estado do sistema
- Métricas avançadas de carga e desempenho
- Pontuação do Nó e estado global da infraestrutura

---

### 💾 Discos e SMART

- Sensores agrupados por disco físico
- Espaço total/usado e métricas avançadas
- Atributos SMART (HDD, SSD, NVMe)
- Temperaturas por tipo de disco
- Métricas NVMe avançadas e estado de saúde

---

### 🖥️ Máquinas Virtuais (QEMU)

- Estado, CPU, memória e disco
- Rede RX/TX
- Informação básica e uptime
- Uso de CPU por núcleo
- Ações de controlo a partir do Home Assistant

---

### 📦 Contentores (LXC)

- Estado, CPU, memória e disco
- Rede RX/TX
- Informação básica e uptime
- Uso de CPU por núcleo
- Ações de controlo a partir do Home Assistant

---

## 💾 Serviços de Backup (VMs e CTs)

A integração permite criar backups diretamente a partir do Home Assistant, totalmente compatíveis com Proxmox VE e PBS.

### 🟦 Backup Individual

- Suporta múltiplos IDs (separados por vírgula)
- Modos: snapshot / suspend / stop
- Compressão: zstd / gzip / lzo / none
- Compatível com PBS e desduplicação

### 🟩 Backup Massivo

- Backup de todos os recursos de um nó
- Controlo de concorrência e temporização
- Ideal para automação
- Compatível com grandes infraestruturas

Os backups são nomeados automaticamente como:

```text
HA-{{vmid}}-{{guestname}}
```

Totalmente compatíveis com PBS, incluindo desduplicação e cadeias existentes.

---

## 🗄️ Proxmox Backup Server (PBS)

Monitorização avançada de datastore e tarefas:

- Uso total, livre e percentagem
- Taxa de desduplicação
- Estado do último backup
- Erros e resumo de tarefas
- Estado do Coletor de Lixo (Garbage Collector)
- Informação detalhada das tarefas

---

## 🎛️ Ações de Controlo (PVE & PBS)

**Nó:**
- Desligar / Reiniciar / Wake-on-LAN

**Máquinas virtuais:**
- Iniciar / Parar / Desligar / Reiniciar / Repor
- Pausar / Retomar / Hibernar

**Contentores:**
- Iniciar / Parar / Desligar / Reiniciar

**PBS:**
- Coletor de Lixo (Garbage Collector)
- Podar (Prune)
- Verificar
- Sincronizar

---

## 🎨 Organização e estrutura

- Sensores automaticamente agrupados em:
  1. Cluster
  2. Nó
  3. Discos físicos
  4. Máquinas virtuais
  5. Contentores
  6. Armazenamento / Datastores
  7. PBS e tarefas

- Nomes consistentes e claros para facilitar dashboards e automações

---

## 🧩 Instalação

### 🔹 Via HACS (recomendado)

1. Abrir **HACS → Integrações**
2. Adicionar repositório personalizado
3. Procurar por **Proxmox Extended Sensors**
4. Instalar e reiniciar o Home Assistant
5. Adicionar a integração a partir das definições

### 🔹 Instalação manual

1. Copiar para `/config/custom_components/proxmox_sensors`
2. Reiniciar o Home Assistant
3. Adicionar a integração

---

## 🧭 Guia Visual de Configuração

Abaixo encontrará um percurso visual completo do processo de configuração, incluindo métodos de acesso, seleção de recursos e passos de instalação.

<details>
  <summary>🪪 Ligação ao Servidor</summary>
  <p align="center">
    <img src="../../img/install/setup_pve_1.png" alt="Ligação Proxmox" width="600">
  </p>
  <p align="center"><i>Não é necessário incluir "http://" ou "https://". Isto é gerido automaticamente.</i></p>
</details>

<details>
  <summary>🪪 Início de Sessão com Utilizador e Palavra-passe (apenas PVE)</summary>
  <p align="center">
    <img src="../../img/install/access_passw.png" alt="Início de sessão com utilizador e palavra-passe" width="600">
  </p>
  <p align="center"><i>Certifique-se de que utiliza o realm correto (`pam` ou `pve`).</i></p>
</details>

<details> 
  <summary>🪪 Início de Sessão com Utilizador e Token (PVE e PBS)</summary>
  <p align="center">
    <img src="../../img/install/access_token.png" alt="Início de sessão com token" width="600">
  </p>
  <p align="center"><i>No campo Token_id deve introduzir apenas o nome do token.</i></p>
</details>

<details>
  <summary>🧠 Seleção de Nós (V4)</summary>
  <p align="center">
    <img src="../../img/install/node_select.png" alt="Seleção de nós" width="600">
  </p>
  <p align="center"><i>Selecione os nós detetados automaticamente ou defina manualmente quais incluir.</i></p>
</details>

<details>
  <summary>⚙️ Seleção de Recursos</summary>
  <p align="center">
    <img src="../../img/install/resources_select.png" alt="Seleção de recursos" width="600">
  </p>
  <p align="center"><i>Selecione os CTs, VMs e armazenamentos que deseja incluir, juntamente com as opções correspondentes.</i></p>
</details>

---

**Se achar esta integração útil, considere deixar uma ⭐ no GitHub.**

---

## 🤝 Contribuições e Comunidade

Contribuições são bem-vindas. Pode abrir issues ou pull requests.
Repositório: https://github.com/Javisen/proxmox_sensors

---

<p align="center"><i>Mantido por Javisen - Licença MIT</i></p>