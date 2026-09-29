PBS monitoring extends Proxmox Extended Sensors beyond the virtualization hosts and brings Proxmox Backup Server information into Home Assistant.

A PBS connection focuses on the backup environment: server health, datastore capacity, stored backups, deduplication, maintenance operations and task information.

It can be used alongside PVE monitoring or independently when Home Assistant only needs visibility into a Proxmox Backup Server.

### What PBS monitoring covers

A configured PBS connection can provide information from several areas:

- **Server health** — availability and supported CPU and memory information from the PBS server.
- [**Datastores**](#datastores) — capacity, used and free space, usage and deduplication information.
- [**Backups**](#backups) — information about the backups stored in each datastore, including summary and latest-backup information.
- [**Maintenance**](#maintenance) — status and supported actions for operations such as Garbage Collection, Prune and Verify.
- [**Tasks**](#tasks) — information about PBS operations and their results.
- **Sync** — supported execution of configured Sync Jobs when they are available.

The exact information available depends on the PBS server, API permissions and what the server or service provider exposes to the configured account.

### PBS and PVE provide different information

PVE and PBS represent different parts of the backup process.

PVE can know about the backup jobs and tasks that it executes.

PBS primarily provides information about the backup server, its datastores, stored backup data and PBS-side maintenance operations.

This distinction is important when interpreting backup information.

For example, a backup job can fail while sending data from PVE without creating a completed backup on PBS. The PBS datastore may still report that its existing stored backups are healthy.

Use the information from each system according to what it represents rather than expecting PVE and PBS to report the same view of a backup operation.

### Local and hosted PBS environments

PBS monitoring can be used with a locally managed Proxmox Backup Server or with a hosted service that provides compatible API access.

A locally managed server may expose server-level information that a hosted or multi-tenant service does not make available to individual customers.

Restricted server or hardware information on a hosted PBS does not necessarily indicate a problem with Proxmox Extended Sensors.

The integration can only expose information available through the account and API provided by the PBS service.

### Multiple PBS servers

Proxmox Extended Sensors V5 treats each configured PBS server as its own Home Assistant connection.

This allows multiple PBS instances to coexist while keeping their server, datastore and maintenance information associated with the correct PBS environment.

This is useful when an installation uses more than one backup destination, such as a local PBS together with an off-site or hosted PBS service.

### Home Assistant organization

PBS information is organized into Home Assistant devices and entities representing the server and its datastores.

This keeps datastore-specific information such as usage, backup state and maintenance operations grouped with the resource they belong to.

You do not need to display every PBS entity on a dashboard.

Use the information that helps answer useful operational questions: whether backup storage has enough capacity, whether stored backups are healthy, whether maintenance operations are completing and whether something requires attention.

### Where to continue

If this is your first PBS connection, continue with [**Authentication**](#authentication) and [**Configuration**](#configuration).

The remaining sections explain:

- [**Datastores**](#datastores)
- [**Backups**](#backups)
- [**Maintenance**](#maintenance)
- [**Tasks**](#tasks)
- [**Troubleshooting**](#troubleshooting)
