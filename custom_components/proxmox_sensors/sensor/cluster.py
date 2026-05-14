"""Cluster-level sensors for Proxmox Extended Sensors."""

from __future__ import annotations
import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

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
        self._attr_name = "Status"
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
        self._attr_name = "Nodes Online"
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
        self._attr_name = "CPU Usage"
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
        self._attr_name = "RAM Usage"
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
        self._attr_name = "VMs Running"
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
        self._attr_name = "CTs Running"
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
        self._attr_name = "Storage Usage"
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
        self._attr_name = "HA Status"
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
# 9. FIREWALL Status
# ---------------------------------------------------------------------------


class ProxmoxClusterFirewallSensor(CoordinatorEntity, SensorEntity):
    """Cluster Firewall status sensor."""

    def __init__(self, coordinator, cluster_name, entry_id):
        super().__init__(coordinator)
        self._cluster_name = cluster_name
        self._entry_id = entry_id

        self._attr_name = "Firewall"
        self._attr_unique_id = f"proxmox_cluster_firewall_{cluster_name}"
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


class ProxmoxRestoredBackupSensor(ProxmoxClusterBaseSensor, RestoreEntity):
    """Base class for backup sensors that can survive an empty startup payload."""

    _restored_state = None
    _restored_attrs = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is None:
            return

        self._restored_state = last_state.state
        self._restored_attrs = dict(last_state.attributes or {})

    def _backup_jobs(self) -> dict:
        data = self.coordinator.data.get("backup_jobs", {})
        return data if isinstance(data, dict) else {}

    def _restored_attr(self, key, default=None):
        if not isinstance(self._restored_attrs, dict):
            return default
        return self._restored_attrs.get(key, default)

    def _restored_state_or_unknown(self):
        if self._restored_state in (None, STATE_UNKNOWN, STATE_UNAVAILABLE):
            return "unknown"
        return self._restored_state

    def _has_valid_run(self, backup_jobs):
        jobs = backup_jobs.get("jobs", [])
        return any(job.get("last_run") for job in jobs)


class ProxmoxBackupJobsSensor(ProxmoxRestoredBackupSensor):
    """Summary sensor for Proxmox backup jobs."""

    def __init__(self, coordinator, entry_id: str, node: str):
        super().__init__(coordinator, entry_id, node)
        self._attr_name = "Backup Jobs"
        self._attr_unique_id = f"pve_{entry_id}_cluster_backup_jobs"
        self._attr_icon = "mdi:backup-restore"

    @property
    def native_value(self):
        backup_jobs = self._backup_jobs() or {}

        jobs = backup_jobs.get("jobs", [])
        has_valid_run = any(job.get("last_run") for job in jobs)

        if not has_valid_run:
            return self._restored_state_or_unknown()

        state = backup_jobs.get("state")
        if state and state != "unknown":
            return state

        return self._restored_state_or_unknown()

    @property
    def extra_state_attributes(self):
        backup_jobs = self._backup_jobs() or {}

        jobs = backup_jobs.get("jobs", [])
        has_valid_run = any(job.get("last_run") for job in jobs)

        if not has_valid_run:
            return {
                "total_jobs": self._restored_attr("total_jobs", 0),
                "failed_jobs": self._restored_attr("failed_jobs", 0),
                "last_run": self._restored_attr("last_run"),
                "jobs": self._restored_attr("jobs", []),
            }

        return {
            "total_jobs": backup_jobs.get("total_jobs"),
            "failed_jobs": backup_jobs.get("failed_jobs"),
            "last_run": backup_jobs.get("last_run"),
            "jobs": backup_jobs.get("jobs"),
        }

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


class ProxmoxBackupAgeSensor(ProxmoxRestoredBackupSensor):
    """Sensor for backup age in hours."""

    def __init__(self, coordinator, entry_id: str, node: str):
        super().__init__(coordinator, entry_id, node)

        self._attr_name = "Backup Age"
        self._attr_unique_id = f"pve_{entry_id}_backup_age"
        self._attr_icon = "mdi:clock-outline"
        self._attr_native_unit_of_measurement = "h"
        self._attr_state_class = "measurement"

    @property
    def native_value(self):
        data = self._backup_jobs()

        last_run = data.get("last_run") or self._restored_attr("last_backup")
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
        last_backup = data.get("last_run") or self._restored_attr("last_backup")

        return {
            "last_backup_ago_hours": self.native_value,
            "last_backup": last_backup,
            "status": data.get("state") or self._restored_attr("status"),
            "total_jobs": data.get("total_jobs", self._restored_attr("total_jobs")),
            "failed_jobs": data.get("failed_jobs", self._restored_attr("failed_jobs")),
        }


class ProxmoxBackupHealthSensor(ProxmoxRestoredBackupSensor):
    """Sensor for backup health status."""

    def __init__(self, coordinator, entry_id: str, node: str):
        super().__init__(coordinator, entry_id, node)

        self._attr_name = "Backup Health"
        self._attr_unique_id = f"pve_{entry_id}_backup_health"
        self._attr_icon = "mdi:shield-check"
        self._attr_device_class = None

    @property
    def native_value(self):
        data = self._backup_jobs()
        age = None
        failed = data.get("failed_jobs", self._restored_attr("failed_jobs", 0))

        # Reusar cálculo del backup_age si existe
        try:
            last_run = data.get("last_run") or self._restored_attr("last_backup")
            if last_run:
                from dateutil import parser
                from datetime import datetime, timezone

                last_run_dt = parser.isoparse(last_run)
                now = datetime.now(tz=timezone.utc)
                age = (now - last_run_dt).total_seconds() / 3600
        except Exception:
            age = None

        if (age is not None and age >= 48) or failed >= 2:
            return "critical"

        if (age is not None and age >= 24) or failed >= 1:
            return "warning"

        if age is not None:
            return "healthy"

        return self._restored_state_or_unknown()

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
            "last_backup": data.get("last_run") or self._restored_attr("last_backup"),
            "failed_jobs": data.get("failed_jobs", self._restored_attr("failed_jobs")),
            "total_jobs": data.get("total_jobs", self._restored_attr("total_jobs")),
        }


# ---------------------------------------------------------------------------
# 11. TASKS
# ---------------------------------------------------------------------------


class ProxmoxFailedTasksSensor(ProxmoxClusterBaseSensor):
    """Sensor for recent failed cluster tasks."""

    def __init__(self, coordinator, entry_id: str, node: str):
        super().__init__(coordinator, entry_id, node)

        self._attr_name = "Failed Tasks"
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
            attrs["last_task"] = last_task
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
