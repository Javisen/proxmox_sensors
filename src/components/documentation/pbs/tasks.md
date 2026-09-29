PBS tasks provide operational context about work performed by the backup server.

They complement datastore and backup information by showing what PBS has recently been doing and whether those operations completed successfully.

### Last task

Proxmox Extended Sensors can expose information about the latest PBS task available to the integration.

Depending on the information returned by PBS, this can include:

- task type;
- task status;
- duration;
- result or message.

These values help explain recent activity without requiring the user to open the PBS task history for every routine operation.

<figure class="pve-figure">
  <img src="../../images/documentation/pbs/pbs-7.png" width="514" height="318" loading="lazy" decoding="async" alt="Last Task view showing PBS task type, status, duration and message." />
  <figcaption>Last Task — task type, status, duration and message provide context about recent PBS activity.</figcaption>
</figure>

### Task type

The task type identifies the kind of operation PBS performed.

This provides context for the result.

A successful Garbage Collection task and a successful Verify task both represent successful operations, but they describe completely different maintenance activity.

### Task status

Task status indicates the reported result of the PBS operation.

This can be useful for dashboards and particularly for notifications when a maintenance operation does not complete as expected.

A failed task should be interpreted together with its type and available message rather than as an isolated failure flag.

### Duration

Task duration can provide useful operational context.

Changes in duration do not automatically indicate a problem, but unusually long operations can be worth investigating when compared with the normal behaviour of the same type of task.

Datastore size, workload and the type of operation can all influence how long a PBS task takes.

### Last action

The integration can also retain information about the latest supported PBS action initiated through Proxmox Extended Sensors.

This helps associate Home Assistant-triggered maintenance activity with the datastore where the operation was requested.

It is useful for understanding what Home Assistant most recently asked PBS to do, while the PBS task information provides the server-side operational result.

### Tasks are not the same as PVE backup jobs

PBS task monitoring represents work performed or reported by PBS.

A backup job initiated by PVE belongs to a different operational context.

When diagnosing a failed backup, determine first whether the failure occurred in the PVE job, during communication or upload, or in a PBS-side operation.

This avoids drawing conclusions from the wrong task source.

For the complete list of PBS task entities, see [**Reference**](../reference/).
