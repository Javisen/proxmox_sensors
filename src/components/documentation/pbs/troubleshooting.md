PBS issues are easier to diagnose when the problem is first separated into connection, permissions, datastore information, backup information or maintenance actions.

Do not assume that missing server-level information means that the entire PBS connection has failed.

### The integration cannot connect to PBS

If the PBS connection cannot be created, verify:

- the PBS host;
- network connectivity from Home Assistant;
- the complete PBS user and realm;
- Token ID;
- Token Secret;
- certificate or SSL settings applicable to the connection.

PBS V5 authentication uses API Token credentials.

Remember that **User**, **Token ID** and **Token Secret** are separate values.

If the API Token has been recreated, update Home Assistant with the new secret.

### Authentication succeeds but information is missing

Successful authentication does not guarantee access to every PBS endpoint.

Check the permissions granted to the dedicated PBS account and API Token.

Monitoring and maintenance actions may require different levels of access.

If some datastore information works while particular actions or task information do not, permissions are one of the first things to check.

### Hosted PBS exposes limited information

Hosted or multi-tenant PBS providers can intentionally restrict access to server-level information.

You may have complete access to your datastore and backups without access to low-level server health or hardware information.

This does not automatically indicate an integration error.

Compare the missing information with what your provider actually exposes through its PBS API and account permissions.

### A datastore does not appear

Confirm that the datastore is visible to the configured PBS account.

If multiple PBS servers are configured, also confirm that you are inspecting the correct Home Assistant PBS connection.

A datastore belongs to the PBS server that exposes it; similarly named datastores on different servers should not be treated as the same resource.

### Datastore usage and backup state seem contradictory

Capacity information and backup health describe different things.

A datastore can have free space while a particular operation fails for another reason.

Likewise, all backups currently stored on PBS can be healthy even when a new PVE backup job has failed before completion.

Check the originating PVE task when diagnosing backup creation failures and use PBS information to understand the state of the backup server and the data actually stored there.

### Backup errors show zero after a failed PVE job

This can be expected.

PBS backup information describes the backups available to PBS.

If a PVE backup fails before a completed backup is stored, the existing PBS backups can remain valid and the PBS-side backup error information does not become a counter for the failed PVE job.

Check [PVE](../pve/) or [Cluster](../cluster/) task/backup monitoring for the originating job failure.

### A maintenance button does not work

If GC, Prune, Verify or Sync monitoring is visible but the corresponding action fails, verify the PBS permissions of the configured account and API Token.

For Prune, Verify and Sync, also confirm that the corresponding PBS job exists and is correctly configured.

These actions execute configured PBS operations; Home Assistant does not create the missing PBS job automatically.

### Sync is not available

Sync requires a corresponding PBS Sync Job.

If no Sync Job is available for the datastore or server configuration, there may be no Sync action for the integration to execute.

Configure and validate the Sync Job in PBS first.

### Prune or Verify is not available

Prune and Verify actions rely on the corresponding configured PBS jobs.

Confirm that the expected job exists in PBS and applies to the datastore you are monitoring.

The integration triggers the configured job rather than creating one on demand.

### Task information is unavailable

Task visibility depends on the information and permissions available through PBS.

If datastore monitoring works but task information is missing, verify that the configured account can access the required task information.

Hosted providers can also restrict operational information that would normally be available on a locally managed PBS server.

### Check Home Assistant logs

When the cause is not obvious, open:

**Settings → System → Logs**

Look for entries related to **Proxmox Extended Sensors** around the time the PBS problem occurred.

Permission errors, unavailable endpoints and connection failures can provide useful diagnostic information.

Remove API Token secrets, credentials and other sensitive information before sharing logs publicly.

### Before opening an issue

Try to identify whether the problem affects:

- the complete PBS connection;
- server health information;
- one datastore;
- backup information;
- a maintenance operation;
- task information;
- or a hosted-provider limitation.

Include the relevant Proxmox Extended Sensors version, Home Assistant version and PBS version when reporting a reproducible problem.

For hosted PBS, also mention that the service is provider-managed when that distinction is relevant.

Never include passwords or API Token secrets.
