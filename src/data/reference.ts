export type ReferenceEntityType = "Sensor" | "Binary sensor" | "Button";

export interface ReferenceEntity {
  name: string;
  type: ReferenceEntityType;
  description: string;
  unit?: string;
  state?: string;
  attributes?: string[];
  moreAttributes?: string[];
  condition?: string;
  dynamic?: boolean;
}

export interface ReferenceGroup {
  title: string;
  entries: ReferenceEntity[];
}

export interface ReferenceGuidanceItem {
  title: string;
  description: string;
  points?: string[];
  link?: { label: string; href: string };
}

export interface ReferenceGuidanceGroup {
  title: string;
  items: ReferenceGuidanceItem[];
}

// User-facing PVE node dictionary, based on the V5.1.0 audit:
// https://github.com/Javisen/test_javisen/blob/main/REFERENCE_INVENTORY.md
export const pveNodeGroups: ReferenceGroup[] = [
  {
    title: "Status & System",
    entries: [
      {
        name: "Node status / overview",
        type: "Sensor",
        state: "offline or health classification",
        description: "Overall node state, with a detailed overview and cluster association in its attributes.",
        attributes: ["Node overview", "Cluster association and scope"],
        condition: "Available when node-list monitoring is enabled.",
      },
      {
        name: "Sidecar Status",
        type: "Sensor",
        state: "ok / degraded / error / unknown",
        description: "Health of the sidecar endpoints used for extended node information.",
        attributes: ["Sensors endpoint", "SMART endpoint", "Memory endpoint", "Mounts endpoint"],
      },
      {
        name: "CPU Info",
        type: "Sensor",
        description: "CPU model reported by the node, with a core-count fallback.",
      },
      {
        name: "KSM Status",
        type: "Sensor",
        state: "Configured / Not configured / Unavailable",
        description: "Configuration and available activity details for Kernel Samepage Merging.",
        attributes: ["Activity", "ksm_run", "ksmtuned status", "Page counters"],
        moreAttributes: ["Full scans", "Saved-memory bytes", "Total RAM bytes"],
      },
      {
        name: "Updates",
        type: "Sensor",
        state: "Available update count",
        description: "Number of available updates; retrieval failures can expose an error or message.",
        attributes: ["Availability", "Package and version list"],
      },
      {
        name: "Uptime",
        type: "Sensor",
        description: "Node uptime returned in the PVE node data.",
      },
      {
        name: "Kernel Version",
        type: "Sensor",
        description: "Kernel version reported by the PVE node.",
      },
      {
        name: "PVE Version",
        type: "Sensor",
        description: "Proxmox VE version reported by the node.",
      },
      {
        name: "Additional Node Metrics",
        type: "Sensor",
        description: "Other node-data keys may create additional sensors. Their names and number depend on the data returned by the monitored node; they are not a fixed universal list.",
        dynamic: true,
      },
    ],
  },
  {
    title: "CPU & Memory",
    entries: [
      {
        name: "CPU Usage",
        type: "Sensor",
        unit: "%",
        description: "Current processor utilization of the PVE node.",
      },
      {
        name: "Memory Usage",
        type: "Sensor",
        unit: "%",
        description: "Current node memory utilization.",
      },
      {
        name: "Swap Usage",
        type: "Sensor",
        unit: "%",
        description: "Current node swap utilization.",
      },
      {
        name: "KSM Shared",
        type: "Sensor",
        unit: "GB",
        description: "Memory saved or shared through Kernel Samepage Merging.",
        condition: "Available when the node reports KSM data.",
      },
    ],
  },
  {
    title: "Performance & Network",
    entries: [
      {
        name: "I/O Wait",
        type: "Sensor",
        unit: "%",
        description: "Time the node spends waiting on I/O, with diagnostic details.",
        attributes: ["I/O-wait diagnostics"],
      },
      {
        name: "Load Average 1m",
        type: "Sensor",
        description: "One-minute node load average.",
        attributes: ["Additional load information"],
      },
      {
        name: "Node Score",
        type: "Sensor",
        description: "Calculated performance and pressure score; lower is better.",
        attributes: ["Interpretation", "Classified state"],
      },
      {
        name: "Network RX",
        type: "Sensor",
        unit: "kB/s",
        description: "Receive rate calculated from monitored VM and CT network counters.",
        attributes: ["Total bytes", "Per-guest usage", "Top guests", "Top-guest percentages"],
      },
      {
        name: "Network TX",
        type: "Sensor",
        unit: "kB/s",
        description: "Transmit rate calculated from monitored VM and CT network counters.",
        attributes: ["Total bytes", "Per-guest usage", "Top guests", "Top-guest percentages"],
      },
    ],
  },
  {
    title: "Storage & Tasks",
    entries: [
      {
        name: "RootFS Usage",
        type: "Sensor",
        unit: "%",
        description: "Utilization of the node root filesystem.",
      },
      {
        name: "Storages",
        type: "Sensor",
        state: "Available storage count",
        description: "Number of available storages for the node.",
        attributes: ["Storage summary"],
        condition: "Available when storage-list monitoring is enabled.",
      },
      {
        name: "Backup Progress",
        type: "Sensor",
        state: "idle / running / error / ok",
        description: "Progress and results of PVE backup tasks from the last 24 hours.",
        attributes: ["Task counts", "Percentage", "Current task", "Recent backups"],
        condition: "Available when backup-progress monitoring is enabled.",
      },
      {
        name: "Last Task",
        type: "Sensor",
        description: "Latest node task summary.",
        attributes: ["Task details", "Node task history"],
      },
    ],
  },
  {
    title: "Health",
    entries: [
      {
        name: "Node Overloaded",
        type: "Binary sensor",
        state: "On / Off",
        description: "On when CPU exceeds 85%, RAM exceeds 90%, or active tasks exceed five.",
        attributes: ["CPU %", "Memory %", "Active tasks", "Reason"],
      },
      {
        name: "Disk Overloaded",
        type: "Binary sensor",
        state: "On / Off",
        description: "Problem signal that turns on when I/O wait exceeds 10%.",
        attributes: ["I/O wait %", "Threshold", "Status"],
      },
      {
        name: "Node Stressed",
        type: "Binary sensor",
        state: "On / Off",
        description: "On when CPU exceeds 85%, I/O wait exceeds 10%, or one-minute load exceeds the node core count.",
        attributes: ["CPU", "I/O wait", "Load 1m", "Cores", "Load ratio"],
      },
    ],
  },
  {
    title: "Actions",
    entries: [
      {
        name: "Reboot Node",
        type: "Button",
        description: "Reboots the PVE node.",
        condition: "Available when node controls are enabled.",
      },
      {
        name: "Shutdown Node",
        type: "Button",
        description: "Shuts down the PVE node.",
        condition: "Available when node controls are enabled.",
      },
      {
        name: "Wake Node",
        type: "Button",
        description: "Sends a Wake-on-LAN request for the node.",
        condition: "Available when a Wake-on-LAN MAC is configured for the node.",
      },
    ],
  },
];

export const pveNodeEntryCount = pveNodeGroups.reduce((count, group) => count + group.entries.length, 0);

export const hardwareMemoryGroups: ReferenceGroup[] = [
  {
    title: "Temperatures",
    entries: [
      {
        name: "CPU Temperature",
        type: "Sensor",
        unit: "°C",
        description: "Grouped CPU temperature using package, Tctl or Tdie data when available, with an averaged-core fallback and support for ARM cpu_thermal data.",
        attributes: ["Package temperature", "Per-core and TCCD temperatures"],
        moreAttributes: ["Critical CPU temperature", "Thermal margin"],
        condition: "Available when hardware monitoring is enabled and compatible sidecar or lm-sensors data is detected.",
      },
      {
        name: "Chipset Temperature",
        type: "Sensor",
        unit: "°C",
        description: "Primary PCH or chipset temperature detected on the monitored node.",
        attributes: ["Average ACPI temperature when available"],
        condition: "Available when hardware monitoring is enabled and a compatible chipset sensor is detected.",
      },
      {
        name: "NVMe Temperature",
        type: "Sensor",
        unit: "°C",
        description: "Temperature for a detected NVMe device, using lm-sensors data with SMART temperature fallback when available.",
        attributes: ["NVMe temperature channels and labels", "SMART-derived information"],
        condition: "Available when hardware monitoring is enabled and an NVMe device is detected.",
        dynamic: true,
      },
      {
        name: "Other Hardware Temperatures",
        type: "Sensor",
        unit: "°C",
        description: "Additional compatible temperature channels reported by lm-sensors. Adapter and PWM entries are skipped, and ACPI-only blocks are not exposed as standalone sensors.",
        condition: "Available when hardware monitoring is enabled and compatible temperature data exists.",
        dynamic: true,
      },
    ],
  },
  {
    title: "Fans & Voltages",
    entries: [
      {
        name: "Fan Sensors",
        type: "Sensor",
        unit: "RPM",
        description: "Fan-speed sensors created from detected fan input channels. Exact names and quantity depend on the monitored hardware.",
        condition: "Available when hardware monitoring is enabled and fan input data is detected.",
        dynamic: true,
      },
      {
        name: "Voltage Sensors",
        type: "Sensor",
        unit: "V",
        description: "Voltage sensors created from detected voltage input channels. Exact names and quantity depend on the monitored hardware.",
        condition: "Available when hardware monitoring is enabled and voltage input data is detected.",
        dynamic: true,
      },
    ],
  },
  {
    title: "Physical Memory",
    entries: [
      {
        name: "DIMM Capacity",
        type: "Sensor",
        unit: "GB",
        description: "Capacity of a detected physical memory module. One entity is created per DIMM returned by the sidecar inventory.",
        attributes: ["speed", "configured_speed", "type", "manufacturer", "locator"],
        condition: "Available for DIMMs detected in the physical memory inventory.",
        dynamic: true,
      },
    ],
  },
];

export const vmGroups: ReferenceGroup[] = [
  {
    title: "Virtual Machine Sensors",
    entries: [
      {
        name: "VM Status",
        type: "Sensor",
        state: "VM state",
        description: "Current state of a monitored QEMU virtual machine.",
        attributes: ["current node", "onboot", "expected state", "actual state matches onboot"],
        moreAttributes: ["replication_status", "replication_jobs", "replication_failed_jobs", "replication details when applicable"],
      },
      {
        name: "VM CPU Usage",
        type: "Sensor",
        unit: "%",
        description: "Current processor utilization of the virtual machine.",
        attributes: ["core count", "CPU per core when available"],
      },
      {
        name: "VM Memory Used",
        type: "Sensor",
        unit: "GB",
        description: "Memory currently used by the virtual machine.",
        attributes: ["usage_percent"],
      },
      {
        name: "VM Memory Total",
        type: "Sensor",
        unit: "GB",
        description: "Total memory assigned to the virtual machine.",
      },
      {
        name: "VM Disk Total",
        type: "Sensor",
        unit: "GB",
        description: "Total disk capacity reported for the virtual machine.",
      },
      {
        name: "VM Uptime",
        type: "Sensor",
        unit: "h",
        description: "Current virtual-machine uptime in hours.",
      },
      {
        name: "VM Network RX",
        type: "Sensor",
        unit: "GB",
        description: "Cumulative network data received by the virtual machine.",
      },
      {
        name: "VM Network TX",
        type: "Sensor",
        unit: "GB",
        description: "Cumulative network data transmitted by the virtual machine.",
      },
    ],
  },
  {
    title: "Virtual Machine Actions",
    entries: [
      { name: "Start VM", type: "Button", description: "Starts the virtual machine.", condition: "Available when VM controls and the corresponding feature are enabled." },
      { name: "Shutdown VM", type: "Button", description: "Requests a virtual-machine shutdown.", condition: "Available when VM controls and the corresponding feature are enabled." },
      { name: "Stop VM", type: "Button", description: "Stops the virtual machine.", condition: "Available when VM controls and the corresponding feature are enabled." },
      { name: "Reboot VM", type: "Button", description: "Reboots the virtual machine.", condition: "Available when VM controls and the corresponding feature are enabled." },
      { name: "Reset VM", type: "Button", description: "Resets the virtual machine.", condition: "Available when VM controls and the corresponding feature are enabled." },
      { name: "Pause VM", type: "Button", description: "Pauses the virtual machine.", condition: "Available when VM controls and the corresponding feature are enabled." },
      { name: "Hibernate VM", type: "Button", description: "Hibernates the virtual machine.", condition: "Available when VM controls and the corresponding feature are enabled." },
      { name: "Resume VM", type: "Button", description: "Resumes the virtual machine.", condition: "Available when VM controls and the corresponding feature are enabled." },
    ],
  },
];

export const ctGroups: ReferenceGroup[] = [
  {
    title: "Container Sensors",
    entries: [
      {
        name: "Container Status",
        type: "Sensor",
        state: "Container state",
        description: "Current state of a monitored LXC container.",
        attributes: ["current node", "onboot", "expected state", "actual state matches onboot"],
        moreAttributes: ["replication_status", "replication_jobs", "replication_failed_jobs", "replication details when applicable"],
      },
      {
        name: "Container CPU Usage",
        type: "Sensor",
        unit: "%",
        description: "Current processor utilization of the container.",
        attributes: ["core count", "CPU per core when available"],
      },
      {
        name: "Container Memory Used",
        type: "Sensor",
        unit: "GB",
        description: "Memory currently used by the container.",
        attributes: ["usage_percent"],
      },
      {
        name: "Container Memory Total",
        type: "Sensor",
        unit: "GB",
        description: "Total memory assigned to the container.",
      },
      {
        name: "Container Disk Total",
        type: "Sensor",
        unit: "GB",
        description: "Total disk capacity reported for the container.",
      },
      {
        name: "Container Disk Used",
        type: "Sensor",
        unit: "GB",
        description: "Disk capacity currently used by the container.",
        attributes: ["usage_percent"],
      },
      {
        name: "Container Uptime",
        type: "Sensor",
        unit: "h",
        description: "Current container uptime in hours.",
      },
      {
        name: "Container Network RX",
        type: "Sensor",
        unit: "GB",
        description: "Cumulative network data received by the container.",
      },
      {
        name: "Container Network TX",
        type: "Sensor",
        unit: "GB",
        description: "Cumulative network data transmitted by the container.",
      },
    ],
  },
  {
    title: "Container Actions",
    entries: [
      { name: "Start Container", type: "Button", description: "Starts the container.", condition: "Available when CT controls and the corresponding feature are enabled." },
      { name: "Shutdown Container", type: "Button", description: "Requests a container shutdown.", condition: "Available when CT controls and the corresponding feature are enabled." },
      { name: "Stop Container", type: "Button", description: "Stops the container.", condition: "Available when CT controls and the corresponding feature are enabled." },
      { name: "Reboot Container", type: "Button", description: "Reboots the container.", condition: "Available when CT controls and the corresponding feature are enabled." },
    ],
  },
];

export const storageDisksZfsGroups: ReferenceGroup[] = [
  {
    title: "PVE Storage",
    entries: [
      { name: "Storage Usage", type: "Sensor", unit: "%", description: "Utilization of a selected and applicable PVE storage resource.", condition: "Available for storage resources discovered for the node and included in selected_storage.", dynamic: true },
      { name: "Storage Used Space", type: "Sensor", unit: "GB", description: "Space currently used on a selected PVE storage resource.", condition: "Available for storage resources discovered for the node and included in selected_storage.", dynamic: true },
      { name: "Storage Free Space", type: "Sensor", unit: "GB", description: "Space currently available on a selected PVE storage resource.", condition: "Available for storage resources discovered for the node and included in selected_storage.", dynamic: true },
      { name: "Storage Total Capacity", type: "Sensor", unit: "GB", description: "Total capacity of a selected PVE storage resource.", condition: "Available for storage resources discovered for the node and included in selected_storage.", dynamic: true },
      { name: "Storage Type", type: "Sensor", state: "Storage type", description: "Storage type reported for a selected PVE storage resource.", condition: "Available for storage resources discovered for the node and included in selected_storage.", dynamic: true },
    ],
  },
  {
    title: "Physical Disks",
    entries: [
      {
        name: "Disk Size",
        type: "Sensor",
        unit: "GB",
        description: "Capacity of a detected non-boot physical disk. SMART details vary by disk type and the smartctl data available.",
        attributes: ["model", "serial", "type", "raw capacity", "firmware", "SMART availability and health", "temperature", "power-on hours", "derived age"],
        moreAttributes: ["reallocated sectors", "pending sectors", "uncorrectable sectors", "NVMe media errors", "spin retry count", "seek error rate", "SMART return code", "available spare", "spare threshold", "percentage used", "data units read and written", "TB read and written", "host read and write commands", "controller busy time", "error log entries", "warning temperature time", "critical temperature time", "critical warning", "Health Score", "Disk Health"],
        condition: "Available when physical-disk monitoring is enabled and a supported non-boot disk is detected; SMART attributes require corresponding SMART data.",
        dynamic: true,
      },
    ],
  },
  {
    title: "Mounted Disks",
    entries: [
      {
        name: "Mounted Disks",
        type: "Sensor",
        state: "Mounted disk count",
        description: "Summary of currently mounted, unmounted and missing local or network mounts.",
        attributes: ["mounted_disks", "unmounted_disks", "total_disks", "mounted_count", "missing_mounts"],
        moreAttributes: ["all_mounted", "mount_points", "mount_points_count", "network_mounts", "local_mounts"],
      },
    ],
  },
  {
    title: "ZFS",
    entries: [
      {
        name: "ZFS Pool Health",
        type: "Sensor",
        state: "ONLINE / DEGRADED / FAULTED / OFFLINE / unknown",
        description: "Current health of a detected ZFS pool.",
        attributes: ["pool", "node", "health", "size GB", "used GB", "free GB", "fragmentation", "deduplication"],
        condition: "Available only when ZFS pool data is detected.",
        dynamic: true,
      },
    ],
  },
];

export const pbsServerDatastoreGroups: ReferenceGroup[] = [
  {
    title: "PBS Server",
    entries: [
      { name: "PBS Version", type: "Sensor", description: "Proxmox Backup Server version reported by the server." },
      { name: "PBS Release", type: "Sensor", description: "Proxmox Backup Server release reported by the server." },
      { name: "PBS Auth Status", type: "Sensor", state: "Authentication status", description: "Current authentication status for the PBS connection." },
      { name: "PBS CPU Usage", type: "Sensor", unit: "%", description: "Current PBS processor utilization.", attributes: ["cores", "CPU model", "load average 1m", "load average 5m", "load average 15m"], condition: "Node-status data can be unavailable when the optional capability is not supported." },
      { name: "PBS RAM Usage", type: "Sensor", unit: "%", description: "Current PBS memory utilization.", attributes: ["total GB", "used GB", "free GB"] },
      { name: "PBS RAM Total", type: "Sensor", unit: "GB", description: "Total memory reported by the PBS server." },
      { name: "PBS RAM Used", type: "Sensor", unit: "GB", description: "Memory currently used by the PBS server." },
      { name: "PBS RAM Free", type: "Sensor", unit: "GB", description: "Memory currently available on the PBS server." },
    ],
  },
  {
    title: "PBS Tasks",
    entries: [
      { name: "PBS Last Task", type: "Sensor", state: "worker type: status", description: "Summary of the latest PBS task." },
      { name: "PBS Last Task Type", type: "Sensor", description: "Worker type of the latest PBS task." },
      { name: "PBS Last Task Status", type: "Sensor", state: "Task status", description: "Result or current status of the latest PBS task.", attributes: ["task type", "worker or vmid", "node", "UPID", "start time", "end time"] },
      { name: "PBS Last Task Message", type: "Sensor", description: "Latest task message or status text." },
      { name: "PBS Last Task Duration", type: "Sensor", unit: "s", description: "Duration of the latest task; running duration is calculated when no end time exists." },
    ],
  },
  {
    title: "PBS Datastore",
    entries: [
      { name: "Datastore Usage", type: "Sensor", unit: "%", description: "Current utilization of a discovered PBS datastore.", condition: "Created for each discovered PBS datastore.", dynamic: true },
      { name: "Datastore Total", type: "Sensor", unit: "GB", description: "Total datastore capacity.", condition: "Created for each discovered PBS datastore.", dynamic: true },
      { name: "Datastore Used", type: "Sensor", unit: "GB", description: "Datastore capacity currently used.", condition: "Created for each discovered PBS datastore.", dynamic: true },
      { name: "Datastore Free", type: "Sensor", unit: "GB", description: "Datastore capacity currently available.", condition: "Created for each discovered PBS datastore.", dynamic: true },
      { name: "Datastore Dedup", type: "Sensor", unit: "x", description: "Deduplication ratio reported for the datastore.", condition: "Created for each discovered PBS datastore.", dynamic: true },
      { name: "Datastore Last Backup", type: "Sensor", state: "Local date and time", description: "Timestamp of the latest backup stored in the datastore.", condition: "Created for each discovered PBS datastore.", dynamic: true },
      { name: "Datastore Last Size", type: "Sensor", unit: "GB", description: "Size of the latest stored backup.", condition: "Created for each discovered PBS datastore.", dynamic: true },
      { name: "Datastore Last Backup Status", type: "Sensor", state: "Verified OK / Verification Failed / Finished (Not Verified) / No backups", description: "Verification-aware status of the latest datastore backup.", condition: "Created for each discovered PBS datastore.", dynamic: true },
      { name: "Datastore Backup Errors", type: "Sensor", state: "Error count", description: "Number of backup errors associated with the datastore.", condition: "Created for each discovered PBS datastore.", dynamic: true },
      { name: "Datastore Backups Summary", type: "Sensor", state: "Snapshot count", description: "Summary of the backup snapshots stored in the datastore.", attributes: ["latest backup per resource", "total snapshots", "datastore name"], condition: "Created for each discovered PBS datastore.", dynamic: true },
    ],
  },
];

export const pbsMaintenanceGroups: ReferenceGroup[] = [
  {
    title: "Maintenance Status",
    entries: [
      { name: "GC Status", type: "Sensor", state: "Iniciado / Running / OK / Error", description: "Current or latest Garbage Collection execution for a PBS datastore.", attributes: ["UPID", "task timing", "status", "duration"], moreAttributes: ["byte and chunk counters", "removed and pending sizes", "Garbage Collection statistics"], condition: "Created for each discovered PBS datastore.", dynamic: true },
      { name: "Verify Status", type: "Sensor", state: "Task status", description: "Current or latest Verify execution for a PBS datastore.", attributes: ["UPID", "status", "start and end timing", "duration"], condition: "Created for each discovered PBS datastore.", dynamic: true },
      { name: "Prune Status", type: "Sensor", state: "Task status", description: "Current or latest Prune execution for a PBS datastore.", attributes: ["UPID", "status", "start and end timing", "duration"], condition: "Created for each discovered PBS datastore.", dynamic: true },
      { name: "Last Action", type: "Sensor", state: "Latest maintenance action", description: "Most recent Garbage Collection, Prune, Verify or Sync action matched to the datastore when possible.", attributes: ["task type", "status", "start and end timing", "duration"], moreAttributes: ["error", "message", "exit status", "raw task type"], condition: "Created for each discovered PBS datastore.", dynamic: true },
    ],
  },
  {
    title: "Datastore Actions",
    entries: [
      { name: "Garbage Collect", type: "Button", description: "Starts Garbage Collection for the datastore.", condition: "Created for each discovered PBS datastore.", dynamic: true },
      { name: "Prune", type: "Button", description: "Starts the matched Prune operation for the datastore.", condition: "Availability and behaviour can depend on a configured and matched datastore job.", dynamic: true },
      { name: "Verify", type: "Button", description: "Starts the matched Verify operation for the datastore.", condition: "Availability and behaviour can depend on a configured and matched datastore job.", dynamic: true },
      { name: "Sync", type: "Button", description: "Starts the matched Sync operation for the datastore.", condition: "Availability and behaviour can depend on a configured and matched datastore job.", dynamic: true },
    ],
  },
  {
    title: "PBS Node Actions",
    entries: [
      { name: "Shutdown PBS", type: "Button", description: "Requests shutdown of the PBS server.", condition: "Available when PBS node controls are enabled." },
      { name: "Reboot PBS", type: "Button", description: "Reboots the PBS server.", condition: "Available when PBS node controls are enabled." },
      { name: "Wake PBS", type: "Button", description: "Sends a Wake-on-LAN request for the PBS server.", condition: "Available when a PBS Wake-on-LAN MAC is configured." },
    ],
  },
];

export const clusterSensorGroups: ReferenceGroup[] = [
  {
    title: "Cluster Status",
    entries: [
      { name: "Cluster Status", type: "Sensor", state: "quorate / no quorum", description: "Overall Proxmox VE cluster quorum state.", attributes: ["cluster name", "version", "quorum", "total nodes", "online nodes", "offline nodes", "node list"] },
      { name: "Nodes Online", type: "Sensor", unit: "nodes", description: "Number of cluster nodes currently online.", attributes: ["total", "online", "offline", "online-node list", "offline-node list"] },
      { name: "Cluster CPU Usage", type: "Sensor", unit: "%", description: "Aggregate cluster CPU utilization weighted by node core count.", attributes: ["total cores", "per-node CPU percentages"] },
      { name: "Cluster RAM Usage", type: "Sensor", unit: "%", description: "Aggregate cluster memory utilization.", attributes: ["total GB", "used GB", "per-node total and used GB"] },
      { name: "VMs Running", type: "Sensor", unit: "VMs", description: "Number of virtual machines currently running across the cluster.", attributes: ["total", "running", "stopped", "other", "running VM list with name, node and vmid"] },
      { name: "CTs Running", type: "Sensor", unit: "CTs", description: "Number of containers currently running across the cluster.", attributes: ["total", "running", "stopped", "running CT list with name, node and vmid"] },
      { name: "Cluster Storage Usage", type: "Sensor", unit: "%", description: "Aggregate utilization across cluster storage resources.", attributes: ["total used GB", "total GB", "per-storage details"] },
      { name: "Cluster Firewall", type: "Sensor", state: "Enabled / Disabled / Unknown", description: "Current cluster firewall state.", attributes: ["raw enable value", "firewall options"] },
      { name: "HA Status", type: "Sensor", state: "active / inactive / unavailable", description: "Current high-availability status for the cluster.", attributes: ["availability and quorum", "master node", "timestamp"], condition: "Available only when cluster HA data exists." },
    ],
  },
];

export const backupReplicationGroups: ReferenceGroup[] = [
  {
    title: "Cluster Backup Monitoring",
    entries: [
      { name: "Backup Jobs", type: "Sensor", state: "ok / error / unknown", description: "Overall state of known cluster backup jobs.", attributes: ["total jobs"] },
      { name: "Backup Age", type: "Sensor", unit: "h", description: "Hours since the latest cluster backup task.", attributes: ["age", "last backup timestamp", "status", "total jobs"] },
      { name: "Backup Health", type: "Sensor", state: "healthy / warning / critical / unknown", description: "Cluster backup health classification based on backup age and state.", attributes: ["last backup", "total jobs"] },
      { name: "Failed Tasks", type: "Sensor", state: "Failed task count", description: "Count of failed or non-OK cluster tasks within the last 24 hours.", attributes: ["failed count", "latest failure timestamp", "node", "task type", "task details"] },
    ],
  },
  {
    title: "Replication Summary",
    entries: [
      { name: "Replication Jobs", type: "Sensor", state: "Job count", description: "Number of known replication jobs.", attributes: ["job list", "inventory freshness", "runtime freshness", "runtime-unknown job count"], condition: "Available when applicable replication inventory or jobs exist.", dynamic: true },
      { name: "Replication Status", type: "Sensor", state: "ok / error count / unknown", description: "Overall replication state derived from job runtime and inventory data.", attributes: ["failed-job list", "inventory freshness", "runtime freshness", "runtime-unknown job count"], condition: "Available when applicable replication inventory or jobs exist.", dynamic: true },
    ],
  },
  {
    title: "Per-job Replication Sensors",
    entries: [
      { name: "Replication Last Sync", type: "Sensor", state: "Timestamp", description: "Time of the latest synchronization for an active replication job; attached to the corresponding VM or CT device.", attributes: ["current replication job record"], condition: "Created for applicable active replication jobs.", dynamic: true },
      { name: "Replication Next Sync", type: "Sensor", state: "Timestamp", description: "Scheduled time of the next synchronization for an active replication job; attached to the corresponding VM or CT device.", attributes: ["current replication job record"], condition: "Created for applicable active replication jobs.", dynamic: true },
      { name: "Replication Duration", type: "Sensor", unit: "s", description: "Duration of the active replication job's latest synchronization; attached to the corresponding VM or CT device.", attributes: ["current replication job record"], condition: "Created for applicable active replication jobs.", dynamic: true },
    ],
  },
];

export const identityAvailabilityGroups: ReferenceGuidanceGroup[] = [
  {
    title: "Entity & Device Identity",
    items: [
      { title: "PVE-local resources", description: "Node, storage, mounted-disk and similar resources use identities associated with the relevant PVE environment." },
      { title: "VM & CT migration identity", description: "When a PVE entry participates in an active cluster scope, monitored VM and CT identity is cluster-scoped. A guest can migrate between cluster nodes while retaining its Home Assistant identity.", points: ["Preserves entity identity and configuration", "Maintains history and statistics relationships", "Keeps dashboard and automation references stable"] },
      { title: "PBS server identity", description: "PBS datastore and maintenance identities are server-scoped, so same-named datastores on different PBS servers remain distinct." },
      { title: "Replication identity", description: "Replication measurements use stable job-based identity and attach to the existing VM or CT device." },
    ],
  },
  {
    title: "Conditional Availability",
    items: [
      {
        title: "Why don't I have this entity?",
        description: "Many entity families appear only when their feature, resource and source data are available.",
        points: [
          "PVE hardware — hardware monitoring enabled and compatible sidecar or lm-sensors data detected",
          "DIMMs — returned by the sidecar physical-memory inventory",
          "Physical disks — physical-disk monitoring enabled; SMART details additionally require SMART data",
          "Storage — discovered, applicable and selected storage resources only",
          "VM & CT — effectively selected monitored guests only",
          "ZFS — detected pools present in zfs_pools",
          "PVE node controls — node controls enabled; Wake additionally requires a MAC",
          "PVE backup progress — backup-progress monitoring enabled",
          "Cluster HA — HA data available",
          "Replication — applicable replication inventory and jobs available",
          "PBS datastore and maintenance — created per discovered datastore",
          "PBS Wake — a Wake-on-LAN MAC configured",
          "PBS Shutdown and Reboot — PBS node controls enabled",
        ],
      },
    ],
  },
];

export const troubleshootingGroups: ReferenceGuidanceGroup[] = [
  {
    title: "Finding & Understanding Entities",
    items: [
      { title: "I cannot find an entity", description: "Confirm that the related integration resource or device is configured, the feature is enabled, and the entity is not conditional on unavailable data. Also check that the VM, CT, storage or datastore is selected or discovered as required." },
      { title: "Hardware entity missing", description: "Hardware sensors depend on environment-specific sidecar and lm-sensors data. Exact temperature, fan and voltage entities vary by machine.", link: { label: "Review PVE hardware guidance", href: "/docs/pve/#hardware" } },
      { title: "SMART attributes missing", description: "SMART attributes vary by disk and device type and by the smartctl data available. No physical disk is expected to expose every documented SMART attribute." },
      { title: "ZFS entity missing", description: "ZFS entities exist only when relevant ZFS pool data is detected." },
      { title: "VM or CT missing", description: "Confirm that the guest is selected or effectively selected for monitoring.", link: { label: "Review VM & CT monitoring", href: "/docs/pve/#vm-ct-monitoring" } },
      { title: "Replication entity missing", description: "Replication entities are conditional and exist only when applicable replication jobs and data are available.", link: { label: "Review Cluster diagnostics", href: "/docs/cluster/#tasks-diagnostics" } },
      { title: "PBS entity missing", description: "Identify whether the expected entity belongs to the PBS server, task, datastore or maintenance family, then verify the corresponding server capability and datastore discovery.", link: { label: "Review PBS troubleshooting", href: "/docs/pbs/#troubleshooting" } },
      { title: "Entity is absent from the automatic Dashboard", description: "Reference documents entities exposed by the integration. The automatic Dashboard intentionally presents a curated subset and does not display every entity.", link: { label: "Review Dashboard documentation", href: "/docs/dashboard/" } },
      { title: "Find entities in Home Assistant", description: "Open Settings → Devices & services → Proxmox Extended Sensors, choose the relevant device, then open its entity list. The global Entities view can also be filtered by integration, device or entity name." },
    ],
  },
];

const countEntries = (groups: ReferenceGroup[]) => groups.reduce((count, group) => count + group.entries.length, 0);
const countGuidanceItems = (groups: ReferenceGuidanceGroup[]) => groups.reduce((count, group) => count + group.items.length, 0);

export const hardwareMemoryEntryCount = countEntries(hardwareMemoryGroups);
export const vmEntryCount = vmGroups[0].entries.length;
export const vmActionCount = vmGroups[1].entries.length;
export const ctEntryCount = ctGroups[0].entries.length;
export const ctActionCount = ctGroups[1].entries.length;
export const vmCtEntryCount = countEntries(vmGroups) + countEntries(ctGroups);
export const storageDisksZfsEntryCount = countEntries(storageDisksZfsGroups);
export const pbsServerDatastoreEntryCount = countEntries(pbsServerDatastoreGroups);
export const pbsMaintenanceEntryCount = countEntries(pbsMaintenanceGroups);
export const clusterSensorEntryCount = countEntries(clusterSensorGroups);
export const backupReplicationEntryCount = countEntries(backupReplicationGroups);
export const identityAvailabilityEntryCount = countGuidanceItems(identityAvailabilityGroups);
export const troubleshootingEntryCount = countGuidanceItems(troubleshootingGroups);
export const implementedReferenceEntryCount = pveNodeEntryCount
  + hardwareMemoryEntryCount
  + vmCtEntryCount
  + storageDisksZfsEntryCount
  + pbsServerDatastoreEntryCount
  + pbsMaintenanceEntryCount
  + clusterSensorEntryCount
  + backupReplicationEntryCount
  + identityAvailabilityEntryCount
  + troubleshootingEntryCount;
