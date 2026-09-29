Cluster monitoring depends on Proxmox cluster information being available through the configured connection and permissions.

When something looks wrong, first determine whether the problem affects the entire cluster view or only one category such as nodes, HA, tasks, replication or backup monitoring.

### Cluster information does not appear

Confirm that the configured Proxmox environment is actually operating as a cluster and that the account used by Proxmox Extended Sensors can access the required cluster information.

Also verify that the relevant Cluster connection or configuration has been created in the integration.

If normal PVE monitoring works but Cluster information does not, permissions and cluster-specific API access are useful first checks.

### Cluster reports no quorum

A `no quorum` state comes from the cluster information reported by Proxmox.

Check the cluster directly in Proxmox VE.

Review:

- expected nodes;
- node availability;
- cluster communication;
- current voting/quorum state.

Home Assistant should be used to surface the condition, while diagnosis and recovery of the Proxmox cluster itself should be performed using the appropriate Proxmox administration tools.

### A node appears offline

Check whether the node is reachable and whether Proxmox itself reports it as online.

Remember that node availability and quorum are related but not identical.

A node being offline does not automatically mean the cluster has lost quorum.

Check both values before interpreting the overall cluster state.

### Aggregate resources look unexpected

Cluster CPU, RAM and storage are aggregated values.

They do not necessarily match the arithmetic average of the percentages shown for individual nodes.

Different nodes can have different CPU, memory and storage capacities.

Use the per-node information and the corresponding PVE monitoring when investigating an unexpected aggregate value.

### VM or CT counts look different from detailed monitoring

Cluster guest summaries describe workloads known across the cluster.

Detailed PVE guest monitoring only exposes the guests selected for individual Home Assistant monitoring.

The two counts therefore do not need to match the number of detailed guest devices or entities in Home Assistant.

### HA information is unavailable

Confirm that High Availability is actually configured in the Proxmox cluster.

If HA is not used, unavailable or limited HA information can be expected.

If HA is configured but the information is unexpectedly missing, check cluster quorum, Proxmox HA status and the permissions available to the integration.

### Failed Tasks is not zero

A non-zero Failed Tasks state means that recent Proxmox task information contains unsuccessful operations.

Inspect the entity attributes for additional context about the latest recorded failure.

Depending on the information available, these can identify:

- when the latest failure occurred;
- the associated node;
- the task type;
- available task status information.

The counter alone does not identify the root cause and the attributes do not represent a complete history of every failure.

Use the available context to identify the relevant task and investigate it in Proxmox when necessary.

### Replication reports a problem

If Replication Status reports a problem, check the replication jobs directly in Proxmox VE.

The entity attributes can provide additional context, including:

- failed jobs;
- whether inventory information is current;
- whether runtime information is current;
- whether any jobs have an unknown runtime state.

Use this information to identify that replication requires attention, then use the Proxmox replication interface and task information to diagnose the underlying cause.

Replication jobs are configured and managed in Proxmox, not by Home Assistant.

### A backup failed but PBS reports healthy backups

This can be expected.

Cluster backup/task monitoring represents the PVE side of the operation.

PBS reports the state of backup data available on the backup server.

If a new backup fails before completion, previously stored PBS backups can remain completely healthy.

Use the Cluster/PVE task information to diagnose the failed job and PBS monitoring to evaluate the backups actually stored on the server.

### Backup Age becomes high

First confirm whether the expected backup job has recently completed successfully.

Check:

- configured backup schedule;
- recent PVE tasks;
- guest availability;
- backup destination;
- any relevant failure messages.

Backup Age identifies that a sufficiently recent successful backup may be missing; it does not by itself identify why.

### Firewall information looks wrong

Confirm the firewall state directly in Proxmox VE.

The integration reports the cluster information available through Proxmox but does not replace inspection of firewall configuration or rules.

### Check Home Assistant logs

When the cause is not obvious, open:

**Settings → System → Logs**

Look for entries related to **Proxmox Extended Sensors** around the time the cluster problem occurred.

Remove credentials, API Token secrets and other sensitive information before sharing logs publicly.

### Before opening an issue

Try to determine whether the problem affects:

- the complete Cluster connection;
- quorum;
- node availability;
- aggregated resources;
- VM or CT summaries;
- HA;
- failed tasks;
- replication;
- firewall information;
- Backup Jobs;
- Backup Age;
- or Backup Health.

Include the relevant Proxmox Extended Sensors version, Home Assistant version and Proxmox VE version when reporting a reproducible problem.

For cluster-specific issues, include the number of nodes and enough non-sensitive information about the cluster topology to understand the scenario.

Never include passwords or API Token secrets.
