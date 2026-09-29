Cluster monitoring provides a unified Home Assistant view of a Proxmox VE cluster.

While [PVE monitoring](../pve/) focuses on individual nodes and selected workloads, Cluster monitoring combines information from across the Proxmox environment so that the overall state of the cluster can be understood without treating each node as an isolated server.

This includes cluster status and quorum, node availability, aggregated resources, workloads, High Availability, failed tasks, firewall state, replication and backup health.

### What Cluster monitoring covers

A configured Cluster connection can provide information from several areas:

- **Cluster status and quorum** — whether the cluster currently has quorum and how many nodes are online or offline.
- [**Resources**](#resources) — aggregated CPU, memory and storage information across the cluster.
- **Workloads** — cluster-wide visibility into running virtual machines and containers.
- [**High Availability**](#high-availability) — information about the Proxmox HA environment when HA is configured.
- **Tasks and diagnostics** — failed-task information and supported cluster diagnostics such as firewall state.
- **Replication** — summary and status information for configured Proxmox replication jobs.
- **Backup monitoring** — configured backup jobs, backup age and an overall backup-health view.

Cluster monitoring is designed to complement PVE monitoring rather than replace it.

### Cluster and PVE provide different views

PVE monitoring answers questions about a particular node or workload:

- What is the CPU usage of this node?
- What temperature is this host reporting?
- What is the state of this VM?
- How much storage is available on this PVE resource?

Cluster monitoring answers broader questions:

- Does the cluster have quorum?
- How many nodes are online?
- How much CPU or memory is being used across the cluster?
- How many VMs and containers are running?
- Is High Availability active?
- Have cluster tasks failed?
- Is replication healthy?
- Are expected backups being created?

Both views can be useful at the same time.

### A cluster is more than a collection of nodes

The most useful cluster information often comes from relationships between resources.

A single node being offline, for example, has a different operational meaning depending on whether the remaining cluster still has quorum, whether HA is configured and where the affected workloads are running.

For this reason, Cluster monitoring should be interpreted as a view of the Proxmox environment as a whole rather than simply as another set of node sensors.

### Home Assistant organization

Cluster information is represented through a dedicated Home Assistant cluster device and related entities.

This keeps cluster-wide information separate from the devices representing individual PVE nodes, VMs, containers and storage resources.

You do not need to display every cluster entity.

A compact cluster overview containing quorum, nodes, resources, HA, failed tasks, replication and backup health can often provide more useful operational information than displaying every available value simultaneously.

### Where to continue

The following sections explain the main areas of Cluster monitoring:

- [**Quorum & Nodes**](#quorum-nodes)
- [**Resources**](#resources)
- [**Guests**](#guests)
- [**High Availability**](#high-availability)
- [**Tasks & Diagnostics**](#tasks-diagnostics)
- [**Backup Health**](#backup-health)
- [**Troubleshooting**](#troubleshooting)
