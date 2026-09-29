PVE monitoring is the core of Proxmox Extended Sensors and provides Home Assistant with visibility into the Proxmox VE hosts and workloads that you choose to monitor.

The integration organizes this information into Home Assistant devices and entities so that node health, resource usage, virtual machines, containers, storage and supported hardware information can be used in dashboards, notifications and automations.

### What PVE monitoring covers

A configured PVE connection can provide information from several areas of a Proxmox VE environment:

- [**Node monitoring**](#node-monitoring) — status, CPU, memory, swap, load, I/O wait, network activity and other node-level information.
- **Virtual machines and containers** — status and resource information for the guests selected for monitoring.
- [**Storage**](#storage) — capacity, usage and status information for storage resources available through PVE.
- **Hardware monitoring** — supported temperature, NVMe, SMART and memory information when the required data is available on the Proxmox host.

The exact entities available depend on the host, its hardware, the selected monitoring options and the information exposed by Proxmox.

### Designed for standalone and clustered environments

PVE monitoring can be used with a standalone Proxmox VE host or with nodes that belong to a cluster.

In a standalone installation, the PVE connection provides the main view of the server and its workloads.

In a clustered environment, PVE continues to provide detailed node-level information while the [**Cluster**](../cluster/) part of Proxmox Extended Sensors can provide the broader cluster-wide view.

This separation allows detailed monitoring to remain associated with the relevant PVE resources without losing the overall view of the environment.

### Home Assistant organization

Proxmox Extended Sensors represents the monitored Proxmox environment using Home Assistant devices and entities.

This keeps related information grouped together and makes it easier to identify whether an entity belongs to a node, virtual machine, container, storage resource or supported hardware component.

You do not need to use every entity that the integration exposes. The goal is to make the Proxmox information that matters to your environment available wherever Home Assistant can make useful use of it.

### Where to continue

If this is your first PVE connection, continue with [**Authentication**](#authentication) to prepare access in Proxmox VE and then [**Configuration**](#configuration) to add the server to Proxmox Extended Sensors.

The remaining sections cover the information exposed after setup:

- [**Node monitoring**](#node-monitoring)
- [**VM & CT monitoring**](#vm-ct-monitoring)
- [**Hardware**](#hardware)
- [**Storage**](#storage)
- [**Troubleshooting**](#troubleshooting)
