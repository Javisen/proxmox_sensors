Node monitoring provides a continuous view of the state and resource usage of your Proxmox VE host.

Proxmox Extended Sensors exposes the most useful node-level information as Home Assistant entities, allowing the server to be included in dashboards, notifications and automations without replacing the detailed administration tools available in Proxmox VE.

### Node status

The node status provides a simple indication of whether the Proxmox VE host is available to the integration.

This can be useful as a high-level health indicator and as a condition for Home Assistant automations that depend on the availability of the server.

A node becoming unavailable does not necessarily mean that the server itself has failed. Network connectivity, authentication or communication with the Proxmox API can also affect the information available to Home Assistant.

### CPU and system load

CPU usage shows how much processor capacity is currently being used by the node.

System load provides additional context by representing the amount of work waiting for or using system resources.

These values are useful together: CPU usage provides an immediate view of processor activity, while load can help identify sustained pressure that may not be obvious from a single CPU percentage.

### Memory and swap

Memory monitoring provides visibility into the RAM used by the Proxmox host and its workloads.

Swap information can provide additional context when investigating memory pressure.

Occasional swap usage does not by itself indicate a problem, but changes in memory and swap behaviour can be useful when diagnosing resource constraints or comparing normal operation with periods of unusually high activity.

### I/O wait

I/O wait represents time during which the system is waiting for storage operations to complete.

It can be particularly useful when investigating a node that feels slow even though CPU usage does not appear unusually high.

Sustained or abnormal I/O wait may justify checking the underlying storage workload and hardware in more detail.

### Network activity

Network monitoring provides receive and transmit activity for the node.

This information can help identify periods of high network usage and provide context for operations such as backups, migrations, media transfers or other workloads that generate significant traffic.

As with other resource metrics, the value is often most useful when compared with the normal behaviour of your own environment.

### Resource information works best together

Individual metrics rarely tell the complete story.

For example, high CPU usage may be expected during a demanding workload, while increased network and storage activity may be normal during a backup operation.

Combining CPU, load, memory, swap, I/O wait and network information provides a much more useful picture of what the node is doing.

<div class="pve-figure-pair">
  <figure class="pve-figure">
    <img src="../../images/documentation/pve/pve-2.png" width="508" height="398" loading="lazy" decoding="async" alt="Node Info view showing operational information from a monitored PVE node." />
    <figcaption>Node Info — operational information from the monitored PVE node.</figcaption>
  </figure>
  <figure class="pve-figure">
    <img src="../../images/documentation/pve/pve-3.png" width="509" height="249" loading="lazy" decoding="async" alt="Node Health view showing CPU, memory, swap and load metrics." />
    <figcaption>Node Health — CPU, memory, swap and load information provide additional context about node activity.</figcaption>
  </figure>
</div>

Home Assistant can display these values together on a dashboard or use selected conditions to notify you when behaviour moves outside the range you consider normal.

### Monitor trends, not every fluctuation

Node metrics can change constantly.

Not every short CPU spike, increase in network traffic or temporary change in memory usage requires attention.

When creating dashboards and automations, focus on sustained conditions and information that helps identify meaningful changes in the behaviour of the node.

For the complete list of node entities exposed by the integration, see [**Reference**](../reference/).
