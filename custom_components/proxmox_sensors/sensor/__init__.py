"""Sensor platform for Proxmox Extended Sensors."""

from __future__ import annotations
import logging
import re

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr
from .hardware import ProxmoxHardwareNVMeSensor

from .zfs import ProxmoxZFSPoolSensor
from .memory import ProxmoxDimmSensor
from .sensor_last_action import PBSLastActionSensor
from ..const import DOMAIN, CONF_NODE, CONF_PLATFORM_TYPE
from ..logic.guest_cleanup import cleanup_excluded_guest_devices
from ..logic.guest_migration_cleanup import setup_guest_migration_cleanup
from ..logic.guest_keys import (
    matches_selected_guest,
    resolve_cluster_id,
    find_guest_node_in_resources,
)
from ..logic.guest_selection import get_cycle_guest_selections, allow_excluded_cluster_guest_cleanup

_LOGGER = logging.getLogger(__name__)

# Node Sensors
from .node import (
    ProxmoxNodeSensor,
    ProxmoxNodeUpdatesSensor,
    ProxmoxCPUInfoSensor,
    ProxmoxKSMSensor,
    ProxmoxKSMStatusSensor,
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
    ProxmoxSidecarStatusSensor,
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




def _build_guest_entities(
    coordinator, c_data: dict, node: str, selected_vms, selected_cts, cluster_id
) -> list:
    """Build the current set of VM/CT entities from coordinator data.

    Used both for the initial platform setup and for live reconciliation
    when a guest appears, disappears, or migrates to another node.
    """
    entities = []

    # Virtual Machines
    vm_map = c_data.get("vms", {})
    for vm_key, vm_data in vm_map.items():
        vm_id = vm_data.get("vmid", vm_key)
        vm_node = vm_data.get("node", node)
        if not matches_selected_guest(selected_vms, vm_node, vm_id, vm_key):
            continue
        label = vm_data.get("name", vm_id)
        entities.append(
            ProxmoxVMSensor(
                coordinator, vm_id, vm_node, label, guest_key=vm_key, cluster_id=cluster_id
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
                    cluster_id=cluster_id,
                )
            )

    # Containers (LXC)
    ct_map = c_data.get("cts", {})
    for ct_key, ct_data in ct_map.items():
        ct_id = ct_data.get("vmid", ct_key)
        ct_node = ct_data.get("node", node)
        if not matches_selected_guest(selected_cts, ct_node, ct_id, ct_key):
            continue
        label = ct_data.get("name", ct_id)
        entities.append(
            ProxmoxContainerSensor(
                coordinator, ct_id, ct_node, label, guest_key=ct_key, cluster_id=cluster_id
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
                    cluster_id=cluster_id,
                )
            )

    return entities


GRACE_CYCLES = 3

_VM_ATTR_SENSORS = [
    ("cpu_usage", "%", "mdi:cpu-64-bit"),
    ("memory_used", "GB", "mdi:memory"),
    ("memory_total", "GB", "mdi:memory"),
    ("disk_total", "GB", "mdi:harddisk-plus"),
    ("uptime", "h", "mdi:timer-sand"),
    ("network_rx", "GB", "mdi:download-network"),
    ("network_tx", "GB", "mdi:upload-network"),
]

_CT_ATTR_SENSORS = [
    ("cpu_usage", "%", "mdi:cpu-64-bit"),
    ("memory_used", "GB", "mdi:memory"),
    ("memory_total", "GB", "mdi:memory"),
    ("disk_total", "GB", "mdi:harddisk-plus"),
    ("disk_used", "GB", "mdi:harddisk"),
    ("uptime", "h", "mdi:timer-outline"),
    ("network_rx", "GB", "mdi:download-network"),
    ("network_tx", "GB", "mdi:upload-network"),
]


def _guest_identity_key(kind: str, cluster_id: str, vmid) -> str:
    """Stable, node-independent identity for a guest: kind + cluster + vmid."""
    return f"{kind}:{cluster_id}:{vmid}"


def _build_guest_entity_groups(
    coordinator, c_data: dict, node: str, selected_vms, selected_cts, cluster_id
) -> dict:
    """Build cluster-scoped VM/CT entities grouped by guest identity.

    Each group holds the guest's status sensor together with ALL of its
    attribute sensors (CPU, memory, disk, network, uptime...), so they can be
    released as one atomic unit on migration. Only meaningful when
    ``cluster_id`` is set (i.e. a sibling CLUSTER entry is configured);
    returns an empty dict otherwise, since migration tracking across nodes
    is not possible/safe without a stable cluster-wide identity.
    """
    groups: dict = {}
    if not cluster_id:
        return groups

    vm_map = c_data.get("vms", {})
    for vm_key, vm_data in vm_map.items():
        vm_id = vm_data.get("vmid", vm_key)
        vm_node = vm_data.get("node", node)
        if not matches_selected_guest(selected_vms, vm_node, vm_id, vm_key):
            continue
        label = vm_data.get("name", vm_id)
        entities = [
            ProxmoxVMSensor(
                coordinator, vm_id, vm_node, label, guest_key=vm_key, cluster_id=cluster_id
            )
        ]
        for attr, unit, icon in _VM_ATTR_SENSORS:
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
                    cluster_id=cluster_id,
                )
            )
        groups[_guest_identity_key("vm", cluster_id, vm_id)] = entities

    ct_map = c_data.get("cts", {})
    for ct_key, ct_data in ct_map.items():
        ct_id = ct_data.get("vmid", ct_key)
        ct_node = ct_data.get("node", node)
        if not matches_selected_guest(selected_cts, ct_node, ct_id, ct_key):
            continue
        label = ct_data.get("name", ct_id)
        entities = [
            ProxmoxContainerSensor(
                coordinator, ct_id, ct_node, label, guest_key=ct_key, cluster_id=cluster_id
            )
        ]
        for attr, unit, icon in _CT_ATTR_SENSORS:
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
                    cluster_id=cluster_id,
                )
            )
        groups[_guest_identity_key("ct", cluster_id, ct_id)] = entities

    return groups


def _group_existing_entities_by_guest(guest_entities, cluster_id) -> dict:

    groups: dict = {}
    if not cluster_id:
        return groups

    for e in guest_entities:
        e_cluster_id = getattr(e, "_cluster_id", None)
        if not e_cluster_id:
            continue
        if isinstance(e, (ProxmoxVMSensor, ProxmoxVMAttributeSensor)):
            kind = "vm"
            vmid = e._vm_id
        elif isinstance(e, (ProxmoxContainerSensor, ProxmoxContainerAttributeSensor)):
            kind = "ct"
            vmid = e._ct_id
        else:
            continue
        gkey = _guest_identity_key(kind, e_cluster_id, vmid)
        groups.setdefault(gkey, []).append(e)

    return groups


def _setup_guest_reconciliation(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator,
    async_add_entities: AddEntitiesCallback,
    node: str,
    selected_vms,
    selected_cts,
    known_unique_ids: set,
    initial_pending_groups: dict | None = None,
    on_guest_release=None,
):

    pending_groups: dict = dict(initial_pending_groups or {})
    live_guest_instances: dict = {}
    missing_everywhere_counter: dict = {}

    @callback
    def _reconcile():
        c_data = coordinator.data or {}
        cluster_id = resolve_cluster_id(hass, c_data)
        ent_reg = er.async_get(hass)
        effective_selected_vms, effective_selected_cts = get_cycle_guest_selections(
            hass, entry, c_data, selected_vms, selected_cts, cluster_id
        )

        current_entities = _build_guest_entities(
            coordinator,
            c_data,
            node,
            effective_selected_vms,
            effective_selected_cts,
            cluster_id,
        )

        if cluster_id:
            current_groups = _build_guest_entity_groups(
                coordinator,
                c_data,
                node,
                effective_selected_vms,
                effective_selected_cts,
                cluster_id,
            )

            cluster_resources = c_data.get("cluster_resources", [])
            cluster_resources_ok = c_data.get("cluster_resources_ok", True)

            for gkey, ents in list(pending_groups.items()):
                all_confirmed = all(
                    (
                        reg_entity_id := ent_reg.async_get_entity_id(
                            "sensor", DOMAIN, e._attr_unique_id
                        )
                    )
                    and (reg_entry := ent_reg.async_get(reg_entity_id))
                    and reg_entry.config_entry_id == entry.entry_id
                    for e in ents
                )
                if all_confirmed:
                    live_guest_instances[gkey] = ents
                    known_unique_ids.update(e._attr_unique_id for e in ents)
                    del pending_groups[gkey]
                    _LOGGER.info(
                        "Guest %s confirmed claimed by this entry (%s)",
                        gkey,
                        node,
                    )
                    continue

                was_rejected = any(
                    getattr(e, "registry_entry", None) is None for e in ents
                )
                if was_rejected:
                    _LOGGER.info(
                        "Guest %s lost the claim race last cycle; discarding "
                        "rejected instances so it can be retried this cycle",
                        gkey,
                    )
                    del pending_groups[gkey]

            configured_pve_nodes = {
                (e.data.get(CONF_NODE) or "").lower()
                for e in hass.config_entries.async_entries(DOMAIN)
                if e.data.get(CONF_PLATFORM_TYPE) == "PVE"
            }

            for gkey in list(live_guest_instances.keys()):
                if gkey in current_groups:
                    # Still local and healthy — clear any stale grace count.
                    missing_everywhere_counter.pop(gkey, None)
                    continue

                kind, _cluster, vmid_str = gkey.split(":", 2)
                located_node = find_guest_node_in_resources(
                    cluster_resources, kind, vmid_str
                )

                if (
                    located_node
                    and located_node.lower() != node.lower()
                    and located_node.lower() in configured_pve_nodes
                ):

                    _LOGGER.info(
                        "Guest %s %s migrated from %s to %s; releasing local "
                        "instances via entity.async_remove(force_remove=False) "
                        "- Entity Registry untouched",
                        kind,
                        vmid_str,
                        node,
                        located_node,
                    )
                    if on_guest_release is not None:
                        on_guest_release(kind, _cluster, vmid_str, located_node)
                    entities_to_release = live_guest_instances.pop(gkey)
                    for entity_obj in entities_to_release:
                        hass.async_create_task(
                            entity_obj.async_remove(force_remove=False)
                        )
                    known_unique_ids.difference_update(
                        e._attr_unique_id for e in entities_to_release
                    )
                    missing_everywhere_counter.pop(gkey, None)
                    continue

                if not cluster_resources_ok:
                    continue

                missing_everywhere_counter[gkey] = (
                    missing_everywhere_counter.get(gkey, 0) + 1
                )
                if missing_everywhere_counter[gkey] >= GRACE_CYCLES:
                    _LOGGER.info(
                        "Guest %s %s missing for %d consecutive cycles "
                        "(not found locally or in cluster_resources). No "
                        "action taken: entity instance and Entity Registry "
                        "left exactly as-is, per design.",
                        kind,
                        vmid_str,
                        GRACE_CYCLES,
                    )

            def _group_ready_to_claim(ents) -> bool:
                for entity_obj in ents:
                    reg_entity_id = ent_reg.async_get_entity_id(
                        "sensor", DOMAIN, entity_obj._attr_unique_id
                    )
                    if not reg_entity_id:
                        continue

                    reg_entry = ent_reg.async_get(reg_entity_id)
                    if reg_entry and reg_entry.config_entry_id == entry.entry_id:
                        continue

                    state = hass.states.get(reg_entity_id)
                    if state is None or "restored" in state.attributes:
                        continue

                    return False

                return True

            for gkey, ents in current_groups.items():
                if gkey in live_guest_instances or gkey in pending_groups:

                    continue

                kind, _cluster, vmid_str = gkey.split(":", 2)
                located_node = find_guest_node_in_resources(
                    cluster_resources, kind, vmid_str
                )

                if cluster_resources_ok and located_node:
                    if located_node.lower() != node.lower():
                        continue

                    if not _group_ready_to_claim(ents):
                        continue

                    pending_groups[gkey] = ents

                    async_add_entities(ents)
                    continue

                if not cluster_resources_ok:
                    continue

                if not _group_ready_to_claim(ents):
                    continue

                pending_groups[gkey] = ents
                async_add_entities(ents)

        new_entities = [
            e
            for e in current_entities
            if e._attr_unique_id not in known_unique_ids
            and not (cluster_id and e._attr_unique_id.startswith("pve_cluster_"))
        ]
        if new_entities:
            async_add_entities(new_entities)
            known_unique_ids.update(e._attr_unique_id for e in new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_reconcile))


def _cleanup_section_for_unique_id(unique_id, entry, server_type):
    uid = (unique_id or "").lower()
    if not uid:
        return None

    if "proxmox_vm_" in uid:
        return "vms"
    if "proxmox_ct_" in uid:
        return "cts"
    if "proxmox_storage_" in uid:
        return "storage"
    if "proxmox_zfs_" in uid:
        return "zfs_pools"
    if "proxmox_disk_" in uid:
        return "node_disks"
    if (
        "proxmox_hw_" in uid
        or "proxmox_cpu_temp_" in uid
        or "proxmox_nvme_" in uid
    ):
        return "hardware"

    node = (entry.data.get(CONF_NODE) or "").lower()
    if node and f"proxmox_{node}_" in uid and "dimm" in uid:
        return "memory"

    if server_type == "PBS":
        server_id = (entry.data.get("server_id") or "").lower()
        prefix = f"pbs_{server_id}_"
        if uid.startswith(prefix):
            rest = uid[len(prefix) :]
            datastore_suffixes = (
                "_usage",
                "_dedup",
                "_last_backup_time",
                "_last_backup_size",
                "_last_backup_status",
                "_backup_errors",
                "_backups_summary",
                "_gc_status",
                "_verify_status",
                "_prune_status",
                "_total",
                "_used",
                "_avail",
            )
            global_ids = {
                "ram_total",
                "ram_used",
                "ram_free",
                "node_cpu",
                "node_ram",
                "version",
                "release",
                "auth_status",
                "last_task",
                "last_task_type",
                "last_task_status",
                "last_task_message",
                "last_task_duration",
            }
            if rest not in global_ids and rest.endswith(datastore_suffixes):
                return "pbs_datastores"

    if server_type == "CLUSTER" and "cluster_ha" in uid:
        return "cluster_ha"

    return None


def _pbs_last_action_unique_id(server_id: str, store: str) -> str:
    return f"pbs_{server_id.lower()}_{store.lower()}_last_action"


def _reconcile_pbs_last_action_unique_ids(
    ent_reg,
    entry: ConfigEntry,
    server_id: str,
    stores,
) -> None:
    for store in stores:
        legacy_unique_id = f"{store.lower()}_last_action"
        scoped_unique_id = _pbs_last_action_unique_id(server_id, store)

        legacy_entity_id = ent_reg.async_get_entity_id(
            "sensor", DOMAIN, legacy_unique_id
        )
        if not legacy_entity_id:
            continue

        legacy_entry = ent_reg.async_get(legacy_entity_id)
        if legacy_entry is None or legacy_entry.config_entry_id != entry.entry_id:
            continue

        target_entity_id = ent_reg.async_get_entity_id(
            "sensor", DOMAIN, scoped_unique_id
        )
        if target_entity_id == legacy_entity_id:
            continue

        if target_entity_id:
            target_entry = ent_reg.async_get(target_entity_id)
            _LOGGER.warning(
                "Cannot migrate PBS LastAction unique_id %s -> %s for %s: "
                "target already belongs to %s",
                legacy_unique_id,
                scoped_unique_id,
                entry.entry_id,
                target_entry.config_entry_id if target_entry else target_entity_id,
            )
            continue

        ent_reg.async_update_entity(
            legacy_entity_id, new_unique_id=scoped_unique_id
        )
        _LOGGER.info(
            "Migrated PBS LastAction unique_id %s -> %s",
            legacy_unique_id,
            scoped_unique_id,
        )


_CPU_SENSOR_KEYS = [
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


def _hardware_sensor_type(value):
    """Detect the lm-sensors channel type from a raw sensor value."""
    if isinstance(value, dict):
        keys = [str(k).lower() for k in value]
        if any(re.match(r"^fan\d+_input$", k) for k in keys):
            return "fan"
        if any(re.match(r"^in\d+_input$", k) for k in keys):
            return "voltage"
        if any(re.match(r"^temp\d+_input$", k) for k in keys):
            return "temperature"
    return "temperature"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up all Proxmox sensors with user-selected filtering."""

    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    selected_vms = entry.options.get(
        "selected_vms", entry.data.get("selected_vms", None)
    )
    selected_cts = entry.options.get(
        "selected_cts", entry.data.get("selected_cts", None)
    )
    selected_storage = entry.options.get(
        "selected_storage", entry.data.get("selected_storage", None)
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

        node_device = device_registry.async_get_device_by_identifier(
            (DOMAIN, f"proxmox_node_{node}"), config_entry_id=entry.entry_id
        )
        if node_device is not None:
            entities.append(ProxmoxSidecarStatusSensor(coordinator, node, node_device))

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
            for key, value in hardware_data.items():
                sid = key.lower()

                # CPU: only real temperature channels may claim the CPU slot
                if (
                    _hardware_sensor_type(value) == "temperature"
                    and any(x in sid for x in _CPU_SENSOR_KEYS)
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
                if any(x in sid for x in _CPU_SENSOR_KEYS):
                    if cpu_created:
                        continue
                    cpu_created = True

                # ---------------- CHIPSET (only one clean) ----------------
                if any(x in sid for x in ["pch"]) and _hardware_sensor_type(
                    hardware_data.get(key)
                ) == "temperature":
                    if chipset_created:
                        continue

                    sensor = ProxmoxHardwareSensor(coordinator, key, node)

                    # Mark as primary
                    sensor._attr_translation_key = "chipset_temp"

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
        # KSM status is diagnostic data from the sidecar, so it must exist even
        # when its first request failed or PVE omitted the legacy ksm section.
        entities.append(ProxmoxKSMStatusSensor(coordinator, node))
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

        # Virtual Machines & Containers (cluster-migration aware)
        cluster_id = resolve_cluster_id(hass, c_data)
        effective_selected_vms, effective_selected_cts = get_cycle_guest_selections(
            hass, entry, c_data, selected_vms, selected_cts, cluster_id
        )
        guest_entities = _build_guest_entities(
            coordinator,
            c_data,
            node,
            effective_selected_vms,
            effective_selected_cts,
            cluster_id,
        )
        entities.extend(guest_entities)

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
        pbs_datastores = c_data.get("pbs_datastores", {})
        ent_reg = er.async_get(hass)

        _reconcile_pbs_last_action_unique_ids(
            ent_reg, entry, server_id, pbs_datastores.keys()
        )

        # Node Hardware Status
        entities.append(ProxmoxPBSCpuSensor(coordinator, server_id))
        entities.append(ProxmoxPBSRamSensor(coordinator, server_id))
        entities.append(ProxmoxPBSRamTotalSensor(coordinator, server_id))
        entities.append(ProxmoxPBSRamUsedSensor(coordinator, server_id))
        entities.append(ProxmoxPBSRamFreeSensor(coordinator, server_id))

        # Datastores
        for store_id in pbs_datastores:

            # Last Action
            entities.append(PBSLastActionSensor(coordinator, server_id, store_id))

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
    cleanup_confirmed = c_data.get("_cleanup_confirmed", {})
    legacy_pbs_last_action_ids = set()
    if server_type == "PBS":
        legacy_pbs_last_action_ids = {
            f"{store.lower()}_last_action"
            for store in c_data.get("pbs_datastores", {})
        }

    for entity_entry in existing_entries:
        # This cleanup belongs only to the sensor platform.
        # Never remove button, binary_sensor or entities from other platforms.
        if entity_entry.domain != "sensor":
            continue

        if entity_entry.unique_id in new_unique_ids:
            continue

        if entity_entry.unique_id in legacy_pbs_last_action_ids:
            continue

        if (entity_entry.unique_id or "").startswith("pve_cluster_"):
            if not allow_excluded_cluster_guest_cleanup(
                hass, entry, c_data, entity_entry.unique_id
            ):
                continue

        cleanup_section = _cleanup_section_for_unique_id(
            entity_entry.unique_id, entry, server_type
        )
        if cleanup_section and not cleanup_confirmed.get(cleanup_section, False):
            _LOGGER.info(
                "Skipping cleanup for %s because %s data is not confirmed fresh",
                entity_entry.entity_id,
                cleanup_section,
            )
            continue

        _LOGGER.info("Removing obsolete entity: %s", entity_entry.entity_id)
        ent_reg.async_remove(entity_entry.entity_id)
    dev_reg = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(dev_reg, entry.entry_id)
    for device in devices:
        # Guest devices require explicit exclusion, not merely an empty registry.
        if any(domain == DOMAIN and identifier.startswith(("proxmox_vm_", "proxmox_ct_"))
               for domain, identifier in device.identifiers):
            continue
        if not er.async_entries_for_device(ent_reg, device.id):
            _LOGGER.info("Removing orphan device: %s", device.name)
            dev_reg.async_remove_device(device.id)

    if server_type == "PVE":
        cleanup_excluded_guest_devices(hass)

    if entities:
        async_add_entities(entities)

    if server_type == "CLUSTER":
        from .replication import setup_replication_sensors

        setup_replication_sensors(hass, coordinator, entry, async_add_entities)

    # Live VM/CT migration handling
    if server_type == "PVE":

        known_guest_ids = {
            getattr(e, "_attr_unique_id", None)
            for e in guest_entities
            if not (cluster_id and getattr(e, "_cluster_id", None))
        }
        known_guest_ids.discard(None)

        initial_pending_groups = _group_existing_entities_by_guest(
            guest_entities, cluster_id
        )

        _setup_guest_reconciliation(
            hass,
            entry,
            coordinator,
            async_add_entities,
            node,
            effective_selected_vms,
            effective_selected_cts,
            known_guest_ids,
            initial_pending_groups=initial_pending_groups,
            on_guest_release=setup_guest_migration_cleanup(hass, entry, coordinator),
        )
