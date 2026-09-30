# 🌡️ Passo 1: Sensores de hardware e Sidecar

Este guia prepara um nó Proxmox VE para dados de hardware que não são expostos pela API Proxmox padrão. V5 usa o sidecar para temperaturas, memória, mounts e SMART e adiciona **Sidecar Status**.

## 1. Instalar pacotes
```bash
apt update && apt install lm-sensors smartmontools -y
```

## 2. Detetar sensores
```bash
sensors-detect
```
Siga o assistente e ative os módulos adequados. Se for proposta a gravação em `/etc/modules`, assegure que os módulos necessários persistem após reiniciar.

## 3. Verificar
```bash
sensors
```
Em Intel com `coretemp`, se necessário:
```bash
modprobe coretemp
sensors
```
Não force `coretemp` em sistemas que usam outro driver.

---

## 4. Instalar o Sidecar

Execute o seguinte comando em cada host PVE/PBS onde pretende instalar o Hardware Sidecar:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/scripts/install-sidecar.sh)
```

Durante a instalação, será solicitado que introduza o endereço ou os endereços IP das suas instâncias do Home Assistant. Pode introduzir vários endereços IP separados por vírgulas.

Apenas os endereços IP especificados terão permissão para aceder ao Hardware Sidecar.

> **Nota:** Se o Sidecar já estiver instalado, execute novamente o mesmo comando para atualizar a instalação existente e configurar os endereços IP autorizados do Home Assistant.

## 5. Verificar o Sidecar

Verifique o estado do serviço Sidecar:

```bash
systemctl status pve-sensors.service
```

O serviço deverá aparecer como `active (running)`.

---

## 6. Em caso de falha
V5 preserva, quando possível, os últimos valores de hardware válidos. **Sidecar Status** mostra Memory, Mounts, Sensors e SMART como `ok`, `degraded`, `error` ou `unknown`.

Seguinte: [02. Utilizador e permissões Proxmox](02-proxmox-config.md)
