"""Sensor platform for Proxmox Extended Sensors."""

from __future__ import annotations
import logging

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr
from .hardware import ProxmoxHardwareNVMeSensor

from .zfs import ProxmoxZFSPoolSensor
from .memory import ProxmoxDimmSensor
from .sensor_last_action import PBSLastActionSensor
from ..const import DOMAIN, CONF_NODE, CONF_PLATFORM_TYPE
from ..logic.guest_keys import matches_selected_guest

_LOGGER = logging.getLogger(__name__)

# Node Sensors
from .node import (
    ProxmoxNodeSensor,
    ProxmoxNodeUpdatesSensor,
    ProxmoxCPUInfoSensor,
    ProxmoxKSMSensor,
    ProxmoxMemorySensor,
    ProxmoxSwapSensor,
    ProxmoxRootFSSensor,
    ProxmoxClusterTasksSensor,
    PVEBackupProgressSensor,
    ProxmoxNodesSensor,
    ProxmoxNodeIOWaitSensor,
    ProxmoxNodeLoadAverageSensor,
    ProxmoxNodeScoreSensor,
    ProxmoxNodeMountedDisksSensor,
    ProxmoxStoragesSensor,
)

from .cluster import (
    ProxmoxBackupJobsSensor,
    ProxmoxClusterStatusSensor,
    ProxmoxClusterNodesSensor,
    ProxmoxClusterCPUSensor,
    ProxmoxClusterRAMSensor,
    ProxmoxClusterVMsSensor,
    ProxmoxClusterCTsSensor,
    ProxmoxClusterStorageSensor,
    ProxmoxClusterHASensor,
)

# Hardware Sensors (lm-sensors)
from .hardware import ProxmoxHardwareSensor

# Physical Disks
from .disks import ProxmoxDiskSensor

# Storage
from .storage import ProxmoxStorageSensor, ProxmoxStorageAttributeSensor

# Virtual Machines
from .vm import ProxmoxVMSensor, ProxmoxVMAttributeSensor

# Containers
from .ct import ProxmoxContainerSensor, ProxmoxContainerAttributeSensor

# PBS Sensors
from .pbs import (
    ProxmoxPBSDatastoreUsageSensor,
    ProxmoxPBSDatastoreSizeSensor,
    ProxmoxPBSDedupSensor,
    ProxmoxPBSMaintenanceSensor,
    ProxmoxPBSCpuSensor,
    ProxmoxPBSRamSensor,
    ProxmoxPBSRamTotalSensor,
    ProxmoxPBSRamUsedSensor,
    ProxmoxPBSRamFreeSensor,
    ProxmoxPBSLastBackupTimeSensor,
    ProxmoxPBSLastBackupSizeSensor,
    ProxmoxPBSLastBackupStatusSensor,
    ProxmoxPBSBackupErrorsSensor,
    ProxmoxPBSBackupsListSensor,
    ProxmoxPBSTaskSensor,
    ProxmoxPBSTaskTypeSensor,
    ProxmoxPBSTaskStatusSensor,
    ProxmoxPBSTaskMessageSensor,
    ProxmoxPBSTaskDurationSensor,
    ProxmoxPBSAuthStatusSensor,
    ProxmoxPBSVersionSensor,
    ProxmoxPBSReleaseSensor,
    ProxmoxPBSVerifySensor,
    ProxmoxPBSPruneSensor,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up all Proxmox sensors with user-selected filtering."""

    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    selected_vms = entry.options.get("selected_vms", entry.data.get("selected_vms", []))
    selected_cts = entry.options.get("selected_cts", entry.data.get("selected_cts", []))
    selected_storage = entry.options.get(
        "selected_storage", entry.data.get("selected_storage", [])
    )

    enable_physical_disks = entry.options.get(
        "enable_physical_disks", entry.data.get("enable_physical_disks", True)
    )

    enable_lm_sensors = entry.options.get(
        "enable_lm_sensors", entry.data.get("enable_lm_sensors", True)
    )

    enable_smart_monitoring = entry.options.get(
        "enable_smart_monitoring", entry.data.get("enable_smart_monitoring", True)
    )

    enable_node_controls = entry.options.get(
        "enable_node_controls", entry.data.get("enable_node_controls", False)
    )

    enable_backup_progress = entry.options.get(
        "enable_backup_progress", entry.data.get("enable_backup_progress", True)
    )

    enable_storage_list = entry.options.get(
        "enable_storage_list", entry.data.get("enable_storage_list", True)
    )

    enable_nodes_list = entry.options.get(
        "enable_nodes_list", entry.data.get("enable_nodes_list", True)
    )

    enable_cluster = entry.options.get(
        "enable_cluster", entry.data.get("enable_cluster", True)
    )

    hass.data[DOMAIN][entry.entry_id]["enable_node_controls"] = enable_node_controls

    node = entry.data.get(CONF_NODE, "Proxmox")
    server_type = hass.data[DOMAIN][entry.entry_id].get("server_type", "PVE")

    entities = []
    c_data = coordinator.data

    if not c_data:
        _LOGGER.warning("No data found in coordinator for %s", node)
        return

    if enable_storage_list and server_type == "PVE":
        try:
            storage_sensor = ProxmoxStoragesSensor(coordinator, entry.entry_id, node)
            entities.append(storage_sensor)
        except Exception as e:
            _LOGGER.error("Error creating storage summary sensor: %s", e)

    # =================PVE SECTION===================
    if server_type == "PVE":
        device_registry = dr.async_get(hass)

        # Create BOTH devices BEFORE entities
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, f"proxmox_node_{node}")},
            manufacturer="Proxmox",
            model="Proxmox Node",
            name=f"Node: {node}",
        )

        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, f"pve_{node}_node_{node}")},
            manufacturer="Proxmox",
            model="Proxmox Node",
            name=f"Node: {node}",
        )

        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, f"mounted_disks_{node}")},
            manufacturer="Proxmox",
            model="Mounted Disks",
            name=f"6. Mounted Disks: {node}",
        )

        # ========NODES LIST SENSOR========
        if server_type == "PVE" and enable_nodes_list:
            try:
                nodes_sensor = ProxmoxNodesSensor(coordinator, entry.entry_id, node)
                entities.append(nodes_sensor)
            except Exception as e:
                _LOGGER.error("Error creating nodes list sensor: %s", e)

        # =======BACKUP PROGRESS SENSOR=========
        if enable_backup_progress:
            try:
                sensor = PVEBackupProgressSensor(coordinator, node, entry.entry_id)
                entities.append(sensor)
            except Exception as e:
                _LOGGER.error("Error creating backup progress sensor: %s", e)

        # Hardware monitoring (lm-sensors)
        if enable_lm_sensors:
            hardware_data = c_data.get("hardware", {})

            cpu_sensors = []
            pch_sensors = []
            nvme_sensors = []
            sata_sensors = []
            other_sensors = []

            cpu_created = False
            chipset_created = False

            # First: Classify all sensors
            for key in hardware_data:
                sid = key.lower()

                # CPU
                if any(
                    x in sid
                    for x in [
                        "coretemp",
                        "core",
                        "package",
                        "cpu",
                        "k10temp",
                        "zenpower",
                        "tctl",
                        "tdie",
                        "tccd",
                    ]
                ):
                    cpu_sensors.append(key)

                # Chipset / motherboard
                elif any(x in sid for x in ["pch", "acpitz", "it87", "nct67"]):
                    pch_sensors.append(key)

                # NVMe
                elif "nvme" in sid:
                    nvme_sensors.append(key)

                # SATA
                elif any(x in sid for x in ["drivetemp", "scsi", "sd", "ata"]):
                    sata_sensors.append(key)

                else:
                    other_sensors.append(key)

            # Second: Group NVMe by device
            import re

            nvme_devices = set()

            for key in nvme_sensors:
                match = re.search(r"(nvme[-_]pci[-_][^_\s]+|nvme\d+)", key.lower())
                if match:
                    nvme_devices.add(match.group(1).replace("_", "-"))

            if not nvme_devices:
                smart_data = c_data.get("smart", {}).get(node, {})
                for disk_id, disk in smart_data.items():
                    if disk.get("device_type") == "nvme":
                        nvme_devices.add(str(disk_id).lower())

            # Create sensors
            for device_prefix in nvme_devices:
                sensor = ProxmoxHardwareNVMeSensor(coordinator, device_prefix, node)
                if sensor.is_valid():
                    entities.append(sensor)

            # Third: Order sensors
            ordered = cpu_sensors + pch_sensors + sata_sensors + other_sensors

            for key in ordered:
                sid = key.lower()

                if "nvme" in sid:
                    continue

                # Skip adapters/pwm
                if any(x in sid for x in ["adapter", "pwm"]):
                    continue

                # ---------------- CPU (only one) ----------------
                if any(
                    x in sid
                    for x in [
                        "coretemp",
                        "core",
                        "package",
                        "cpu",
                        "k10temp",
                        "zenpower",
                        "tctl",
                        "tdie",
                        "tccd",
                    ]
                ):
                    if cpu_created:
                        continue
                    cpu_created = True

                # ---------------- CHIPSET (only one clean) ----------------
                if any(x in sid for x in ["pch"]):
                    if chipset_created:
                        continue

                    sensor = ProxmoxHardwareSensor(coordinator, key, node)

                    # Mark as primary
                    sensor._attr_translation_key = "chipset_temp"
                    sensor._attr_name = "Chipset Temp"

                    if sensor.is_valid():
                        entities.append(sensor)
                        chipset_created = True
                    continue

                # Do not create sensor for acpitz
                if "acpitz" in sid:
                    continue

                # ---------------- REMAINING ----------------
                sensor = ProxmoxHardwareSensor(coordinator, key, node)
                if sensor.is_valid():
                    entities.append(sensor)

        # -------- Memory --------
        memory_map = c_data.get("memory", {}).get(node, {}).get("dimms", {})

        for dimm_id in memory_map:
            entities.append(ProxmoxDimmSensor(coordinator, node, dimm_id))

        # Node & Cluster monitoring
        node_data = c_data.get("node", {})
        if node_data:
            entities.append(ProxmoxClusterTasksSensor(coordinator, node))
            entities.append(ProxmoxNodeUpdatesSensor(coordinator, node))

            entities.append(ProxmoxNodeIOWaitSensor(coordinator, node))
            entities.append(ProxmoxNodeLoadAverageSensor(coordinator, node))
            entities.append(ProxmoxNodeScoreSensor(coordinator, node))
            entities.append(ProxmoxNodeMountedDisksSensor(coordinator, node))

            mapping = {
                "cpuinfo": ProxmoxCPUInfoSensor,
                "ksm": ProxmoxKSMSensor,
                "memory": ProxmoxMemorySensor,
                "swap": ProxmoxSwapSensor,
                "rootfs": ProxmoxRootFSSensor,
            }

            for key, cls in mapping.items():
                if key in node_data:
                    entities.append(cls(coordinator, node))

            for key in node_data:
                if key not in mapping and key not in (
                    "kversion",
                    "boot-info",
                    "last_task",
                    "wait",
                ):
                    entities.append(ProxmoxNodeSensor(coordinator, key, node))

        # Physical Disks
        if enable_physical_disks:
            for d_id, d_info in c_data.get("disks", {}).items():
                d_model = str(d_info.get("model", "")).lower()
                if d_model and "boot" not in d_model:
                    entities.append(
                        ProxmoxDiskSensor(
                            coordinator, d_id, node, d_info.get("model") or d_id
                        )
                    )

        # Storage pools
        storage_map = c_data.get("storage", {})
        created_storages = set()

        for st_name, st in storage_map.items():

            # Skip storages without name
            if not st_name:
                continue

            # Avoid duplicates
            if st_name in created_storages:
                continue

            # Skip offline storages
            if st.get("active") != 1:
                continue

            # -------- INTELLIGENT FILTER --------
            is_shared = st.get("shared", 0) == 1
            storage_node = st.get("node")
            storage_path = st.get("path", "")
            storage_type = st.get("type", "")

            # ---- SHARED (PBS, NFS, CIFS...) ----
            if is_shared:
                pass

            # ---- NON-SHARED (local storages) ----
            else:
                # Respect node if defined
                if storage_node and storage_node != node:
                    continue

                # Detect mounted disks (USB / bind mounts)
                if storage_path.startswith("/mnt") or storage_path.startswith("/media"):

                    total = st.get("total", 0) or 0
                    used = st.get("used", 0) or 0

                    # If no size, it's not mounted on this node
                    if total == 0 and used == 0:
                        continue

            # Respect user selection
            if st_name not in selected_storage:
                continue

            created_storages.add(st_name)

            entities.append(ProxmoxStorageSensor(coordinator, st_name, st, node))

            for label, key in [
                ("Used Space", "used"),
                ("Free Space", "avail"),
                ("Total Capacity", "total"),
                ("Type", "type"),
            ]:
                entities.append(
                    ProxmoxStorageAttributeSensor(
                        coordinator, st_name, st, label, key, node
                    )
                )

        # -------- ZFS POOLS --------
        zfs_data = c_data.get("zfs_pools", {})

        for pool_name in zfs_data:
            entities.append(ProxmoxZFSPoolSensor(coordinator, node, pool_name))

        # Virtual Machines
        vm_map = c_data.get("vms", {})
        for vm_key, vm_data in vm_map.items():
            vm_id = vm_data.get("vmid", vm_key)
            vm_node = vm_data.get("node", node)
            if matches_selected_guest(selected_vms, vm_node, vm_id, vm_key):
                label = vm_data.get("name", vm_id)
                entities.append(
                    ProxmoxVMSensor(
                        coordinator,
                        vm_id,
                        vm_node,
                        label,
                        guest_key=vm_key,
                    )
                )
                for attr, unit, icon in [
                    ("cpu_usage", "%", "mdi:cpu-64-bit"),
                    ("memory_used", "GB", "mdi:memory"),
                    ("memory_total", "GB", "mdi:memory"),
                    ("disk_total", "GB", "mdi:harddisk-plus"),
                    ("uptime", "h", "mdi:timer-sand"),
                    ("network_rx", "GB", "mdi:download-network"),
                    ("network_tx", "GB", "mdi:upload-network"),
                ]:
                    entities.append(
                        ProxmoxVMAttributeSensor(
                            coordinator,
                            vm_id,
                            vm_node,
                            label,
                            attr,
                            unit,
                            icon,
                            guest_key=vm_key,
                        )
                    )

        # Containers (LXC)
        ct_map = c_data.get("cts", {})
        for ct_key, ct_data in ct_map.items():
            ct_id = ct_data.get("vmid", ct_key)
            ct_node = ct_data.get("node", node)
            if matches_selected_guest(selected_cts, ct_node, ct_id, ct_key):
                label = ct_data.get("name", ct_id)
                entities.append(
                    ProxmoxContainerSensor(
                        coordinator,
                        ct_id,
                        ct_node,
                        label,
                        guest_key=ct_key,
                    )
                )
                for attr, unit, icon in [
                    ("cpu_usage", "%", "mdi:cpu-64-bit"),
                    ("memory_used", "GB", "mdi:memory"),
                    ("memory_total", "GB", "mdi:memory"),
                    ("disk_total", "GB", "mdi:harddisk-plus"),
                    ("disk_used", "GB", "mdi:harddisk"),
                    ("uptime", "h", "mdi:timer-outline"),
                    ("network_rx", "GB", "mdi:download-network"),
                    ("network_tx", "GB", "mdi:upload-network"),
                ]:
                    entities.append(
                        ProxmoxContainerAttributeSensor(
                            coordinator,
                            ct_id,
                            ct_node,
                            label,
                            attr,
                            unit,
                            icon,
                            guest_key=ct_key,
                        )
                    )

    # ==============CLUSTER SECTION====================
    elif server_type == "CLUSTER":
        from .cluster import (
            ProxmoxClusterStatusSensor,
            ProxmoxClusterNodesSensor,
            ProxmoxClusterCPUSensor,
            ProxmoxClusterRAMSensor,
            ProxmoxClusterVMsSensor,
            ProxmoxClusterCTsSensor,
            ProxmoxClusterStorageSensor,
            ProxmoxClusterHASensor,
            ProxmoxClusterFirewallSensor,
            ProxmoxBackupAgeSensor,
            ProxmoxBackupHealthSensor,
            ProxmoxFailedTasksSensor,
        )

        cluster_status = c_data.get("cluster_status", {})
        cluster_name = cluster_status.get("name", "Proxmox Cluster")

        device_registry = dr.async_get(hass)
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, f"proxmox_cluster_{entry.entry_id}")},
            manufacturer="Proxmox",
            model="Proxmox VE Cluster",
            name=f"Cluster: {cluster_name}",
        )

        entities.append(ProxmoxClusterStatusSensor(coordinator, entry.entry_id, node))
        entities.append(ProxmoxClusterNodesSensor(coordinator, entry.entry_id, node))
        entities.append(ProxmoxClusterCPUSensor(coordinator, entry.entry_id, node))
        entities.append(ProxmoxClusterRAMSensor(coordinator, entry.entry_id, node))
        entities.append(ProxmoxClusterVMsSensor(coordinator, entry.entry_id, node))
        entities.append(ProxmoxClusterCTsSensor(coordinator, entry.entry_id, node))
        entities.append(ProxmoxClusterStorageSensor(coordinator, entry.entry_id, node))
        entities.append(
            ProxmoxClusterFirewallSensor(coordinator, cluster_name, entry.entry_id)
        )
        entities.append(ProxmoxBackupJobsSensor(coordinator, entry.entry_id, node))
        if c_data.get("cluster_ha"):
            entities.append(ProxmoxClusterHASensor(coordinator, entry.entry_id, node))
        entities.append(ProxmoxBackupAgeSensor(coordinator, entry.entry_id, node))
        entities.append(ProxmoxBackupHealthSensor(coordinator, entry.entry_id, node))
        entities.append(ProxmoxFailedTasksSensor(coordinator, entry.entry_id, node))

    # ==============PBS SECTION====================
    elif server_type == "PBS":
        server_id = entry.data["server_id"]

        # Node Hardware Status
        entities.append(ProxmoxPBSCpuSensor(coordinator, server_id))
        entities.append(ProxmoxPBSRamSensor(coordinator, server_id))
        entities.append(ProxmoxPBSRamTotalSensor(coordinator, server_id))
        entities.append(ProxmoxPBSRamUsedSensor(coordinator, server_id))
        entities.append(ProxmoxPBSRamFreeSensor(coordinator, server_id))

        # Datastores
        for store_id in c_data.get("pbs_datastores", {}):

            # Last Action
            entities.append(PBSLastActionSensor(coordinator, store_id))

            entities.append(
                ProxmoxPBSDatastoreUsageSensor(coordinator, server_id, store_id)
            )

            for key, lbl, icon in [
                ("total", "Total", "mdi:harddisk"),
                ("used", "Used", "mdi:harddisk-remove"),
                ("avail", "Free", "mdi:harddisk-plus"),
            ]:
                entities.append(
                    ProxmoxPBSDatastoreSizeSensor(
                        coordinator, server_id, store_id, key, lbl, icon
                    )
                )

            entities.append(ProxmoxPBSDedupSensor(coordinator, server_id, store_id))
            entities.append(
                ProxmoxPBSMaintenanceSensor(coordinator, server_id, store_id)
            )
            entities.append(ProxmoxPBSVerifySensor(coordinator, server_id, store_id))
            entities.append(ProxmoxPBSPruneSensor(coordinator, server_id, store_id))
            entities.append(
                ProxmoxPBSLastBackupTimeSensor(coordinator, server_id, store_id)
            )
            entities.append(
                ProxmoxPBSLastBackupSizeSensor(coordinator, server_id, store_id)
            )
            entities.append(
                ProxmoxPBSLastBackupStatusSensor(coordinator, server_id, store_id)
            )
            entities.append(
                ProxmoxPBSBackupErrorsSensor(coordinator, server_id, store_id)
            )
            entities.append(
                ProxmoxPBSBackupsListSensor(coordinator, server_id, store_id)
            )

        # Global PBS Status
        entities.append(ProxmoxPBSTaskSensor(coordinator, server_id))
        entities.append(ProxmoxPBSTaskTypeSensor(coordinator, server_id))
        entities.append(ProxmoxPBSTaskStatusSensor(coordinator, server_id))
        entities.append(ProxmoxPBSTaskMessageSensor(coordinator, server_id))
        entities.append(ProxmoxPBSTaskDurationSensor(coordinator, server_id))
        entities.append(ProxmoxPBSAuthStatusSensor(coordinator, server_id))
        entities.append(ProxmoxPBSVersionSensor(coordinator, server_id))
        entities.append(ProxmoxPBSReleaseSensor(coordinator, server_id))

    # =========ENTITY AND DEVICE CLEANUP============
    ent_reg = er.async_get(hass)
    existing_entries = er.async_entries_for_config_entry(ent_reg, entry.entry_id)
    new_unique_ids = {getattr(entity, "_attr_unique_id", None) for entity in entities}

    for entity_entry in existing_entries:
        if entity_entry.unique_id not in new_unique_ids:
            _LOGGER.info("Removing obsolete entity: %s", entity_entry.entity_id)
            ent_reg.async_remove(entity_entry.entity_id)

    dev_reg = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(dev_reg, entry.entry_id)
    for device in devices:
        if not er.async_entries_for_device(ent_reg, device.id):
            _LOGGER.info("Removing orphan device: %s", device.name)
            dev_reg.async_remove_device(device.id)

    if entities:
        async_add_entities(entities)
