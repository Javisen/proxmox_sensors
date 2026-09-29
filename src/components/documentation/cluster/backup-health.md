Cluster backup monitoring provides a PVE-side view of configured backup jobs and whether expected backups are being created successfully.

This complements [PBS monitoring](../pbs/), which focuses on the backup server and the backup data stored there.

### Backup Jobs

The Backup Jobs information summarizes the backup jobs configured in the Proxmox environment.

This allows Home Assistant to understand that backup schedules exist and provide a cluster-level view of their current operational state.

The exact information available depends on the backup jobs configured in Proxmox.

### Backup Age

A backup can exist and still be too old for the protection policy you expect.

Backup Age monitoring focuses on how long it has been since the relevant successful backup information was recorded.

This is often more useful than simply asking whether a backup exists.

A workload that normally receives a daily backup deserves attention if its most recent successful backup becomes several days old even though older backups remain available.

### Backup Health

Backup Health combines the available backup information into a higher-level operational view.

Its purpose is to make it easier to identify backup situations that require attention without relying on a single raw value.

It should still be interpreted together with Backup Jobs and Backup Age when diagnosing a problem.

<figure class="pve-figure">
  <img src="../../images/documentation/cluster/cluster-5.png" width="507" height="261" loading="lazy" decoding="async" alt="Backup Health showing Jobs in error, a recent Age and Health as warning." />
  <figcaption>Backup Health — job state, backup age and overall health describe different parts of the PVE-side backup situation and should be interpreted together.</figcaption>
</figure>

This example shows:

- Jobs → error
- a recent Backup Age;
- Health → warning.

### PVE and PBS remain complementary

Cluster Backup Health describes the PVE side of the backup workflow.

PBS monitoring describes the backup server, its datastores, stored backups, verification and maintenance operations.

These two views can legitimately report different states.

For example:

1. PBS contains healthy, previously verified backups.
2. A new scheduled PVE backup begins.
3. The upload or backup task fails before a valid new backup is completed.
4. Cluster backup monitoring can identify the failed or ageing PVE-side backup situation.
5. PBS can still report that the backups already stored in its datastore are healthy.

There is no contradiction.

The two systems are describing different stages of the backup process.

### Use age as an operational signal

Backup failures are not the only reason an expected recent backup may be missing.

A job may not have run, a workload may have been unavailable or another operational condition may have prevented the expected backup.

Monitoring age helps detect the outcome that matters:

**Is the latest successful backup still recent enough?**

This makes Backup Age particularly useful for Home Assistant notifications.

### Avoid relying on a single backup indicator

A robust backup overview can combine:

- configured Backup Jobs;
- Backup Age;
- Backup Health;
- failed cluster tasks;
- PBS datastore information;
- PBS verification status.

Each answers a different question.

Together they provide a much more complete view of the backup environment.

For the complete list of Cluster backup entities, see [**Reference**](../reference/).
