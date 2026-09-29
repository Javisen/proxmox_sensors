Proxmox High Availability can protect selected workloads by coordinating their availability across cluster nodes.

When HA information is available, Proxmox Extended Sensors exposes a cluster-level view that can be used in Home Assistant.

### HA status

The cluster HA sensor provides a high-level indication of the HA environment.

When the required HA information is available and quorum is healthy, the cluster can report HA as active.

If the required information is unavailable or quorum is not healthy, the reported state can reflect that condition.

This makes HA status useful as part of the broader cluster-health picture.

### Quorum matters to HA

High Availability depends on the state of the cluster.

For that reason, HA status should not be interpreted independently from quorum.

If the cluster loses quorum, the HA environment cannot simply be treated as healthy because individual nodes remain reachable.

Display quorum and HA together when they are operationally important to your environment.

### Master and HA resources

Where Proxmox provides the information, HA monitoring can include additional context such as the current HA master and HA-managed resources.

This helps explain the state reported by the cluster without requiring Home Assistant to reproduce the complete Proxmox HA interface.

### HA is optional

Not every Proxmox cluster uses High Availability.

If HA is not configured in Proxmox, the absence of meaningful HA resource information does not indicate a problem with the integration.

Cluster monitoring remains useful for quorum, nodes, resources, workloads, tasks, replication and backups without HA.

### Home Assistant does not configure Proxmox HA

Proxmox Extended Sensors monitors the HA information exposed by Proxmox.

It does not replace the Proxmox HA configuration or decide which workloads should be HA-managed.

HA groups, resources, policies and operational decisions remain configured in Proxmox VE.

Home Assistant should be treated as an additional monitoring and automation layer around that environment.

For the complete list of HA-related Cluster entities, see [**Reference**](../reference/).
