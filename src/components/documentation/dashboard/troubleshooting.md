Dashboard problems should first be separated into two categories:

**Is Proxmox Extended Sensors providing the expected data?**

or:

**Is the dashboard failing to display data that already exists?**

This distinction usually makes troubleshooting much easier.

### The dashboard does not appear

Confirm that:

- Proxmox Extended Sensors is installed;
- Card Mod is installed;
- `/proxmox_sensors/proxmox-dashboard.js` has been added as a JavaScript Module;
- the browser has been reloaded after adding the resource.

If the **Proxmox Extended Sensors** option does not appear under Community dashboards, verify the frontend resource before troubleshooting the generated dashboard itself.

### The dashboard appears but is empty

Confirm that Proxmox Extended Sensors currently exposes the expected entities in Home Assistant.

Check:

**Settings → Devices & services → Proxmox Extended Sensors**

If the expected PVE, PBS or Cluster devices and entities exist but the dashboard remains empty, investigate the dashboard resource and frontend loading.

### A VM or CT does not appear

First confirm that the guest is selected for monitoring in Proxmox Extended Sensors and that its Home Assistant entities exist.

The automatic dashboard can only display guests that the integration exposes for detailed monitoring.

If the guest was recently added, refresh the dashboard after confirming that Home Assistant has created its entities.

### A removed VM or CT is still displayed

If the dashboard is still in automatic mode, first confirm that monitoring for the guest has actually been removed from Proxmox Extended Sensors.

Then refresh the dashboard.

If you previously used **Take Control**, the dashboard is no longer automatically maintained.

In that case, obsolete cards or sections must be removed manually.

### A migrated guest remains under the old node

First determine whether the dashboard is still automatic.

In automatic mode, a monitored guest that migrates within the configured cluster should be represented under its current node after the integration has refreshed the guest location.

If the integration already reports the new node but the automatic dashboard still shows the previous location, refresh the dashboard and investigate the frontend state.

If **Take Control** has been used, automatic movement between node sections is no longer expected.

The manually controlled dashboard must be updated by the user.

### Replication is not displayed

Replication information is conditional.

If no monitored VM or container currently exposes the replication information required by the dashboard, the replication section may not be displayed.

This is expected behaviour and prevents empty dashboard elements from remaining visible.

If replication should exist, verify the corresponding entities in Proxmox Extended Sensors before troubleshooting the dashboard.

### Some sensors are missing from the dashboard

This can be completely normal.

The automatic dashboard intentionally does not display every entity exposed by Proxmox Extended Sensors.

It presents a curated selection intended to prioritize useful operational information and avoid overcrowding.

Check [**Reference**](../reference/) if you want to confirm whether an entity exists in the integration.

If you want to display additional entities manually, use [**Take Control**](#take-control) and add them through the Home Assistant dashboard editor.

### The dashboard looks unchanged after an update

The browser or Home Assistant frontend may still be using cached JavaScript resources.

Refresh the Home Assistant frontend and perform a hard browser refresh if necessary.

Confirm that the installed dashboard files actually correspond to the version you intended to install.

Do not begin changing dashboard configuration simply to work around a stale frontend cache.

### Custom generator changes disappeared after an update

If you modified `frontend/proxmox-dashboard.js` directly, an update may replace the distributed file.

Direct modifications to the generator are advanced customizations and must be maintained by the user.

Review and reapply compatible changes against the new version rather than assuming they will be preserved automatically.

### Take Control no longer updates automatically

This is expected.

After Take Control, Home Assistant preserves the manually controlled dashboard configuration.

Automatic guest addition/removal, migration placement, conditional sections and future generator layout changes are no longer applied to that manually controlled version.

If automatic maintenance is more important than manual editing, use the generated automatic dashboard instead.

### Check the browser console

If entities exist correctly in Home Assistant but the dashboard does not load or behaves unexpectedly, browser developer tools may provide useful frontend errors.

Look for errors related to the Proxmox dashboard or its frontend resources.

Remove sensitive information before sharing console output publicly.

### Check Home Assistant logs

For problems that may involve the integration rather than only the frontend, open:

**Settings → System → Logs**

Look for entries related to **Proxmox Extended Sensors** around the time the problem occurred.

### Before opening an issue

Try to determine whether the problem affects:

- dashboard installation;
- frontend resource loading;
- automatic resource discovery;
- a particular PVE/PBS/Cluster view;
- VM or CT discovery;
- guest migration placement;
- conditional content such as replication;
- Take Control behaviour;
- or a custom modification to `proxmox-dashboard.js`.

Include:

- Proxmox Extended Sensors version;
- Home Assistant version;
- browser used;
- whether the dashboard is automatic or has used Take Control;
- enough non-sensitive information to reproduce the problem.

If `proxmox-dashboard.js` has been manually modified, mention that explicitly.

Never include passwords, API Token secrets or other credentials.
