Cluster resource monitoring combines information from multiple Proxmox nodes to provide an overall view of how the cluster is being used.

This is useful for understanding capacity and workload distribution without replacing the detailed per-node information available through PVE monitoring.

### Cluster CPU usage

The cluster CPU sensor represents aggregated processor usage across the online cluster nodes.

Instead of treating each node percentage equally, the calculation takes the available CPU capacity of the nodes into account.

This produces a cluster-wide utilization value that better represents the processor resources currently being consumed.

Per-node CPU information remains useful for identifying where the workload is located, while the cluster value answers a different question:

**How much of the cluster's available CPU capacity is currently being used?**

### Cluster memory usage

Cluster memory monitoring combines the memory used and available across the online nodes.

This provides an overall RAM utilization percentage together with useful capacity context.

Per-node information remains important because a cluster can have significant free memory overall while one particular node is under memory pressure.

The aggregate value should therefore be used as a cluster-capacity indicator rather than as a replacement for node monitoring.

<figure class="pve-figure">
  <img src="../../images/documentation/cluster/cluster-3.png" width="509" height="252" loading="lazy" decoding="async" alt="Cluster Health showing CPU, RAM and Failed Tasks entities." />
  <figcaption>Cluster Health — aggregated CPU and RAM provide capacity context while Failed Tasks remains an independent operational signal.</figcaption>
</figure>

### Workloads contribute to resource usage

CPU and memory utilization should be interpreted together with the workloads currently running in the cluster.

A change in cluster resource usage may be expected after:

- starting or stopping guests;
- migrating workloads;
- maintenance operations;
- changing workload demand.

The aggregate view provides context while PVE and guest monitoring provide the detail needed to identify the source.

### Cluster storage usage

Cluster monitoring can also provide an aggregated view of the storage resources reported through the cluster.

This can include overall used and total capacity together with information about the storage resources contributing to that value.

As with other aggregate metrics, the cluster percentage should not replace monitoring of individual storage resources.

A cluster may have substantial total free capacity while one important storage resource is approaching its own limit.

<figure class="pve-figure">
  <img src="../../images/documentation/cluster/cluster-4.png" width="510" height="255" loading="lazy" decoding="async" alt="Cluster System view showing Storage and Firewall entities." />
  <figcaption>Cluster system overview — aggregated storage usage and the reported Proxmox firewall state provide complementary cluster-level context.</figcaption>
</figure>

### Aggregated information needs context

Cluster-wide percentages are intentionally summaries.

They are useful for dashboards, trends and high-level alerts, but they should not be treated as proof that every node or storage resource is healthy.

A good monitoring strategy uses the cluster view to identify that something deserves attention and the corresponding PVE information to understand where it is happening.

For the complete list of Cluster resource entities, see [**Reference**](../reference/).
