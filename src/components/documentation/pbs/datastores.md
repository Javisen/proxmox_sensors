Datastores are the central storage resources of Proxmox Backup Server.

Proxmox Extended Sensors exposes datastore information to Home Assistant so backup capacity and storage behaviour can be monitored without continuously opening the PBS interface.

### Capacity and usage

Datastore monitoring can provide information such as:

- total capacity;
- used space;
- free space;
- usage percentage.

These values provide a quick view of how much backup storage remains available.

Home Assistant can display them on a dashboard or use them as conditions for notifications and automations.

<figure class="pve-figure">
  <img src="../../images/documentation/pbs/pbs-3.png" width="506" height="344" loading="lazy" decoding="async" alt="PBS datastore view showing total, used and free capacity, usage and deduplication." />
  <figcaption>PBS datastore overview — capacity, usage and deduplication information for a monitored datastore.</figcaption>
</figure>

### Free space needs context

A datastore does not necessarily need to be almost full before its capacity becomes operationally important.

Backup size, retention policy, maintenance behaviour and expected future growth all affect how much free space is appropriate.

A datastore with significant free capacity can still deserve attention if the next backup cycle is expected to consume a large amount of space.

For this reason, storage trends are often more useful than a single percentage viewed in isolation.

### Deduplication

PBS can store duplicate data efficiently by reusing chunks that are already present.

Proxmox Extended Sensors can expose the deduplication information reported for a datastore.

A high deduplication factor can indicate that the stored backups share a significant amount of data, but it should not be interpreted as a health score.

Deduplication describes storage efficiency, not whether the backups themselves are valid.

### Datastore information and physical storage are different

The datastore information exposed to Home Assistant represents the PBS storage resource as reported by Proxmox Backup Server.

It does not necessarily describe the physical disks, filesystem, RAID or other storage infrastructure underneath that datastore.

This distinction is especially important with hosted PBS services, where the physical storage layer may not be visible to the customer at all.

### Multiple datastores

A PBS server can expose more than one datastore.

Proxmox Extended Sensors keeps datastore-specific information associated with the datastore it belongs to so capacity, backup state and maintenance information can be interpreted independently.

Different datastores can also require different monitoring thresholds depending on their size, retention policy and purpose.

For the complete list of PBS datastore entities, see [**Reference**](../reference/).
