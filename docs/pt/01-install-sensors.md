# 🚀 Passo 1: Instalação e configuração de sensores

**Este guia explica como preparar o nó Proxmox para que exponha os dados de hardware e garanta que as leituras de temperatura e os dados Smart estejam disponíveis para o Home Assistant.**


## 1. Instalação de dependências

*Para que a integração possa ler todos os sensores de hardware e os atributos SMART dos discos, é necessário instalar as seguintes ferramentas no Proxmox:*

- **lm-sensors** → Sensores de CPU, placa-mãe, chipset, VRM, ventoinhas…**
- **smartmontools** → Informações SMART de HDD, SSD e NVMe**


```bash

apt update && apt install lm-sensors smartmontools -y

```

## 2. Deteção de hardware

* **Execute o assistente de deteção para identificar os módulos necessários:**


```bash

sensors-detect

```

**Responda YES (ou prima Enter) a todas as perguntas. Ao terminar, o sistema identificará os módulos necessários (por exemplo: `coretemp` para CPUs Intel).**


## 3. Persistência de módulos

**Para que os sensores se ativem sozinhos ao reiniciar o servidor, o assistente `sensors-detect` fará uma pergunta fundamental no final do processo:**


`Do you want to add these lines automatically to /etc/modules? (yes/NO)`



> [!CAUTION]
> **Deve escrever `yes` manualmente e premir Enter.** Se apenas premir Enter sem escrever nada, o sistema selecionará `NO` por defeito. Se isto acontecer, os sensores não serão carregados após um reinício e o Home Assistant deixará de receber dados de temperatura.



## 4. Verificação imediata

**Para ativar os sensores agora mesmo sem ter de reiniciar, execute:**



```bash

# Carrega os módulos detetados (exemplo para Intel)

modprobe coretemp

# Verifica se as temperaturas são apresentadas

sensors

```

## 🚀 Passo 5: Instalação do Servidor de Sensores (API Bridge)
**A API oficial do Proxmox não expõe todos os sensores de hardware, pelo que é necessário instalar um pequeno script que atua como ponte entre o Proxmox e o Home Assistant.**

1. **Download e instalação do script**
Execute estes comandos no terminal do seu servidor Proxmox:
```bash
# Descarregar o script do repositório
wget https://raw.githubusercontent.com/Javisen/proxmox_sensors/main/scripts/pve-sensors-api.py -O /usr/local/bin/pve-sensors-api.py

# Dar permissões de execução
chmod +x /usr/local/bin/pve-sensors-api.py
```
2. **Configuração como serviço do sistema**
Crie o ficheiro de serviço:
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

3. **Ativação imediata**

```bash
systemctl daemon-reload
systemctl enable --now pve-sensors
```

4. **Verificação final**
Abra no seu navegador:
```
http://O_SEU_IP_PROXMOX:9000/sensors
```

Se aparecer um JSON com temperaturas e sensores, o servidor está a funcionar corretamente.

## ✔ Conclusão

**Assim que o comando sensors devolve leituras e o serviço pve-sensors está ativo, o Home Assistant poderá obter todos os dados de hardware sem necessidade de configurações adicionais.**
