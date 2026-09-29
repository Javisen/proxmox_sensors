Cluster monitoring provides a high-level view of virtual machines and LXC containers across the complete Proxmox cluster.

This complements the detailed guest monitoring available through PVE connections.

<figure class="pve-figure">
  <img src="../../images/documentation/cluster/cluster-2.png" width="508" height="251" loading="lazy" decoding="async" alt="Cluster Resources showing 2 nodes, 22 containers and 5 virtual machines." />
  <figcaption>Cluster resources — node, container and virtual-machine counts provide a compact view of the workloads known across the cluster.</figcaption>
</figure>

### Virtual machines

The cluster VM information summarizes the virtual machines known to the cluster and how many are currently running.

Additional information can identify the running workloads together with their VMID and current node.

This provides a quick operational view of the virtual-machine population without requiring every guest to be displayed individually.

### Containers

LXC containers are summarized separately from virtual machines.

The cluster CT information can provide:

- total containers;
- running containers;
- stopped containers;
- information about the running containers and their current nodes.

Keeping VMs and containers separate makes the cluster overview easier to understand while preserving the distinction between the two Proxmox workload types.

### Guests can move between nodes

One of the fundamental characteristics of a Proxmox cluster is that workloads are not permanently tied to one node.

A VM or container can migrate while remaining the same logical workload.

Cluster monitoring reflects the current cluster state and can show which node currently hosts a running guest.

For detailed monitoring of an individual selected VM or container, Proxmox Extended Sensors V5 is designed to preserve the guest's Home Assistant identity when it migrates between nodes within the configured cluster.

This allows dashboards, history and automations associated with that monitored guest to remain attached to the workload rather than to its previous node.

### Cluster guest counts and selected guest monitoring are different

The cluster summary can know about workloads across the cluster even when those workloads have not all been selected for detailed Home Assistant monitoring.

This distinction is intentional.

Cluster guest information provides an operational summary of the environment.

PVE guest selection determines which individual VMs and containers receive detailed Home Assistant entities.

You therefore do not need to monitor every guest individually simply to obtain a useful cluster-wide workload overview.

### Use both levels where useful

A cluster dashboard might show:

- total/running VMs;
- total/running containers;
- cluster CPU;
- cluster RAM.

Detailed cards or automations can then focus only on the particular guests that matter to your Home Assistant environment.

This keeps the cluster overview useful without creating unnecessary entity noise.

For detailed VM and CT monitoring, see [**PVE → VM & CT monitoring**](../pve/#vm-ct-monitoring).

For the complete list of Cluster guest entities, see [**Reference**](../reference/).
