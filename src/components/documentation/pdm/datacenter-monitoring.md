The PDM root device presents the information that belongs to the managed Datacenter as a whole.

### Datacenter Status

**Datacenter Status** reports `Good` when the known remotes are healthy and no failed remote is reported; otherwise it reports `Degraded`.

Its attributes summarize the total PVE/PBS remotes, failed remotes and the freshness of the polled PDM sections.

### Datacenter Inventory

**Datacenter Inventory** summarizes the resources reported through PDM. Depending on the managed environments, its attributes can include PVE/PBS nodes, VMs, containers, PVE storage, PBS datastores and SDN zones.

Unknown categories remain unknown rather than being presented as zero.

### Datacenter Capacity

**Datacenter Capacity** uses aggregate PVE and PBS information for CPU, memory and storage. Memory and storage are presented in GiB with calculated utilization percentages when both used and total values are available.

CPU is presented as used threads, available threads and—where PDM supplies it—allocated guest cores. CPU utilization is calculated from used threads divided by available threads.

This is an aggregate operational view. Direct PVE and PBS connections remain the detailed monitoring path for individual systems and resources.
