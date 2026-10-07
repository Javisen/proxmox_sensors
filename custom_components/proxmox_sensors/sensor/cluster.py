"""Cluster-level sensors for Proxmox Extended Sensors."""

from __future__ import annotations
import logging
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from ..const import DOMAIN

from dateutil import parser
from datetime import datetime, timezone

_LOGGER = logging.getLogger(__name__)


def _coerce_proxmox_bool(value):
    """Convert Proxmox-style truthy values to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "enabled"}
    return None


def _safe(data: dict, *keys, default=None):
    """Safely traverse nested dicts."""
    for key in keys:
        if not isinstance(data, dict):
            return default
        data = data.get(key, default)
    return data


# ----------Base class----------


class ProxmoxClusterBaseSensor(CoordinatorEntity, SensorEntity):
    """Base sensor for cluster-level data."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry_id: str, node: str):
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._node = node

    @property
    def device_info(self):
        cluster_data = self.coordinator.data.get("cluster_status", {})
        cluster_name = cluster_data.get("name", "Proxmox Cluster")
        return {
            "identifiers": {(DOMAIN, f"proxmox_cluster_{self._entry_id}")},
            "name": f"Cluster: {cluster_name}",
            "manufacturer": "Proxmox",
            "model": "Proxmox VE Cluster",
        }

    def _cluster(self) -> dict:
        return self.coordinator.data.get("cluster_status", {})

    def _resources(self) -> list:
        return self.coordinator.data.get("cluster_resources", [])

    def _ha(self) -> dict:
        return self.coordinator.data.get("cluster_ha", {})


# ---------------------------------------------------------------------------
# 1. Cluster Status — main sensor (quorum + name)
# ---------------------------------------------------------------------------


class ProxmoxClusterStatusSensor(ProxmoxClusterBaseSensor):
    """Main cluster sensor: name, quorum, version."""

    def __init__(self, coordinator, entry_id: str, node: str):
        super().__init__(coordinator, entry_id, node)
        self._attr_translation_key = "cluster_status"
        self._attr_unique_id = f"pve_{entry_id}_cluster_status"
        self._attr_icon = "mdi:server-network"

    @property
    def native_value(self):
        c = self._cluster()
        if not c:
            return "unknown"
        # Proxmox API returns "quorate" (int 0/1), not "quorum"
        quorate = c.get("quorate", c.get("quorum", 0))
        return "quorate" if quorate else "no quorum"

    @property
    def extra_state_attributes(self):
        c = self._cluster()

        nodes_info = [r for r in self._resources() if r.get("type") == "node"]
        online = sum(
            1 for n in nodes_info if n.get("status") == "online" or n.get("online") == 1
        )
        offline = len(nodes_info) - online
        quorate = bool(c.get("quorate", c.get("quorum", 0)))

        return {
            "cluster_name": c.get("name", "unknown"),
            "version": c.get("version"),
            "quorum": quorate,
            "nodes_total": len(nodes_info),
            "nodes_online": online,
            "nodes_offline": offline,
            "node_list": [n.get("node", n.get("name")) for n in nodes_info],
        }


# ---------------------------------------------------------------------------
# 2. Nodes summary
# ---------------------------------------------------------------------------


class ProxmoxClusterNodesSensor(ProxmoxClusterBaseSensor):
    """How many nodes are online vs offline."""

    def __init__(self, coordinator, entry_id: str, node: str):
        super().__init__(coordinator, entry_id, node)
        self._attr_translation_key = "cluster_nodes_online"
        self._attr_unique_id = f"pve_{entry_id}_cluster_nodes_online"
        self._attr_icon = "mdi:server"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "nodes"

    @property
    def native_value(self):
        nodes = [r for r in self._resources() if r.get("type") == "node"]
        return sum(
            1 for n in nodes if n.get("status") == "online" or n.get("online") == 1
        )

    @property
    def extra_state_attributes(self):
        nodes = [r for r in self._resources() if r.get("type") == "node"]
        online = [
            n for n in nodes if n.get("status") == "online" or n.get("online") == 1
        ]
        offline = [n for n in nodes if n not in online]
        return {
            "total": len(nodes),
            "online": len(online),
            "offline": len(offline),
            "online_nodes": [n.get("node", n.get("name")) for n in online],
            "offline_nodes": [n.get("node", n.get("name")) for n in offline],
        }


# ---------------------------------------------------------------------------
# 3. Cluster CPU usage (aggregate)
# ---------------------------------------------------------------------------


class ProxmoxClusterCPUSensor(ProxmoxClusterBaseSensor):
    """Aggregated CPU usage across all cluster nodes."""

    def __init__(self, coordinator, entry_id: str, node: str):
        super().__init__(coordinator, entry_id, node)
        self._attr_translation_key = "cluster_cpu_usage"
        self._attr_unique_id = f"pve_{entry_id}_cluster_cpu"
        self._attr_icon = "mdi:cpu-64-bit"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "%"

    @property
    def native_value(self):
        nodes = [
            r
            for r in self._resources()
            if r.get("type") == "node" and r.get("status") == "online"
        ]
        if not nodes:
            return None
        total_cpu = sum(r.get("cpu", 0) * r.get("maxcpu", 1) for r in nodes)
        total_max = sum(r.get("maxcpu", 1) for r in nodes)
        if total_max == 0:
            return None
        return round((total_cpu / total_max) * 100, 1)

    @property
    def extra_state_attributes(self):
        nodes = [r for r in self._resources() if r.get("type") == "node"]
        return {
            "total_cores": sum(r.get("maxcpu", 0) for r in nodes),
            "per_node": {
                r.get("node"): round(r.get("cpu", 0) * 100, 1)
                for r in nodes
                if r.get("node")
            },
        }


# ---------------------------------------------------------------------------
# 4. Cluster RAM usage (aggregate)
# ---------------------------------------------------------------------------


class ProxmoxClusterRAMSensor(ProxmoxClusterBaseSensor):
    """Aggregated RAM usage across all cluster nodes."""

    def __init__(self, coordinator, entry_id: str, node: str):
        super().__init__(coordinator, entry_id, node)
        self._attr_translation_key = "cluster_ram_usage"
        self._attr_unique_id = f"pve_{entry_id}_cluster_ram"
        self._attr_icon = "mdi:memory"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "%"

    @property
    def native_value(self):
        nodes = [
            r
            for r in self._resources()
            if r.get("type") == "node" and r.get("status") == "online"
        ]
        total_used = sum(r.get("mem", 0) for r in nodes)
        total_max = sum(r.get("maxmem", 1) for r in nodes)
        if total_max == 0:
            return None
        return round((total_used / total_max) * 100, 1)

    @property
    def extra_state_attributes(self):
        nodes = [r for r in self._resources() if r.get("type") == "node"]

        def to_gb(b):
            return round(b / (1024**3), 2) if b else 0

        return {
            "total_gb": to_gb(sum(r.get("maxmem", 0) for r in nodes)),
            "per_node_total_gb": {
                r.get("node"): to_gb(r.get("maxmem", 0)) for r in nodes if r.get("node")
            },
            "total_used_gb": to_gb(sum(r.get("mem", 0) for r in nodes)),
            "per_node_used_gb": {
                r.get("node"): to_gb(r.get("mem", 0)) for r in nodes if r.get("node")
            },
        }


# ---------------------------------------------------------------------------
# 5. VMs running across cluster
# ---------------------------------------------------------------------------


class ProxmoxClusterVMsSensor(ProxmoxClusterBaseSensor):
    """Total VMs running in the cluster."""

    def __init__(self, coordinator, entry_id: str, node: str):
        super().__init__(coordinator, entry_id, node)
        self._attr_translation_key = "cluster_vms_running"
        self._attr_unique_id = f"pve_{entry_id}_cluster_vms"
        self._attr_icon = "mdi:monitor-multiple"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "VMs"

    @property
    def native_value(self):
        vms = [r for r in self._resources() if r.get("type") == "qemu"]
        return sum(1 for v in vms if v.get("status") == "running")

    @property
    def extra_state_attributes(self):
        vms = [r for r in self._resources() if r.get("type") == "qemu"]
        running = [v for v in vms if v.get("status") == "running"]
        stopped = [v for v in vms if v.get("status") == "stopped"]
        other = [v for v in vms if v.get("status") not in ("running", "stopped")]
        return {
            "total": len(vms),
            "running": len(running),
            "stopped": len(stopped),
            "other": len(other),
            "running_list": [
                {
                    "name": v.get("name", v.get("vmid")),
                    "node": v.get("node"),
                    "vmid": v.get("vmid"),
                }
                for v in running
            ],
        }


# ---------------------------------------------------------------------------
# 6. CTs running across cluster
# ---------------------------------------------------------------------------


class ProxmoxClusterCTsSensor(ProxmoxClusterBaseSensor):
    """Total containers running in the cluster."""

    def __init__(self, coordinator, entry_id: str, node: str):
        super().__init__(coordinator, entry_id, node)
        self._attr_translation_key = "cluster_cts_running"
        self._attr_unique_id = f"pve_{entry_id}_cluster_cts"
        self._attr_icon = "mdi:box-shadow"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "CTs"

    @property
    def native_value(self):
        cts = [r for r in self._resources() if r.get("type") == "lxc"]
        return sum(1 for c in cts if c.get("status") == "running")

    @property
    def extra_state_attributes(self):
        cts = [r for r in self._resources() if r.get("type") == "lxc"]
        running = [c for c in cts if c.get("status") == "running"]
        stopped = [c for c in cts if c.get("status") == "stopped"]
        return {
            "total": len(cts),
            "running": len(running),
            "stopped": len(stopped),
            "running_list": [
                {
                    "name": c.get("name", c.get("vmid")),
                    "node": c.get("node"),
                    "vmid": c.get("vmid"),
                }
                for c in running
            ],
        }


# ---------------------------------------------------------------------------
# 7. Cluster Storage usage (aggregate)
# ---------------------------------------------------------------------------


class ProxmoxClusterStorageSensor(ProxmoxClusterBaseSensor):
    """Aggregated storage usage across all cluster shared storages."""

    def __init__(self, coordinator, entry_id: str, node: str):
        super().__init__(coordinator, entry_id, node)
        self._attr_translation_key = "cluster_storage_usage"
        self._attr_unique_id = f"pve_{entry_id}_cluster_storage"
        self._attr_icon = "mdi:database"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "%"

    def _storage_resources(self):
        return [r for r in self._resources() if r.get("type") == "storage"]

    @property
    def native_value(self):
        storages = self._storage_resources()
        total_used = sum(r.get("disk", 0) for r in storages)
        total_max = sum(r.get("maxdisk", 0) for r in storages)
        if total_max == 0:
            return None
        return round((total_used / total_max) * 100, 1)

    @property
    def extra_state_attributes(self):
        storages = self._storage_resources()

        def to_gb(b):
            return round(b / (1024**3), 2) if b else 0

        return {
            "total_used_gb": to_gb(sum(r.get("disk", 0) for r in storages)),
            "total_gb": to_gb(sum(r.get("maxdisk", 0) for r in storages)),
            "storages": [
                {
                    "id": r.get("storage"),
                    "node": r.get("node"),
                    "total_gb": to_gb(r.get("maxdisk", 0)),
                    "used_gb": to_gb(r.get("disk", 0)),
                    "status": r.get("status"),
                }
                for r in storages
            ],
        }


# ---------------------------------------------------------------------------
# 8. HA Status
# ---------------------------------------------------------------------------


class ProxmoxClusterHASensor(ProxmoxClusterBaseSensor):
    """Cluster High Availability manager status."""

    def __init__(self, coordinator, entry_id: str, node: str):
        super().__init__(coordinator, entry_id, node)
        self._attr_translation_key = "cluster_ha_status"
        self._attr_unique_id = f"pve_{entry_id}_cluster_ha"
        self._attr_icon = "mdi:shield-check"

    @property
    def native_value(self):
        ha = self._ha()
        if not ha:
            return "unavailable"
        return ha.get("quorum_ok") and "active" or "inactive"

    @property
    def icon(self):
        ha = self._ha()
        if not ha:
            return "mdi:shield-off"
        return "mdi:shield-check" if ha.get("quorum_ok") else "mdi:shield-alert"

    @property
    def extra_state_attributes(self):
        ha = self._ha()
        if not ha:
            return {"available": False}
        return {
            "quorum_ok": ha.get("quorum_ok"),
            "master_node": ha.get("master"),
            "timestamp": ha.get("timestamp"),
        }


# ---------------------------------------------------------------------------
# 9. COROSYNC QDEVICE
# ---------------------------------------------------------------------------


class ProxmoxClusterQDeviceSensor(ProxmoxClusterBaseSensor):
    """Corosync QDevice connection status."""

    def __init__(self, coordinator, entry_id: str, node: str):
        super().__init__(coordinator, entry_id, node)
        self._attr_translation_key = "cluster_qdevice"
        self._attr_unique_id = f"pve_{entry_id}_cluster_qdevice"
        self._attr_icon = "mdi:shield-link-variant"

    def _qdevice(self) -> dict:
        value = self.coordinator.data.get("cluster_qdevice", {})
        return value if isinstance(value, dict) else {}

    @property
    def native_value(self):
        return self._qdevice().get("State", "unknown")

    @property
    def extra_state_attributes(self):
        qdevice = self._qdevice()
        return {
            "QNetd host": qdevice.get("QNetd host"),
            "Last poll call": qdevice.get("Last poll call"),
            "Model": qdevice.get("Model"),
            "Algorithm": qdevice.get("Algorithm"),
            "Tie-breaker": qdevice.get("Tie-breaker"),
        }


def setup_qdevice_sensor(hass, coordinator, entry, async_add_entities):
    """Reconcile the optional QDevice entity for one CLUSTER entry."""
    registry = er.async_get(hass)
    unique_id = f"pve_{entry.entry_id}_cluster_qdevice"
    instance = None
    removing_task = None

    def registered_row():
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        return registry.async_get(entity_id) if entity_id else None

    async def remove_entity():
        nonlocal instance
        try:
            for entity in (instance,) if instance is not None else ():
                if getattr(entity, "hass", None) is not None:
                    await entity.async_remove(force_remove=True)
        except Exception:
            _LOGGER.exception("Failed to remove QDevice entity")
        finally:
            row = registered_row()
            if row is not None and row.config_entry_id == entry.entry_id:
                registry.async_remove(row.entity_id)
            instance = None

    @callback
    def reconcile():
        nonlocal instance, removing_task
        data = coordinator.data or {}
        if data.get("cluster_qdevice_ok") is not True:
            return

        if removing_task is not None:
            if not removing_task.done():
                return
            removing_task = None

        qdevice = data.get("cluster_qdevice")
        configured = isinstance(qdevice, dict) and bool(qdevice)
        row = registered_row()

        if configured:
            if instance is not None:
                return
            if row is not None and row.config_entry_id != entry.entry_id:
                return
            instance = ProxmoxClusterQDeviceSensor(
                coordinator, entry.entry_id, entry.data.get("node", "")
            )
            async_add_entities([instance])
            return

        if instance is not None or (
            row is not None and row.config_entry_id == entry.entry_id
        ):
            removing_task = hass.async_create_task(remove_entity())
            # If the device is reconfigured before removal finishes, make
            # that same update eligible for recreation once the registry row
            # has been cleaned up.
            removing_task.add_done_callback(lambda _task: reconcile())

    reconcile()
    entry.async_on_unload(coordinator.async_add_listener(reconcile))


# ---------------------------------------------------------------------------
# 10. FIREWALL Status
# ---------------------------------------------------------------------------


class ProxmoxClusterFirewallSensor(CoordinatorEntity, SensorEntity):
    """Cluster Firewall status sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, cluster_name, entry_id, identity_context=None):
        super().__init__(coordinator)
        self._cluster_name = cluster_name
        self._entry_id = entry_id

        self._attr_translation_key = "cluster_firewall"
        self._attr_unique_id = (
            f"proxmox_cluster_firewall_{identity_context.scope}"
            if identity_context and identity_context.use_scoped_identity
            else f"proxmox_cluster_firewall_{cluster_name}"
        )
        self._attr_icon = "mdi:shield-check"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"proxmox_cluster_{self._entry_id}")},
            "manufacturer": "Proxmox",
            "model": "Proxmox VE Cluster",
            "name": f"0. Cluster: {cluster_name}",
        }

    @property
    def native_value(self):
        firewall = self.coordinator.data.get("cluster_firewall")

        if not isinstance(firewall, dict):
            return "Unknown"

        enabled = _coerce_proxmox_bool(firewall.get("enable"))

        if enabled is None:
            return "Unknown"

        return "Enabled" if enabled else "Disabled"

    @property
    def extra_state_attributes(self):
        firewall = self.coordinator.data.get("cluster_firewall")

        if not isinstance(firewall, dict):
            return {}

        return {
            "raw_enable": firewall.get("enable"),
            "options": firewall,
        }

    @property
    def icon(self):
        state = self.native_value

        if not state:
            return "mdi:shield-outline"

        state = state.lower()

        if state in ["enabled", "on"]:
            return "mdi:shield-check"
        elif state in ["disabled", "off"]:
            return "mdi:shield-off"

        return "mdi:shield-outline"


# ---------------------------------------------------------------------------
#  10. BACKUPS SENSORS
# ---------------------------------------------------------------------------


class ProxmoxBackupSensor(ProxmoxClusterBaseSensor):
    def _backup_jobs(self) -> dict:
        data = self.coordinator.data.get("backup_jobs", {})
        return data if isinstance(data, dict) else {}


class ProxmoxBackupJobsSensor(ProxmoxBackupSensor):
    """Summary sensor for Proxmox backup jobs."""

    def __init__(self, coordinator, entry_id: str, node: str):
        super().__init__(coordinator, entry_id, node)
        self._attr_translation_key = "cluster_backup_jobs"
        self._attr_unique_id = f"pve_{entry_id}_cluster_backup_jobs"
        self._attr_icon = "mdi:backup-restore"

    @property
    def native_value(self):
        state = self._backup_jobs().get("state")
        return state if state in {"ok", "error"} else "unknown"

    @property
    def extra_state_attributes(self):
        return {"total_jobs": self._backup_jobs().get("total_jobs")}

    @property
    def icon(self):
        state = self.native_value

        if state == "ok":
            return "mdi:check-circle"
        elif state == "warning":
            return "mdi:alert-circle"
        elif state == "error":
            return "mdi:close-circle"
        return "mdi:help-circle"


class ProxmoxBackupAgeSensor(ProxmoxBackupSensor):
    """Sensor for backup age in hours."""

    def __init__(self, coordinator, entry_id: str, node: str):
        super().__init__(coordinator, entry_id, node)

        self._attr_translation_key = "cluster_backup_age"
        self._attr_unique_id = f"pve_{entry_id}_backup_age"
        self._attr_icon = "mdi:clock-outline"
        self._attr_native_unit_of_measurement = "h"
        self._attr_state_class = "measurement"

    @property
    def native_value(self):
        data = self._backup_jobs()

        last_run = data.get("last_task_run")
        if last_run is None:
            return None

        try:
            last_run_dt = parser.isoparse(last_run)
        except Exception:
            return None

        now = datetime.now(tz=timezone.utc)

        age_hours = (now - last_run_dt).total_seconds() / 3600

        age_hours = max(age_hours, 0)

        return round(age_hours, 2)

    @property
    def extra_state_attributes(self):
        data = self._backup_jobs()
        last_backup = data.get("last_task_run")

        return {
            "last_backup_ago_hours": self.native_value,
            "last_backup": last_backup,
            "status": data.get("state", "unknown"),
            "total_jobs": data.get("total_jobs"),
        }


class ProxmoxBackupHealthSensor(ProxmoxBackupSensor):
    """Sensor for backup health status."""

    def __init__(self, coordinator, entry_id: str, node: str):
        super().__init__(coordinator, entry_id, node)

        self._attr_translation_key = "cluster_backup_health"
        self._attr_unique_id = f"pve_{entry_id}_backup_health"
        self._attr_icon = "mdi:shield-check"
        self._attr_device_class = None

    @property
    def native_value(self):
        data = self._backup_jobs()
        age = None

        # Reusar cálculo del backup_age si existe
        try:
            last_run = data.get("last_task_run")
            if last_run:
                from dateutil import parser
                from datetime import datetime, timezone

                last_run_dt = parser.isoparse(last_run)
                now = datetime.now(tz=timezone.utc)
                age = (now - last_run_dt).total_seconds() / 3600
        except Exception:
            age = None

        if age is not None and age >= 48:
            return "critical"

        if (age is not None and age >= 24) or data.get("state") == "error":
            return "warning"

        if age is not None and data.get("state") == "ok":
            return "healthy"

        return "unknown"

    @property
    def icon(self):
        state = self.state

        if state == "healthy":
            return "mdi:shield-check"
        elif state == "warning":
            return "mdi:shield-alert"
        elif state == "critical":
            return "mdi:shield-remove"
        return "mdi:shield-off"

    @property
    def extra_state_attributes(self):
        data = self._backup_jobs()

        return {
            "last_backup": data.get("last_task_run"),
            "total_jobs": data.get("total_jobs"),
        }


# ---------------------------------------------------------------------------
# 11. TASKS
# ---------------------------------------------------------------------------


class ProxmoxFailedTasksSensor(ProxmoxClusterBaseSensor):
    """Sensor for recent failed cluster tasks."""

    def __init__(self, coordinator, entry_id: str, node: str):
        super().__init__(coordinator, entry_id, node)

        self._attr_translation_key = "cluster_failed_tasks"
        self._attr_unique_id = f"pve_{entry_id}_cluster_failed_tasks"
        self._attr_icon = "mdi:alert-circle"
        self._attr_state_class = "measurement"

    @property
    def native_value(self):
        tasks = self._get_failed_tasks()
        return len(tasks)

    def _get_failed_tasks(self):
        tasks = self.coordinator.data.get("cluster_tasks") or []

        from datetime import datetime, timezone, timedelta

        now = datetime.now(tz=timezone.utc)
        cutoff = now - timedelta(hours=24)

        failed = []

        for task in tasks:
            if not isinstance(task, dict):
                continue

            status = task.get("status")
            if not status or status.lower() == "ok":
                continue

            endtime = task.get("endtime") or task.get("starttime")
            if not endtime:
                continue

            try:
                task_time = datetime.fromtimestamp(endtime, tz=timezone.utc)
            except Exception:
                continue

            if task_time < cutoff:
                continue

            failed.append(
                {
                    "node": task.get("node"),
                    "type": task.get("type"),
                    "status": status,
                    "time": task_time.isoformat(),
                }
            )

        return failed

    @property
    def extra_state_attributes(self):
        failed = self._get_failed_tasks()

        # 🔥 ordenar por fecha (más reciente primero)
        failed.sort(key=lambda x: x["time"], reverse=True)

        attrs = {
            "failed_tasks": len(failed),
        }

        if failed:
            last_task = failed[0]
            attrs["last_failure"] = last_task["time"]
            task_time = datetime.fromisoformat(last_task["time"])
            attrs["last_task"] = {
                **last_task,
                "time": dt_util.as_local(task_time).strftime("%Y-%m-%d %H:%M:%S"),
            }
            attrs["last_task_type"] = last_task.get("type")
            attrs["last_node"] = last_task.get("node")
        else:
            attrs["last_failure"] = "Never"

        return attrs

    @property
    def icon(self):
        count = self.native_value

        if count == 0:
            return "mdi:check-circle"
        elif count < 3:
            return "mdi:alert-circle"
        return "mdi:close-circle"
