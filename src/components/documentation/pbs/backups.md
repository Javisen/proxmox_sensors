PBS backup monitoring describes the backup data stored on the Proxmox Backup Server.

This is different from monitoring the PVE job that originally created and uploaded the backup.

Understanding that distinction makes PBS backup information much easier to interpret.

### Backup summary

Proxmox Extended Sensors can provide a summary of the backups stored in a datastore.

This gives Home Assistant a high-level view of the backup content currently available on PBS without requiring every stored snapshot to become an individual Home Assistant entity.

The summary is useful for understanding the overall state of the datastore while keeping the entity model manageable.

### Backup errors

Backup error information reflects problems detected in the backup information available from PBS.

It should not be interpreted as a universal counter for every failed PVE backup job.

A PVE backup task can fail before a valid backup reaches PBS.

In that situation, the existing backups stored on PBS can remain healthy even though the PVE job itself failed.

For PVE-side failed tasks and backup health information, use the appropriate [PVE](../pve/) or [Cluster](../cluster/) monitoring instead of treating the PBS datastore as the source of the original job result.

### Last backup

The integration can expose information about the latest backup available in a datastore, including supported information such as:

- time of the latest backup;
- backup size;
- backup status.

These values are useful together.

A recent timestamp tells you when the latest stored backup was created, while size and status provide additional context about that backup.

<figure class="pve-figure">
  <img src="../../images/documentation/pbs/pbs-4.png" width="510" height="340" loading="lazy" decoding="async" alt="PBS backup information showing stored backup count, errors, latest backup, size and verification status." />
  <figcaption>Backup information — stored backup count, reported errors, latest backup, size and verification status provide complementary context.</figcaption>
</figure>

### Verified backups

When PBS reports verification information, it can provide confidence that the stored backup data has passed the corresponding PBS verification process.

Verification and creation are different operations.

A backup being present does not by itself mean that it has been verified, and a successful verification does not mean that every future backup job will succeed.

Treat verification as information about stored backup integrity rather than as a prediction of future backup operations.

### Backup age matters

For many environments, the most important backup question is not simply whether backups exist, but whether a sufficiently recent backup exists.

A datastore containing many old backups can still represent a problem if the expected recent backup has not arrived.

Home Assistant can use latest-backup information to help surface situations where the stored backup history is becoming older than expected.

### Read backup information together

Backup count, latest backup time, size, status and verification information describe different parts of the same backup environment.

As with node monitoring, they are most useful when interpreted together rather than treating a single value as a complete health assessment.

For the complete list of PBS backup entities, see [**Reference**](../reference/).
