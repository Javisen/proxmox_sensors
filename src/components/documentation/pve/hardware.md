Proxmox Extended Sensors can complement the information provided by the Proxmox API with hardware monitoring from the PVE host.

When supported by the system, this provides additional visibility into temperatures, storage devices and installed memory directly from Home Assistant.

Hardware monitoring is optional and the information available depends on the physical server, its sensors, installed drives and the data that the host can expose.

### Temperature monitoring

Supported systems can expose temperature information detected on the PVE host.

Depending on the hardware, this may include:

- CPU temperature;
- individual CPU core temperatures;
- chipset or motherboard-related temperatures;
- NVMe drive temperatures;
- other supported temperature sensors detected by the host.

The exact names and number of sensors can vary significantly between systems.

A compact mini PC, a workstation and a rack server may expose completely different hardware information even when all three run the same version of Proxmox VE.

<figure class="pve-figure">
  <img src="../../images/documentation/pve/pve-6.png" width="504" height="260" loading="lazy" decoding="async" alt="Hardware temperature sensors for CPU, chipset and NVMe devices on a PVE host." />
  <figcaption>Hardware temperatures — CPU, chipset and NVMe information available from the monitored PVE host.</figcaption>
</figure>

### lm-sensors

Linux hardware sensors detected through `lm-sensors` can provide additional temperature information to the integration.

Proxmox Extended Sensors does not create hardware measurements that the operating system cannot detect. If a temperature or hardware sensor is not available on the PVE host, the integration cannot expose it to Home Assistant.

This makes the host itself the first place to check when an expected hardware sensor is missing.

### SMART and storage health

Supported physical drives can expose SMART-related information that helps provide visibility into the underlying storage hardware.

This information complements the storage capacity and usage data provided elsewhere by the integration.

Storage monitoring answers questions such as **how much space is being used**, while hardware monitoring can provide information about **the physical device behind that storage**.

The exact SMART information available depends on the drive, controller and how the storage device is exposed to the operating system.

### NVMe devices

NVMe drives can provide device-specific information such as temperature and supported health data.

As with SMART monitoring, availability depends on whether the PVE host can access the required information from the device.

Controllers, passthrough configurations and other storage arrangements can affect what the host — and therefore the integration — can see.

### Memory information

When the required system information is available, Proxmox Extended Sensors can expose information about installed memory modules.

This can include the capacity of individual DIMM slots and other supported memory information detected on the host.

DIMM monitoring is useful for documenting the physical memory configuration of a node and can complement the overall RAM usage information available through Node monitoring.

### Hardware availability varies by host

Two PVE nodes configured identically in Home Assistant may expose different hardware entities.

This is expected.

Hardware monitoring depends on factors such as:

- motherboard and CPU sensor support;
- kernel and driver support;
- installed storage devices;
- storage controllers;
- available SMART or NVMe information;
- memory configuration;
- what the underlying operating system can detect.

For this reason, the absence of a particular hardware entity does not automatically indicate a problem with Proxmox Extended Sensors.

### Use hardware data as additional context

Hardware information is most useful when combined with the operational information from the rest of the integration.

For example, increased I/O activity together with an unusual storage temperature provides more context than either value alone.

Likewise, CPU usage and CPU temperature describe different aspects of the same workload.

Use the hardware entities that provide meaningful information for your equipment rather than expecting every possible sensor to be present.

For the complete list of supported hardware entities, see [**Reference**](../reference/).

If hardware information that should be available on the host does not appear in Home Assistant, see [**Troubleshooting**](#troubleshooting).
