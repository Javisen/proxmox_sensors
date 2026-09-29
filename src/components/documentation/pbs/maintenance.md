Proxmox Backup Server requires maintenance operations to keep backup storage healthy and manageable.

Proxmox Extended Sensors can expose maintenance status and supported actions in Home Assistant, allowing PBS maintenance to become part of dashboards and automation workflows.

### Garbage Collection

Garbage Collection removes datastore chunks that are no longer required by referenced backups according to PBS behaviour.

Proxmox Extended Sensors can expose Garbage Collection information and provide a supported action to start GC for a datastore.

GC is not the same as deleting backups.

It operates on datastore data after backup retention and other PBS operations have determined which data is no longer referenced.

### Prune

Prune applies the retention policy defined by a configured PBS Prune Job.

When a Prune Job is available for the datastore, Proxmox Extended Sensors can expose its status and provide a supported action to run that configured job.

The integration does not invent a retention policy.

The retention rules belong to the PBS Prune Job configured on the server.

Home Assistant simply provides another way to trigger the supported operation.

### Verify

Verification checks stored backup data according to the configured PBS Verify Job.

When a Verify Job is configured, Proxmox Extended Sensors can expose verification status and provide a supported action to run that job.

Verification can be particularly useful as part of a scheduled backup-maintenance workflow because creating a backup and checking the integrity of stored backup data are separate concerns.

### Sync

When a PBS Sync Job exists, Proxmox Extended Sensors can expose a supported action to run it.

Sync operations are defined by PBS.

The integration triggers the configured job rather than creating or redefining its source, destination or synchronization policy.

<div class="pve-figure-pair">
  <figure class="pve-figure">
    <img src="../../images/documentation/pbs/pbs-5.png" width="509" height="332" loading="lazy" decoding="async" alt="PBS maintenance view showing GC, Prune and Verify status and the latest action." />
    <figcaption>Maintenance status — GC, Prune and Verify status together with the latest supported action recorded for the datastore.</figcaption>
  </figure>
  <figure class="pve-figure">
    <img src="../../images/documentation/pbs/pbs-6.png" width="508" height="349" loading="lazy" decoding="async" alt="PBS actions view with Garbage Collect, Prune, Verify and Sync controls." />
    <figcaption>Maintenance actions — supported Garbage Collect, Prune, Verify and Sync operations exposed in Home Assistant.</figcaption>
  </figure>
</div>

### Maintenance actions and permissions

Being able to monitor PBS does not automatically mean that the configured account can execute maintenance operations.

GC, Prune, Verify and Sync actions depend on the permissions granted to the PBS account and API Token.

If maintenance information is visible but an action fails, check permissions before assuming that the monitoring connection itself is broken.

### Automation workflows

PBS actions can be incorporated into Home Assistant automations.

For example, a workflow can trigger a configured maintenance operation according to your own schedule or conditions and then use PBS task or status information to monitor the result.

Automation should complement the PBS configuration rather than replace it.

Retention rules, Verify Jobs and Sync Jobs should remain defined in PBS, while Home Assistant can coordinate when supported operations are requested and how their results are surfaced.

Use maintenance actions deliberately, particularly on production backup storage.

For the complete list of supported PBS actions and maintenance entities, see [**Reference**](../reference/).
