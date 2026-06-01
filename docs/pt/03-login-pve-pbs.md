# 🔌 Passo 3: Instalação da Integração no Home Assistant

Para visualizar todos os dados (temperaturas, sensores de hardware, discos, PBS, VMs e CTs), utilizaremos a integração **Proxmox Extended Sensors**.

---

## 1. Instalação através do HACS

Por ser uma integração personalizada, primeiro deves adicioná-la ao HACS:

1. Vá a **HACS → Integrações**
2. Clique nos **três pontos** (canto superior direito)
3. Selecione **Repositórios personalizados**
4. Adicione este repositório:
   `https://github.com/Javisen/proxmox_sensors/`
5. Em **Categoria**, selecione `Integração`
6. Instale a integração e **reinicie o Home Assistant**

---

## 2. Adicionar a integração

Após reiniciar:

1. Vá a **Configurações → Dispositivos e Serviços**
2. Clique em **Adicionar Integração**
3. Procure por **Proxmox Extended Sensors**

---

## 3. Configuração da ligação

### 🔹 Host
- **Rede local:** `192.168.1.50`
- **Acesso externo:** `proxmox.meudominio.com`

> Não é necessário incluir `http://` ou `https://`. Isto é detetado automaticamente.

---

### 🔹 Tipo de servidor
- **CLUSTER** → Cluster Proxmox
- **PVE** → Proxmox Virtual Environment
- **PBS** → Proxmox Backup Server

---

### 🔹 Método de autenticação

- **Utilizador + palavra-passe** → apenas em PVE e Cluster
- **Token API** → Obrigatório em PBS

---

## 🔐 Opção A: Utilizador e palavra-passe (apenas PVE)

Campos:

- **Utilizador:** `utilizador@realm`
  - Exemplo: `homeassistant@pve`
- **Palavra-passe:** palavra-passe do utilizador

> 💡 Desde a V3, o nó é detetado automaticamente. Não é necessário inseri-lo manualmente.

---

## 🔐 Opção B: Token API (recomendado)

Campos:

- **Utilizador:** `utilizador@realm`
- **ID do Token:** apenas o nome → `ha-token`
- **Segredo do Token:** o segredo gerado no Proxmox

> ⚠️ Não utilize o formato `utilizador@pve!token`

---

## 🧠 Seleção de recursos (PVE)

Após a ligação, a integração detetará automaticamente os recursos disponíveis.

Poderá selecionar:

- Máquinas virtuais (VMs)
- Contentores (CTs)
- Discos físicos
- Armazenamentos

> 💡 Selecione apenas o necessário para manter o Home Assistant limpo e eficiente.

---

## 🧭 Guia Visual de Instalação

Segue-se o processo completo com capturas de ecrã:

<details>
  <summary>🪪 Ligação ao servidor</summary>
  <p align="center">
    <img src="../../img/install/setup_pve_1.png" alt="Ligação Proxmox" width="600">
  </p>
  <p align="center"><i>Não é necessário incluir http/https.</i></p>
</details>

<details>
  <summary>🪪 Início de sessão com utilizador e palavra-passe (PVE)</summary>
  <p align="center">
    <img src="../../img/install/access_passw.png" alt="Início de sessão utilizador" width="600">
  </p>
  <p align="center"><i>Utilize o realm correto (pam ou pve).</i></p>
</details>

<details>
  <summary>🪪 Início de sessão com token (PVE e PBS)</summary>
  <p align="center">
    <img src="../../img/install/access_token.png" alt="Início de sessão com token" width="600">
  </p>
  <p align="center"><i>Insira apenas o nome do token no ID do Token.</i></p>
</details>

<details>
  <summary>🧠 Seleção de nós (V3)</summary>
  <p align="center">
    <img src="../../img/install/node_select.png" alt="Seleção de nós" width="600">
  </p>
  <p align="center"><i>Os nós são detetados automaticamente e podem ser selecionados manualmente.</i></p>
</details>

<details>
  <summary>⚙️ Seleção de recursos</summary>
  <p align="center">
    <img src="../../img/install/resources_select.png" alt="Seleção de recursos" width="600">
  </p>
</details>

---

## ⚠️ Nota sobre PBS em ambientes geridos

Se utilizar um PBS **gerido ou multi-tenant** (Tuxis, Hetzner, etc.):

- Não terá acesso aos sensores de hardware
- Não verá temperaturas nem discos físicos
- Não haverá métricas do nó

Isto é normal porque:

- Não tem acesso ao hardware real
- O fornecedor restringe o sistema
- Não existem permissões de baixo nível

**Resultado:**
Apenas serão exibidos dados limitados do datastore.

---