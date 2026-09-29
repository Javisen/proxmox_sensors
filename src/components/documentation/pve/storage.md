Proxmox Extended Sensors can expose information about the storage resources configured and available through Proxmox VE.

This provides Home Assistant with visibility into storage capacity, usage and availability without requiring the physical device behind the storage to be monitored directly.

### Proxmox storage

A PVE storage represents a storage resource configured in Proxmox VE.

Depending on the environment, this can include local storage as well as shared or remote storage used by the node.

The integration monitors the information that Proxmox exposes for these storage resources and represents it in Home Assistant.

This means that Storage monitoring focuses on the resource as PVE sees it rather than on the physical disk that may exist underneath it.

### Capacity and usage

Storage information can provide visibility into values such as total capacity, used space and available space.

These metrics are useful for dashboards and for identifying storage resources that are approaching the limits you consider appropriate for your environment.

Home Assistant can also use storage information in notifications or automations when a capacity threshold requires attention.

A storage reaching a high percentage of usage does not always require immediate action, but monitoring the trend can help prevent unexpected capacity problems.

<figure class="pve-figure">
  <img src="../../images/documentation/pve/pve-7.png" width="510" height="264" loading="lazy" decoding="async" alt="PVE Storage overview showing configured storage resources and usage." />
  <figcaption>PVE storage overview — configured storage resources can be monitored consistently regardless of their underlying type or location.</figcaption>
</figure>

### Local and remote storage

Not every PVE storage is a local physical disk.

A Proxmox environment may use storage backed by different technologies or remote systems.

From the integration's point of view, the important distinction is that PVE exposes the resource as storage that can be monitored.

This allows Home Assistant to provide a consistent view of storage usage even when the underlying storage technologies are different.

### Storage and hardware are different views

Storage monitoring and Hardware monitoring provide complementary information.

**Storage** describes the resource available to Proxmox:

- how much capacity it has;
- how much is being used;
- how much remains available;
- and its reported availability or state.

**Hardware** can provide information about the physical device itself when that information is available:

- temperature;
- SMART information;
- NVMe health data;
- and other supported hardware characteristics.

A storage resource can therefore be monitored even when Home Assistant has no direct hardware information about the device behind it.

Likewise, a physical disk detected by the hardware monitoring system does not necessarily correspond one-to-one with a PVE storage.

### Mounted disks

Proxmox Extended Sensors can also expose supported mounted disk information when it is available from the PVE host.

Mounted disks are useful when storage attached to the server needs visibility in Home Assistant even when it does not map directly to the same concepts used by Proxmox storage definitions.

This provides an additional view of storage resources without treating mounted filesystems as physical disk health sensors.

<figure class="pve-figure">
  <img src="../../images/documentation/pve/pve-8.png" width="405" height="178" loading="lazy" decoding="async" alt="Mounted Disks sensor showing supported mounted storage on the PVE host." />
  <figcaption>Mounted Disks — additional visibility into supported mounted storage detected on the PVE host.</figcaption>
</figure>

### Use storage information proactively

Storage monitoring is most useful before capacity becomes a problem.

Rather than checking storage only after an operation fails, Home Assistant can keep important capacity information visible or notify you when usage reaches a threshold appropriate for that resource.

Different storage resources may need different thresholds.

A small system volume, a large media store and a backup destination do not necessarily require the same amount of free space or the same monitoring strategy.

For the complete list of storage and mounted disk entities exposed by the integration, see [**Reference**](../reference/).

For physical drive temperatures and health information, see [**Hardware**](#hardware).
