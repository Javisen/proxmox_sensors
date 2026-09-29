The Proxmox Extended Sensors dashboard is designed to remain synchronized with the integration automatically.

It does not create a fixed collection of cards that the user must maintain manually.

Instead, the dashboard builds its content from the Proxmox resources and entities currently available in Home Assistant.

### Adapts to your environment

The dashboard only displays information that is relevant to the current installation.

Sections and elements can appear or disappear automatically as the Proxmox environment and the integration configuration change.

For example, replication information is only displayed when replicated VMs or containers are available.

If no monitored workload uses replication, the corresponding dashboard content is not shown.

The same principle allows the dashboard to avoid presenting empty or irrelevant sections for functionality that is not available in the current environment.

This keeps the interface focused on the features that actually exist.

### Organized automatically

The dashboard also organizes the available information into views and sections corresponding to the monitored Proxmox resources.

The layout is generated from the resources currently available rather than requiring the user to build and maintain those views manually.

<figure class="pve-figure">
  <img src="../../images/documentation/dashboard/dashboard-4.png" width="1626" height="601" loading="lazy" decoding="async" alt="Automatic Proxmox VE dashboard view showing node health, temperatures and operational information." />
  <figcaption>Automatic PVE view — the dashboard organizes each monitored node and prioritizes relevant health, hardware and operational information while adapting to the resources available in the integration.</figcaption>
</figure>

The dashboard intentionally prioritizes useful operational information instead of placing every available sensor on screen.

### Add or remove monitored guests

When a VM or LXC container is added to Proxmox Extended Sensors monitoring, the dashboard can include it automatically.

If monitoring for that guest is later removed, its dashboard content disappears automatically as well.

There is no need to manually remove obsolete cards or repair references to entities that are no longer part of the monitored configuration.

The goal is to keep the dashboard clean and avoid leaving broken or irrelevant elements behind.

### Guest migration

The automatic dashboard also follows monitored VMs and containers when they migrate between nodes within the configured Proxmox cluster.

If a monitored guest moves from one node to another, the dashboard removes it from the source node and displays it under its current node automatically.

No dashboard editing is required after the migration.

This works together with the V5 guest identity model: the workload remains the same monitored guest while its current Proxmox node changes.

The dashboard therefore reflects the current topology without requiring the user to reorganize cards after normal cluster operations.

### Conditional information

Some dashboard information only makes sense when the corresponding feature or resource exists.

The automatic dashboard uses this context to avoid displaying empty sections.

Replication is one example.

If replication is present, the relevant information is displayed.

If it is not present, the dashboard does not reserve unnecessary space for it.

<figure class="pve-figure dashboard-comparison">
  <div class="dashboard-comparison__images">
    <div>
      <p class="dashboard-comparison__label">Replication available</p>
      <img src="../../images/documentation/dashboard/dashboard-6.png" width="1103" height="689" loading="lazy" decoding="async" alt="Historical automatic dashboard showing ZFS diagnostics and one replication job for CT 104 with status ok." />
    </div>
    <div>
      <p class="dashboard-comparison__label">Replication unavailable</p>
      <img src="../../images/documentation/dashboard/dashboard-7.png" width="1235" height="685" loading="lazy" decoding="async" alt="Automatic dashboard after replication and corresponding ZFS resources are absent, with no replication section displayed." />
    </div>
  </div>
  <figcaption>Conditional content — when replication is available, the automatic dashboard adds the corresponding section. When the feature is no longer present, the section is removed automatically without leaving broken or empty dashboard elements.</figcaption>
</figure>

The screenshots represent two different valid environment states, not a failure scenario.

The same dynamic principle helps remove other obsolete or unavailable information rather than leaving empty or broken dashboard elements.

### Automatic maintenance

As long as the dashboard remains in automatic mode, its structure can continue adapting to changes such as:

- adding monitored VMs or containers;
- removing monitored VMs or containers;
- migrating guests between cluster nodes;
- enabling or removing supported functionality;
- resources becoming available or no longer being relevant;
- changes introduced by future dashboard updates.

This means the dashboard normally requires very little manual maintenance.

The automatic behaviour is one of its main features.

### Automatic does not mean everything is displayed

The dashboard automatically reacts to the available integration data, but that does not mean every available entity is placed on screen.

The information hierarchy described in [**Overview**](#overview) still applies.

The generator determines which supported information belongs in the operational dashboard and how it should be organized.

Other entities remain available through Home Assistant and the [**Reference**](../reference/) documentation.
