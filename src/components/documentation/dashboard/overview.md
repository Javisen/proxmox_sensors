The Proxmox Extended Sensors dashboard provides an automatically generated Home Assistant interface for the resources monitored by the integration.

Its purpose is not simply to display entities.

The dashboard organizes the available Proxmox information into an operational view that remains synchronized with the integration and adapts as the monitored environment changes.

[PVE](../pve/) nodes, [PBS](../pbs/) servers, [clusters](../cluster/), storage resources, virtual machines, containers and supported features are presented only when they are relevant to the current configuration.

The result is a dashboard that can normally be installed and used without manually creating or maintaining a large collection of Home Assistant cards.

### Designed to prioritize useful information

Proxmox Extended Sensors can expose a large amount of information, but the automatic dashboard is intentionally not designed to display every available entity.

The sensors, cards and layout included in the dashboard have been selected and organized according to their operational relevance.

The goal is to provide enough information to understand the state of the Proxmox environment without overwhelming the interface with every metric exposed by the integration.

More important indicators are given greater visual relevance, while secondary information is grouped, reduced or omitted from the main view.

This creates a deliberate information hierarchy:

- important health and status information should be easy to identify;
- related values should be presented together so they can be interpreted in context;
- secondary metrics should not compete visually with conditions that may require attention;
- the number of visible sensors should remain manageable;
- information that is useful for detailed investigation does not necessarily need to occupy permanent dashboard space.

The automatic dashboard should therefore be treated as a curated operational view of Proxmox Extended Sensors, not as a complete entity catalogue.

If you need information that is not displayed in the automatic dashboard, the underlying entities remain available in Home Assistant and can be added to your own dashboards when required.

For the complete list of entities exposed by the integration, see [**Reference**](../reference/).

<figure class="pve-figure">
  <img src="../../images/documentation/dashboard/dashboard-1.png" width="1630" height="898" loading="lazy" decoding="async" alt="Complete automatic Proxmox Backup Server dashboard showing navigation, health, datastore, backup, maintenance, task and action areas." />
  <figcaption>Automatic Dashboard — Proxmox resources are organized into focused views that prioritize operational information without exposing every available entity at once.</figcaption>
</figure>

### One dashboard, different environments

The dashboard does not assume that every Proxmox Extended Sensors installation is identical.

A small installation monitoring a single PVE server should not need the same interface as a cluster containing multiple nodes, virtual machines, containers, storage resources and a Proxmox Backup Server.

The generated dashboard uses the resources available in the current Home Assistant installation to determine what should be shown.

This allows the same dashboard system to remain useful across installations of very different sizes.

### Automatic or manually controlled

There are two main ways to use the dashboard:

- **Automatic mode** — Proxmox Extended Sensors maintains the generated dashboard and adapts it to changes in the monitored environment.
- **Take Control** — Home Assistant converts the generated dashboard into a manually editable configuration controlled by the user.

Both approaches are valid, but they have an important difference.

Automatic mode prioritizes dynamic maintenance.

Take Control prioritizes manual customization.

The following sections explain [how to install the dashboard](#installation), [how its automatic behaviour works](#automatic-dashboard) and [what changes when you take control](#take-control).
