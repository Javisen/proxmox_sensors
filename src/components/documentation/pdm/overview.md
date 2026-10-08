PDM monitoring provides a centralized Home Assistant view of the Proxmox VE and Proxmox Backup Server environments managed by one Proxmox Datacenter Manager connection.

It is designed for Datacenter-level visibility: overall status, aggregate capacity, centralized inventory, available updates and the state of configured PVE/PBS remotes.

### PDM complements direct connections

PDM does not recreate the detailed monitoring supplied by direct PVE, PBS or Cluster connections.

Use PDM when you want to see several managed environments together. Keep direct connections when you need node hardware, individual VM/LXC entities, detailed backup operations or supported actions.

### Current V5.2 scope

The current implementation creates:

- one PDM root device;
- **Datacenter Status**, **Datacenter Inventory**, **Datacenter Capacity** and **Datacenter Updates** sensors;
- one child device for every configured PVE or PBS remote;
- **Remote Status** and **Remote Overview** sensors for each remote.

PDM V5.2 does not create individual VM or container entities and does not provide PDM actions or buttons.

Continue with [Configuration](#configuration) to add a connection or [Datacenter Monitoring](#datacenter-monitoring) to understand the centralized view.
