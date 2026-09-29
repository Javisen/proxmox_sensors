Proxmox Extended Sensors can monitor selected virtual machines and LXC containers alongside the PVE nodes that host them.

Instead of exposing every guest automatically, the integration lets you choose which VMs and containers are useful in Home Assistant.

This keeps guest monitoring focused while still providing the information needed for dashboards, notifications and automations.

### Select the guests that matter

A Proxmox environment can contain many virtual machines and containers, but Home Assistant does not necessarily need information from all of them.

Select the guests whose state or resource usage has a useful purpose in Home Assistant.

Typical examples include:

- infrastructure services you want to know are running;
- important application servers;
- containers involved in Home Assistant automations;
- workloads whose CPU or memory usage you want to observe;
- guests whose state you want to include on a dashboard.

The guest selection can be adjusted later as your environment changes.

### Guest status

Guest status provides a quick view of whether a selected VM or container is running, stopped or in another state reported by Proxmox.

This is often one of the most useful pieces of guest information because it can be displayed directly on a dashboard or used by Home Assistant as part of an automation.

For example, the state of an important service VM or container can be monitored without continuously opening the Proxmox interface.

### Resource monitoring

Selected guests can expose resource information such as CPU and memory usage together with other information available for that guest.

These metrics provide context about what a workload is doing and can help identify unusual behaviour or sustained resource pressure.

As with node monitoring, short-lived changes are not necessarily problems. Resource information is most useful when interpreted in relation to the normal behaviour and purpose of the guest.

### Guest controls

When the configuration and Proxmox permissions allow it, Proxmox Extended Sensors can also expose supported guest control actions in Home Assistant.

These can include actions such as:

- **Start**
- **Stop**
- **Shutdown**
- **Reboot**

Monitoring access and control access are not necessarily equivalent. An account may have sufficient permissions to read guest information while lacking the privileges required to perform control operations.

Use guest controls deliberately and grant only the permissions required for the functionality you intend to use.

<div class="pve-figure-pair">
  <figure class="pve-figure">
    <img src="../../images/documentation/pve/pve-4.png" width="509" height="683" loading="lazy" decoding="async" alt="Home Assistant VM monitoring view with guest controls and resource sensors." />
    <figcaption>VM monitoring — guest controls and resource sensors exposed in Home Assistant.</figcaption>
  </figure>
  <figure class="pve-figure">
    <img src="../../images/documentation/pve/pve-5.png" width="511" height="739" loading="lazy" decoding="async" alt="Home Assistant CT monitoring view with container controls and resource sensors." />
    <figcaption>CT monitoring — container controls and resource sensors remain separately represented.</figcaption>
  </figure>
</div>

### VMs and containers remain distinct

Virtual machines and LXC containers are different Proxmox workload types and remain represented separately by the integration.

This makes it easier to identify and organize them in Home Assistant while still providing a consistent monitoring experience.

The exact information available can differ between VMs and containers depending on what Proxmox exposes for each workload type.

### Guest identity in a cluster

In a clustered Proxmox environment, a virtual machine or container may move from one node to another.

Proxmox Extended Sensors V5 is designed so that a monitored guest remains the same Home Assistant resource when it migrates between nodes in the same configured cluster.

The node currently hosting the workload can change without turning the migrated guest into a new Home Assistant entity.

This is important for long-term monitoring because dashboards, automations, history and other Home Assistant configuration associated with the guest can remain attached to the same logical resource after migration.

In everyday use, the guest can therefore be treated as the workload it represents rather than as something permanently tied to a particular PVE node.

### Monitoring after migration

A migration can temporarily change where the integration obtains information about a guest, but the monitoring model is designed to follow the workload to its current node.

This means that cluster operations do not require you to rebuild your Home Assistant setup simply because a VM or container has moved.

For cluster-wide information such as quorum, overall resources, HA or the state of multiple nodes, use the dedicated [**Cluster**](../cluster/) monitoring section.

### Use guest information where it adds value

Guest monitoring is most effective when the information has a purpose.

A dashboard may only need the state and basic resource usage of important workloads, while an automation may only care whether a particular guest has unexpectedly stopped.

There is no benefit in giving every VM and container the same amount of attention simply because the information is available.

For the complete list of VM and CT entities exposed by the integration, see [**Reference**](../reference/).
