Once PBS authentication has been prepared, the server can be added to Proxmox Extended Sensors from Home Assistant.

A PBS connection creates its own Home Assistant configuration entry and remains separate from PVE and Cluster connections.

### Add the PBS server

In Home Assistant, open:

**Settings → Devices & services → Add Integration**

Search for **Proxmox Extended Sensors**.

Enter the PBS host and select:

**Proxmox Backup Server (PBS)**

when choosing the server type.

<figure class="pve-figure">
  <img src="../../images/documentation/pbs/pbs-1.png" width="568" height="506" loading="lazy" decoding="async" alt="Proxmox Extended Sensors server connection form with Proxmox Backup Server selected as the server type." />
  <figcaption>Server connection — select PBS when adding a Proxmox Backup Server to Proxmox Extended Sensors.</figcaption>
</figure>

### Connect using the PBS API Token

The current V5 PBS setup uses API Token authentication.

Enter the credentials prepared in the [Authentication](#authentication) section:

- **User**
- **Token ID**
- **Token Secret**

These are separate values.

The Token ID can be a short name or a complete API token identifier containing `!`. See [**Hosted / Remote PBS**](#hosted-remote) for the exact rule and a tested hosted example.

<figure class="pve-figure">
  <img src="../../images/documentation/pbs/pbs-2.png" width="568" height="541" loading="lazy" decoding="async" alt="PBS access credentials form with separate User, Token ID and Token Secret fields and SSL verification option." />
  <figcaption>PBS access credentials — User, Token ID and Token Secret are entered as separate values.</figcaption>
</figure>

### Server identity

Each PBS configuration is treated as a distinct server by Proxmox Extended Sensors.

This is particularly important when multiple PBS instances are configured because similarly named resources must remain associated with the correct server.

From a user perspective, each PBS connection should therefore be considered an independent backup environment even when two servers contain datastores with similar purposes or names.

### What becomes available

After a successful connection, Proxmox Extended Sensors discovers the PBS information available to the configured account.

Depending on the server and permissions, this can include:

- server health information;
- datastores;
- capacity and deduplication information;
- stored backup information;
- maintenance status;
- PBS tasks;
- supported maintenance actions.

Not every PBS environment exposes every category.

Hosted services in particular may intentionally restrict access to server-level information while still providing datastore and backup information.

### Configuration can evolve

As with PVE, the initial configuration does not need to determine how every PBS entity will eventually be used.

Start by confirming that the server and expected datastores are available and that the information relevant to your backup workflow appears correctly.

Dashboard views, notifications and automations can then be added around the information that has a useful purpose.

If the connection succeeds but expected information is missing, see [**Troubleshooting**](#troubleshooting).
