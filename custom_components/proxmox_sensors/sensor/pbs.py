"""Sensors PBS for Proxmox Extended Sensors."""

import math
import time

from homeassistant.const import PERCENTAGE, UnitOfInformation
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.util import dt as dt_util

from ..const import DOMAIN
from ..pbs_devices import pbs_device_identifier, pbs_parent_device
from .base import ProxmoxPbsBaseSensor


def extract_store_from_task(task):
    store = task.get("store") or task.get("datastore")
    if not store:
        worker_id = task.get("worker_id", "")
        if "::" in worker_id:
            store = worker_id.split("::")[0]
    return store


def _format_utc_timestamp(ts):
    """Convert UTC PBS timestamps into Home Assistant local time."""
    return dt_util.as_local(dt_util.utc_from_timestamp(ts)).strftime("%d/%m/%Y %H:%M:%S")


def _pbs_node_status(coordinator):
    """Return node status, or None when the optional capability is unavailable."""
    status = coordinator.data.get("pbs_node_status")
    return status if isinstance(status, dict) else None


class ProxmoxPBSVersionSensor(ProxmoxPbsBaseSensor):
    """Sensor for PBS version."""

    def __init__(self, coordinator, server_id):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id="version",
            name=None,
        )
        self._attr_translation_key = "pbs_version"
        self._attr_icon = "mdi:information-outline"

    def _get_value(self):
        return self.coordinator.data.get("pbs_version", "Unknown")


class ProxmoxPBSReleaseSensor(ProxmoxPbsBaseSensor):
    """Sensor for PBS release."""

    def __init__(self, coordinator, server_id):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id="release",
            name=None,
        )
        self._attr_translation_key = "pbs_release"
        self._attr_icon = "mdi:tag"

    def _get_value(self):
        return self.coordinator.data.get("pbs_release", "Unknown")


class ProxmoxPBSAuthStatusSensor(ProxmoxPbsBaseSensor):
    """Sensor for PBS auth status."""

    def __init__(self, coordinator, server_id):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id="auth_status",
            name=None,
        )
        self._attr_translation_key = "pbs_auth_status"
        self._attr_icon = "mdi:shield-check"

    def _get_value(self):
        return self.coordinator.data.get("pbs_auth_status", "UNKNOWN")


class ProxmoxPBSCpuSensor(ProxmoxPbsBaseSensor):
    """Sensor for CPU usage."""

    def __init__(self, coordinator, server_id):
        super().__init__(coordinator, server_id, "node_cpu", None, "%")
        self._attr_translation_key = "pbs_cpu_usage"
        self._attr_icon = "mdi:cpu-64-bit"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    def _get_value(self):
        status = _pbs_node_status(self.coordinator)
        if status is None:
            return None
        cpu = status.get("cpu")
        return round(cpu * 100, 2) if cpu is not None else 0

    @property
    def extra_state_attributes(self):
        status = _pbs_node_status(self.coordinator)
        if status is None:
            return {
                "cores": None,
                "model": None,
                "load_1m": None,
                "load_5m": None,
                "load_15m": None,
            }
        cpuinfo = status.get("cpuinfo") or {}

        # Fallback for containers
        cores = cpuinfo.get("cores") or status.get("cpu_cores") or status.get("cpus")

        loadavg = status.get("loadavg") or []

        return {
            "cores": cores,
            "model": cpuinfo.get("model"),
            "load_1m": loadavg[0] if len(loadavg) > 0 else None,
            "load_5m": loadavg[1] if len(loadavg) > 1 else None,
            "load_15m": loadavg[2] if len(loadavg) > 2 else None,
        }


class ProxmoxPBSRamSensor(ProxmoxPbsBaseSensor):
    """Sensor for RAM usage percentage."""

    def __init__(self, coordinator, server_id):
        super().__init__(coordinator, server_id, "node_ram", None, "%")
        self._attr_translation_key = "pbs_ram_usage"
        self._attr_icon = "mdi:memory"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    def _get_value(self):
        status = _pbs_node_status(self.coordinator)
        if status is None:
            return None
        memory = status.get("memory", {})
        total = memory.get("total")
        used = memory.get("used")
        if total and used:
            return round((used / total) * 100, 2)
        return 0

    @property
    def extra_state_attributes(self):
        status = _pbs_node_status(self.coordinator)
        if status is None:
            return {"total_gb": None, "used_gb": None, "free_gb": None}
        memory = status.get("memory", {})
        return {
            "total_gb": round(memory.get("total", 0) / (1024**3), 2),
            "used_gb": round(memory.get("used", 0) / (1024**3), 2),
            "free_gb": round(memory.get("free", 0) / (1024**3), 2),
        }


class ProxmoxPBSRamTotalSensor(ProxmoxPbsBaseSensor):
    """Sensor for total RAM."""

    def __init__(self, coordinator, server_id):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id="ram_total",
            name=None,
            unit="GB",
        )
        self._attr_translation_key = "pbs_ram_total"
        self._attr_icon = "mdi:memory"
        self._attr_native_unit_of_measurement = "GB"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    def _get_value(self):
        status = _pbs_node_status(self.coordinator)
        if status is None:
            return None
        ram = status.get("memory", {})
        return round(ram.get("total", 0) / (1024**3), 2)


class ProxmoxPBSRamUsedSensor(ProxmoxPbsBaseSensor):
    """Sensor for used RAM."""

    def __init__(self, coordinator, server_id):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id="ram_used",
            name=None,
            unit="GB",
        )
        self._attr_translation_key = "pbs_ram_used"
        self._attr_icon = "mdi:memory"
        self._attr_native_unit_of_measurement = "GB"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    def _get_value(self):
        status = _pbs_node_status(self.coordinator)
        if status is None:
            return None
        ram = status.get("memory", {})
        return round(ram.get("used", 0) / (1024**3), 2)


class ProxmoxPBSRamFreeSensor(ProxmoxPbsBaseSensor):
    """Sensor for free RAM."""

    def __init__(self, coordinator, server_id):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id="ram_free",
            name=None,
            unit="GB",
        )
        self._attr_translation_key = "pbs_ram_free"
        self._attr_icon = "mdi:memory"
        self._attr_native_unit_of_measurement = "GB"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    def _get_value(self):
        status = _pbs_node_status(self.coordinator)
        if status is None:
            return None
        ram = status.get("memory", {})
        return round(ram.get("free", 0) / (1024**3), 2)


class ProxmoxPBSTaskSensor(ProxmoxPbsBaseSensor):
    """Sensor for last task summary."""

    def __init__(self, coordinator, server_id):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id="last_task",
            name=None,
        )
        self._attr_translation_key = "pbs_last_task"
        self._attr_icon = "mdi:clipboard-list"

    def _get_value(self):
        tasks = self.coordinator.data.get("pbs_tasks", [])
        if not isinstance(tasks, list) or not tasks:
            return "No data"

        task = tasks[0]
        worker = task.get("worker_type", "Task")
        status = task.get("status") or task.get("msg") or "OK"
        return f"{worker}: {status}"

    @property
    def device_info(self):
        """Return device info for tasks."""
        return {
            "identifiers": {(DOMAIN, f"pbs_tasks_{self._server_id}")},
            "via_device_id": pbs_parent_device(self.coordinator),
            "name": f"Tasks - {self._server_id.upper()}",
            "manufacturer": "Proxmox",
            "model": "Backup Server Tasks",
        }


class ProxmoxPBSTaskTypeSensor(ProxmoxPbsBaseSensor):
    """Sensor for last task type."""

    def __init__(self, coordinator, server_id):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id="last_task_type",
            name=None,
        )
        self._attr_translation_key = "pbs_last_task_type"
        self._attr_icon = "mdi:clipboard-text"

    def _get_value(self):
        tasks = self.coordinator.data.get("pbs_tasks", [])
        if not isinstance(tasks, list) or not tasks:
            return None
        task = tasks[0]
        return task.get("worker_type")

    @property
    def device_info(self):
        """Return device info for tasks."""
        return {
            "identifiers": {(DOMAIN, f"pbs_tasks_{self._server_id}")},
            "via_device_id": pbs_parent_device(self.coordinator),
            "name": f"Tasks - {self._server_id.upper()}",
            "manufacturer": "Proxmox",
            "model": "Backup Server Tasks",
        }


class ProxmoxPBSTaskStatusSensor(ProxmoxPbsBaseSensor):
    """Sensor for last task status."""

    def __init__(self, coordinator, server_id):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id="last_task_status",
            name=None,
        )
        self._attr_translation_key = "pbs_last_task_status"
        self._attr_icon = "mdi:information"

    def _get_value(self):
        tasks = self.coordinator.data.get("pbs_tasks", [])
        if not isinstance(tasks, list) or not tasks:
            return "OK"

        task = tasks[0]
        status = task.get("status")
        if status:
            return status

        msg = task.get("msg", "").lower()
        if "ok" in msg:
            return "OK"
        if "error" in msg:
            return "Error"

        return "OK"

    @property
    def extra_state_attributes(self):
        tasks = self.coordinator.data.get("pbs_tasks", [])
        if not isinstance(tasks, list) or not tasks:
            return {}

        task = tasks[0]

        def format_ts(ts):
            if ts and isinstance(ts, (int, float)):
                return _format_utc_timestamp(ts)
            return ts

        return {
            "task_type": task.get("worker_type"),
            "vmid": task.get("worker_id"),
            "node": task.get("node", "server"),
            "upid": task.get("upid"),
            "start_time": format_ts(task.get("starttime")),
            "end_time": format_ts(task.get("endtime")),
        }

    @property
    def device_info(self):
        """Return device info for tasks."""
        return {
            "identifiers": {(DOMAIN, f"pbs_tasks_{self._server_id}")},
            "via_device_id": pbs_parent_device(self.coordinator),
            "name": f"Tasks - {self._server_id.upper()}",
            "manufacturer": "Proxmox",
            "model": "Backup Server Tasks",
        }


class ProxmoxPBSTaskMessageSensor(ProxmoxPbsBaseSensor):
    """Sensor for last task message."""

    def __init__(self, coordinator, server_id):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id="last_task_message",
            name=None,
        )
        self._attr_translation_key = "pbs_last_task_message"
        self._attr_icon = "mdi:message-text-outline"

    def _get_value(self):
        tasks = self.coordinator.data.get("pbs_tasks", [])
        if not isinstance(tasks, list) or not tasks:
            return "OK"
        task = tasks[0]
        msg = task.get("msg")
        return msg if msg else "OK"

    @property
    def device_info(self):
        """Return device info for tasks."""
        return {
            "identifiers": {(DOMAIN, f"pbs_tasks_{self._server_id}")},
            "via_device_id": pbs_parent_device(self.coordinator),
            "name": f"Tasks - {self._server_id.upper()}",
            "manufacturer": "Proxmox",
            "model": "Backup Server Tasks",
        }


class ProxmoxPBSTaskDurationSensor(ProxmoxPbsBaseSensor):
    """Sensor for last task duration."""

    def __init__(self, coordinator, server_id):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id="last_task_duration",
            name=None,
            unit="s",
        )
        self._attr_translation_key = "pbs_last_task_duration"
        self._attr_icon = "mdi:timer-outline"

    def _get_value(self):
        tasks = self.coordinator.data.get("pbs_tasks", [])
        if not isinstance(tasks, list) or not tasks:
            return 0

        task = tasks[0]
        start = task.get("starttime")
        end = task.get("endtime")

        if start and end:
            return int(end - start)

        if start and not end:
            import time

            return int(time.time() - start)

        return 0

    @property
    def device_info(self):
        """Return device info for tasks."""
        return {
            "identifiers": {(DOMAIN, f"pbs_tasks_{self._server_id}")},
            "via_device_id": pbs_parent_device(self.coordinator),
            "name": f"Tasks - {self._server_id.upper()}",
            "manufacturer": "Proxmox",
            "model": "Backup Server Tasks",
        }


class ProxmoxPBSDatastoreUsageSensor(ProxmoxPbsBaseSensor):
    """Sensor for datastore usage percentage."""

    def __init__(self, coordinator, server_id, store):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id=f"{store}_usage",
            name=None,
            unit=PERCENTAGE,
        )
        self._attr_translation_key = "pbs_datastore_usage"
        self._store = store
        self._attr_icon = "mdi:database-clock"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    def _get_value(self):
        data = self.coordinator.data.get("pbs_datastores", {}).get(self._store, {})
        used = data.get("used", 0)
        total = data.get("total", 0)
        return round((used / total) * 100, 2) if total > 0 else 0

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, pbs_device_identifier("datastore", self._server_id, self._store))},
            "via_device_id": pbs_parent_device(self.coordinator),
            "name": f"Datastore: {self._store}",
            "manufacturer": "Proxmox",
            "model": "Backup Server Datastore",
        }


class ProxmoxPBSDatastoreSizeSensor(ProxmoxPbsBaseSensor):
    """Sensor for datastore size (total/used/free)."""

    def __init__(self, coordinator, server_id, store, key, label, icon=None):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id=f"{store}_{key}",
            name=None,
            unit=UnitOfInformation.GIGABYTES,
        )
        self._store = store
        self._key = key
        translation_key_map = {
            "total": "pbs_datastore_total",
            "used": "pbs_datastore_used",
            "avail": "pbs_datastore_free",
        }
        self._attr_translation_key = translation_key_map.get(key)

        if icon:
            self._attr_icon = icon
        else:
            icons = {
                "total": "mdi:database",
                "used": "mdi:database-arrow-up",
                "free": "mdi:database-arrow-down",
            }
            self._attr_icon = icons.get(key, "mdi:database-outline")
        if key in ("total", "used", "avail"):
            self._attr_state_class = SensorStateClass.MEASUREMENT

    def _get_value(self):
        data = self.coordinator.data.get("pbs_datastores", {}).get(self._store, {})
        return round(data.get(self._key, 0) / (1024**3), 2)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, pbs_device_identifier("datastore", self._server_id, self._store))},
            "via_device_id": pbs_parent_device(self.coordinator),
            "name": f"Datastore: {self._store}",
            "manufacturer": "Proxmox",
            "model": "Backup Server Datastore",
        }


class ProxmoxPBSDedupSensor(ProxmoxPbsBaseSensor):
    """Sensor for datastore deduplication ratio."""

    def __init__(self, coordinator, server_id, store):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id=f"{store}_dedup",
            name=None,
            unit="x",
        )
        self._attr_translation_key = "pbs_dedup"
        self._store = store
        self._attr_icon = "mdi:clippy"

    def _get_value(self):
        data = self.coordinator.data.get("pbs_datastores", {}).get(self._store, {})
        idx = data.get("index-data-bytes", 0)
        disk = data.get("disk-bytes", 0)
        return round(idx / disk, 2) if disk > 0 else 1.0

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, pbs_device_identifier("datastore", self._server_id, self._store))},
            "via_device_id": pbs_parent_device(self.coordinator),
            "name": f"Datastore: {self._store}",
            "manufacturer": "Proxmox",
            "model": "Backup Server Datastore",
        }


class ProxmoxPBSLastBackupTimeSensor(ProxmoxPbsBaseSensor):
    """Sensor for last backup timestamp."""

    def __init__(self, coordinator, server_id, store):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id=f"{store}_last_backup_time",
            name=None,
        )
        self._attr_translation_key = "pbs_last_backup_time"
        self._store = store
        self._attr_icon = "mdi:clock-outline"

    def _get_value(self):
        data = self.coordinator.data.get("pbs_datastores", {}).get(self._store, {})
        last = data.get("last_backup")
        if not last:
            return None
        ts = last.get("backup-time")
        if (
            isinstance(ts, bool)
            or not isinstance(ts, (int, float))
            or not math.isfinite(ts)
        ):
            return None
        try:
            return dt_util.as_local(dt_util.utc_from_timestamp(ts)).strftime(
                "%d/%m/%Y %H:%M:%S"
            )
        except (OSError, OverflowError, ValueError):
            return None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, pbs_device_identifier("datastore", self._server_id, self._store))},
            "via_device_id": pbs_parent_device(self.coordinator),
            "name": f"Datastore: {self._store}",
            "manufacturer": "Proxmox",
            "model": "Backup Server Datastore",
        }


class ProxmoxPBSLastBackupSizeSensor(ProxmoxPbsBaseSensor):
    """Sensor for last backup size."""

    def __init__(self, coordinator, server_id, store):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id=f"{store}_last_backup_size",
            name=None,
            unit=UnitOfInformation.GIGABYTES,
        )
        self._attr_translation_key = "pbs_last_backup_size"
        self._store = store
        self._attr_icon = "mdi:database"

    def _get_value(self):
        data = self.coordinator.data.get("pbs_datastores", {}).get(self._store, {})
        last = data.get("last_backup")
        size = last.get("size") if last else 0
        return round(size / (1024**3), 2)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, pbs_device_identifier("datastore", self._server_id, self._store))},
            "via_device_id": pbs_parent_device(self.coordinator),
            "name": f"Datastore: {self._store}",
            "manufacturer": "Proxmox",
            "model": "Backup Server Datastore",
        }


class ProxmoxPBSLastBackupStatusSensor(ProxmoxPbsBaseSensor):
    """Sensor for last backup verification status."""

    def __init__(self, coordinator, server_id, store):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id=f"{store}_last_backup_status",
            name=None,
        )
        self._attr_translation_key = "pbs_last_backup_status"
        self._store = store
        self._attr_icon = "mdi:check-circle-outline"

    def _get_value(self):
        data = self.coordinator.data.get("pbs_datastores", {}).get(self._store, {})
        last = data.get("last_backup")

        if not last:
            return "No backups"

        ver = last.get("verification")
        if ver:
            state = ver.get("state")
            if state == "ok":
                return "Verified OK"
            if state == "failed":
                return "Verification Failed"
            return str(state).capitalize()

        return "Finished (Not Verified)"

    @property
    def icon(self):
        status = self.native_value
        if status == "Verified OK":
            return "mdi:check-decagram"
        if status == "Verification Failed":
            return "mdi:alert-decagram"
        if status == "No backups":
            return "mdi:database-off"
        return "mdi:check-circle-outline"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, pbs_device_identifier("datastore", self._server_id, self._store))},
            "via_device_id": pbs_parent_device(self.coordinator),
            "name": f"Datastore: {self._store}",
            "manufacturer": "Proxmox",
            "model": "Backup Server Datastore",
        }


class ProxmoxPBSBackupErrorsSensor(ProxmoxPbsBaseSensor):
    """Sensor for backup error count."""

    def __init__(self, coordinator, server_id, store):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id=f"{store}_backup_errors",
            name=None,
        )
        self._attr_translation_key = "pbs_backup_errors"
        self._store = store
        self._attr_icon = "mdi:alert-circle-outline"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    def _get_value(self):
        data = self.coordinator.data.get("pbs_datastores", {}).get(self._store, {})
        return len(data.get("backup_errors", []))

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, pbs_device_identifier("datastore", self._server_id, self._store))},
            "via_device_id": pbs_parent_device(self.coordinator),
            "name": f"Datastore: {self._store}",
            "manufacturer": "Proxmox",
            "model": "Backup Server Datastore",
        }


class ProxmoxPBSBackupsListSensor(ProxmoxPbsBaseSensor):
    """Sensor for backup summary."""

    def __init__(self, coordinator, server_id, store):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id=f"{store}_backups_summary",
            name=None,
        )
        self._attr_translation_key = "pbs_backups_summary"
        self._store = store
        self._attr_icon = "mdi:archive-clock-outline"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    def _get_value(self):
        data = self.coordinator.data.get("pbs_datastores", {}).get(self._store, {})
        return int(len(data.get("backups", [])))

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data.get("pbs_datastores", {}).get(self._store, {})
        backups = data.get("backups", [])

        summary = {}
        for b in backups:
            b_type = b.get("backup-type")
            b_id = b.get("backup-id")
            b_time = b.get("backup-time")
            if b_type and b_id and b_time:
                key = f"{b_type}/{b_id}"
                namespace = b.get("namespace")
                if namespace:
                    key = f"{namespace}/{key}"
                if key not in summary or b_time > summary[key]["raw_time"]:
                    summary[key] = {
                        "raw_time": b_time,
                        "last_backup": _format_utc_timestamp(b_time),
                    }

        return {
            "last_backups_per_resource": {
                k: v["last_backup"] for k, v in sorted(summary.items())
            },
            "total_snapshots": len(backups),
            "datastore_name": self._store,
        }

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, pbs_device_identifier("datastore", self._server_id, self._store))},
            "via_device_id": pbs_parent_device(self.coordinator),
            "name": f"Datastore: {self._store}",
            "manufacturer": "Proxmox",
            "model": "Backup Server Datastore",
        }


def _pbs_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _pbs_action_task(sensor, action):
    """Resolve an accepted UPID, or the latest external execution in this PBS."""
    hass = getattr(sensor, "hass", None)
    actions = (hass.data if hass else {}).get(DOMAIN, {}).get(
        sensor.coordinator.config_entry.entry_id, {}
    ).get("pbs_action_upids", {}).get(sensor._server_id, {}).get(sensor._store, {})
    upid = actions.get(action)
    if not isinstance(upid, str) or not upid.startswith("UPID:"):
        upid = None
    tasks = sensor.coordinator.data.get("pbs_tasks", [])
    tasks = [t for t in tasks if isinstance(t, dict)] if isinstance(tasks, list) else []
    if upid:
        return upid, next((t for t in tasks if t.get("upid") == upid), None)

    workers = {
        "gc": {"garbage_collection"},
        "prune": {"prune", "prunejob"},
        "verify": {"verify", "verifyjob", "verificationjob"},
    }[action]
    candidates = []
    for task in tasks:
        worker_id = task.get("worker_id")
        if task.get("worker_type") not in workers or not isinstance(worker_id, str):
            continue
        store = worker_id if action == "gc" else worker_id.split(":", 1)[0]
        if store == sensor._store and _pbs_number(task.get("starttime")):
            candidates.append(task)
    return None, max(candidates, key=lambda t: (t["starttime"], str(t.get("upid", ""))), default=None)


def _pbs_execution_state(task, accepted=None):
    if task is None:
        return "Iniciado" if accepted else None
    if task.get("endtime") is None:
        return "Running"
    status = task.get("status")
    if not isinstance(status, str) or not status or status.lower() == "unknown":
        return None
    return "OK" if status == "OK" else "Error"


def _pbs_execution_attributes(task, accepted=None):
    attrs = {"upid": accepted} if accepted else {}
    if task is None:
        return attrs
    attrs.update({key: task[key] for key in ("upid", "status", "starttime", "endtime")
                  if task.get(key) is not None})
    start, end = task.get("starttime"), task.get("endtime")
    for value, key in ((start, "started_at"), (end, "last_run")):
        if _pbs_number(value):
            try:
                attrs[key] = dt_util.as_local(dt_util.utc_from_timestamp(value)).isoformat()
            except (ValueError, OverflowError, OSError):
                pass
    finish = time.time() if end is None else end
    if _pbs_number(start) and _pbs_number(finish) and finish >= start:
        attrs["duration_sec"] = finish - start
        attrs["duration_min"] = round((finish - start) / 60, 2)
    return attrs


def _pbs_size(value):
    """Human-readable binary size; exact bytes remain in a separate attribute."""
    for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB"):
        if value < 1024 or unit == "EiB":
            return f"{value:.3f}".rstrip("0").rstrip(".") + f" {unit}"
        value /= 1024


def _pbs_remember_terminal(sensor, accepted, task):
    """Volatile memory only: never restored or reconstructed after HA restart."""
    if getattr(sensor, "_accepted_upid", None) != accepted:
        sensor._accepted_upid = accepted
        sensor._terminal_task = None
    if accepted and task is not None and task.get("endtime") is not None and task.get("status"):
        sensor._terminal_task = dict(task)
    return getattr(sensor, "_terminal_task", None) or task


class ProxmoxPBSMaintenanceSensor(ProxmoxPbsBaseSensor):
    """Sensor for garbage collection maintenance status."""

    def __init__(self, coordinator, server_id, store):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id=f"{store}_gc_status",
            name=None,
        )
        self._attr_translation_key = "pbs_gc_status"
        self._store = store
        self._attr_icon = "mdi:recycle-variant"

    def _execution(self):
        accepted, task = _pbs_action_task(self, "gc")
        data = self.coordinator.data.get("pbs_gc", {}).get(self._store, {})
        data = data if isinstance(data, dict) else {}
        payload_upid = data.get("upid")
        finished = data.get("last-run-endtime") is not None and bool(data.get("last-run-state"))
        use_payload = False
        if accepted:
            use_payload = payload_upid == accepted and finished
        elif finished:
            # The GC endpoint is the primary completed result. A newer task in
            # the list takes precedence only when its start can be compared.
            use_payload = task is None or task.get("upid") == payload_upid
            if task is not None and task.get("upid") != payload_upid:
                tasks = self.coordinator.data.get("pbs_tasks", [])
                previous = next((t for t in tasks if isinstance(t, dict)
                                 and t.get("upid") == payload_upid), None)
                previous_start = previous.get("starttime") if previous else None
                end, duration = data.get("last-run-endtime"), data.get("duration")
                if not _pbs_number(previous_start) and _pbs_number(end) and _pbs_number(duration) and 0 <= duration <= end:
                    previous_start = end - duration
                if _pbs_number(previous_start):
                    use_payload = previous_start > task["starttime"]
                else:
                    # No UPID timestamp parsing: retain the endpoint's completed
                    # result unless the list supplies an active execution.
                    use_payload = task.get("endtime") is not None
        if use_payload:
            same_task = task if task and task.get("upid") == payload_upid else {}
            task = {**same_task, "upid": payload_upid,
                    "status": data["last-run-state"], "endtime": data["last-run-endtime"]}
            task["_gc_payload"] = dict(data)
        task = _pbs_remember_terminal(self, accepted, task)
        return accepted, task

    def _get_value(self):
        accepted, task = self._execution()
        return _pbs_execution_state(task, accepted)

    @property
    def extra_state_attributes(self):
        accepted, task = self._execution()
        attrs = _pbs_execution_attributes(task, accepted)
        data = task.get("_gc_payload", {}) if task else {}
        fields = (
            "index-data-bytes", "index-file-count", "disk-bytes", "disk-chunks",
            "removed-bytes", "removed-chunks", "pending-bytes", "pending-chunks",
            "removed-bad", "still-bad",
        )
        attrs.update({key.replace("-", "_"): data[key]
                      for key in fields if data.get(key) is not None})
        for key, alias in (("index-data-bytes", "index_data_size"),
                           ("disk-bytes", "disk_size"),
                           ("removed-bytes", "removed_size"),
                           ("pending-bytes", "pending_size")):
            if _pbs_number(data.get(key)) and data[key] >= 0:
                attrs[alias] = _pbs_size(data[key])
        duration = data.get("duration")
        if _pbs_number(duration) and duration >= 0:
            attrs["duration_sec"] = duration
            attrs["duration_min"] = round(duration / 60, 2)
        for key, alias in (("pending-bytes", "pending_gb"), ("removed-bytes", "removed_gb")):
            if _pbs_number(data.get(key)):
                attrs[alias] = round(data[key] / (1024**3), 2)
        return attrs

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, pbs_device_identifier("maintenance", self._server_id, self._store))},
            "via_device_id": pbs_parent_device(self.coordinator),
            "name": f"Maintenance: {self._store}",
            "manufacturer": "Proxmox",
            "model": "Backup Server Maintenance",
        }


class ProxmoxPBSVerifySensor(ProxmoxPbsBaseSensor):
    """Sensor for PBS verify status."""

    def __init__(self, coordinator, server_id, store):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id=f"{store}_verify_status",
            name=None,
        )
        self._attr_translation_key = "pbs_verify_status"
        self._store = store
        self._attr_icon = "mdi:check-decagram"

    def _execution(self):
        accepted, task = _pbs_action_task(self, "verify")
        return accepted, _pbs_remember_terminal(self, accepted, task)

    def _get_value(self):
        accepted, task = self._execution()
        return _pbs_execution_state(task, accepted)

    @property
    def extra_state_attributes(self):
        accepted, task = self._execution()
        return _pbs_execution_attributes(task, accepted)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, pbs_device_identifier("maintenance", self._server_id, self._store))},
            "via_device_id": pbs_parent_device(self.coordinator),
            "name": f"Maintenance: {self._store}",
            "manufacturer": "Proxmox",
            "model": "Backup Server Maintenance",
        }


class ProxmoxPBSPruneSensor(ProxmoxPbsBaseSensor):
    """Sensor for PBS prune status."""

    def __init__(self, coordinator, server_id, store):
        super().__init__(
            coordinator=coordinator,
            server_id=server_id,
            sensor_id=f"{store}_prune_status",
            name=None,
        )
        self._attr_translation_key = "pbs_prune_status"
        self._store = store
        self._attr_icon = "mdi:delete-sweep"

    def _execution(self):
        accepted, task = _pbs_action_task(self, "prune")
        return accepted, _pbs_remember_terminal(self, accepted, task)

    def _get_value(self):
        accepted, task = self._execution()
        return _pbs_execution_state(task, accepted)

    @property
    def extra_state_attributes(self):
        accepted, task = self._execution()
        return _pbs_execution_attributes(task, accepted)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, pbs_device_identifier("maintenance", self._server_id, self._store))},
            "via_device_id": pbs_parent_device(self.coordinator),
            "name": f"Maintenance: {self._store}",
            "manufacturer": "Proxmox",
            "model": "Backup Server Maintenance",
        }
