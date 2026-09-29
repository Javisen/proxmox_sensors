Quorum is one of the most important health indicators in a Proxmox VE cluster.

Proxmox Extended Sensors exposes cluster status together with node availability so Home Assistant can provide a simple view of whether the cluster is currently able to operate with quorum.

### Cluster status

The main cluster status represents whether the Proxmox cluster is currently **quorate** or has **no quorum**.

This provides a high-level health indicator for dashboards and automations.

A quorate cluster has the required voting majority according to its current Proxmox configuration.

A cluster without quorum requires attention because some cluster operations may be restricted or unavailable until quorum is restored.

<figure class="pve-figure">
  <img src="../../images/documentation/cluster/cluster-1.png" width="959" height="108" loading="lazy" decoding="async" alt="Cluster device showing Status as quorate." />
  <figcaption>Cluster status — the Cluster device provides a high-level view of the current Proxmox quorum state.</figcaption>
</figure>

### Nodes online

Cluster monitoring also provides a summary of the nodes currently online.

The information can include:

- total number of nodes;
- number of online nodes;
- number of offline nodes;
- which nodes are currently online;
- which nodes are currently offline.

This allows Home Assistant to distinguish between the overall quorum state and the availability of individual cluster members.

### Quorum and node availability are related but different

An offline node does not automatically mean that the cluster has lost quorum.

Likewise, the operational importance of an offline node depends on the size and voting configuration of the cluster.

For this reason, node availability and quorum should be read together.

A useful cluster dashboard can show both values prominently:

**Is the cluster quorate?**

and:

**Are all expected nodes online?**

These answer different questions.

### Use quorum as a high-value signal

Unlike rapidly changing CPU or network metrics, quorum normally represents a condition that deserves immediate attention when it changes unexpectedly.

This makes it particularly useful for Home Assistant notifications.

Automations should still be designed carefully to avoid unnecessary repeated notifications during planned maintenance or intentional node shutdowns.

For the complete list of Cluster status and node entities, see [**Reference**](../reference/).
