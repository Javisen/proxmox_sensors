Cluster monitoring includes operational signals that can help identify problems without continuously reviewing the Proxmox task history.

Particularly useful areas include failed tasks, replication state and cluster firewall information.

### Failed tasks

The Failed Tasks entity provides a cluster-wide view of recent Proxmox operations that did not complete successfully.

Its entity state acts as the high-level counter.

A non-zero value is therefore a signal that something in the recent cluster activity deserves investigation.

### Failed task attributes

The Failed Tasks entity also exposes attributes that provide context about the latest recorded failure.

Depending on the available task information, these can include:

- **Last failure** — when the latest recorded failure occurred;
- **Last node** — the node associated with that failure;
- **Last task** — available task context including the reported status;
- **Last task type** — the Proxmox task type associated with the failure.

These attributes provide diagnostic context for the **latest recorded failure**.

They do not represent a complete history of every failed task represented by the counter.

<figure class="pve-figure">
  <img src="../../images/documentation/cluster/cluster-6.png" width="564" height="734" loading="lazy" decoding="async" alt="Failed Tasks entity details showing the count and attributes for the latest recorded failure, node, task and task type." />
  <figcaption>Failed Tasks details — the entity count provides the alert signal while its attributes identify the latest recorded failure, node and task type.</figcaption>
</figure>

### Investigate the task, not only the counter

A failed-task count tells you that a problem occurred, but not necessarily how serious it is or what caused it.

The task type, node, timestamp and available status information provide the context needed to understand the latest recorded failure.

A failed manual operation, an unsuccessful backup and a failed migration are different events even if they all contribute to the same high-level problem signal.

Use the cluster signal to detect the problem and the detailed task information to diagnose it.

### Backup failures can appear here

Backup jobs executed by PVE create Proxmox tasks.

When those tasks fail, the failure belongs to the PVE/cluster operational side of the backup process.

This is different from PBS reporting the health of backups already stored in a datastore.

A failed backup task can therefore appear in cluster task monitoring while the existing backups on PBS remain healthy.

This distinction is important when diagnosing backup problems.

### Replication

Proxmox Extended Sensors can monitor the state of replication jobs configured in the cluster.

Cluster monitoring provides a summary of the configured replication jobs together with an overall replication status.

Additional entity attributes can provide diagnostic context such as:

- whether the replication inventory information is current;
- whether runtime information is current;
- the number of failed jobs;
- whether any configured jobs have an unknown runtime state.

A healthy replication status indicates that the information currently available to the integration does not report a replication problem.

It does not replace the detailed replication configuration and job history available in Proxmox VE.

Replication jobs remain configured and managed in Proxmox.

Proxmox Extended Sensors monitors their state so Home Assistant can surface failures or unexpected conditions.

<figure class="pve-figure">
  <img src="../../images/documentation/cluster/cluster-7.png" width="506" height="255" loading="lazy" decoding="async" alt="Historical Cluster Replication view showing one job for CT 104 with status ok." />
  <figcaption>Cluster replication — configured replication jobs can be monitored together with their current reported status.</figcaption>
</figure>

The screenshot is a historical example from a cluster configuration with active replication. It shows one configured replication job for CT 104 with status `ok`.

When replication is used in an environment, Replication Status can be particularly useful for notifications because a change from the normal state can draw attention to a problem without requiring continuous inspection of the Proxmox replication interface.

### Firewall state

Cluster monitoring can expose the state of the Proxmox firewall configuration available through the cluster.

This provides a simple diagnostic indicator in Home Assistant.

It should not be treated as a replacement for reviewing firewall rules in Proxmox VE.

The sensor indicates the relevant state reported by Proxmox; firewall rules and security policy remain configured and managed in Proxmox.

### Notifications and automation

Failed tasks, replication problems and other cluster-state changes can be useful notification signals because many important Proxmox operations normally complete without requiring manual attention.

Home Assistant can surface an unexpected condition instead of requiring the administrator to repeatedly inspect the Proxmox interfaces.

As with other alerts, automation should provide enough context to identify what needs investigation rather than simply repeating that a counter or state changed.

For the complete list of task, replication and diagnostic Cluster entities, see [**Reference**](../reference/).
