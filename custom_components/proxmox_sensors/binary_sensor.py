"""Binary sensors for Proxmox Extended Sensors."""

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)


class ProxmoxNodeOverloadedBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor to detect if node is overloaded."""

    def __init__(self, coordinator, node, entry_id):
        super().__init__(coordinator)
        self._node = node
        self._entry_id = entry_id

        self._attr_name = f"{node} Overloaded"
        self._attr_unique_id = f"{entry_id}_node_overloaded_{node}"
        self._attr_icon = "mdi:alert-circle"

    @property
    def is_on(self):
        data = self.coordinator.data
        node_data = data.get("node", {})

        cpu = node_data.get("cpu", 0)
        memory = node_data.get("memory", {})

        mem_used = memory.get("used", 0)
        mem_total = memory.get("total", 1)

        cpu_percent = cpu * 100 if isinstance(cpu, (int, float)) else 0
        mem_percent = (mem_used / mem_total) * 100 if mem_total > 0 else 0

        active_tasks = sum(
            1
            for task in data.get("tasks", [])
            if task.get("node") == self._node
            and task.get("status") not in ["OK", "stopped"]
        )

        return cpu_percent > 85 or mem_percent > 90 or active_tasks > 5

    @property
    def icon(self):
        return "mdi:alert-circle" if self.is_on else "mdi:check-circle"

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        node_data = data.get("node", {})

        cpu = node_data.get("cpu", 0)
        memory = node_data.get("memory", {})

        mem_used = memory.get("used", 0)
        mem_total = memory.get("total", 1)

        cpu_percent = cpu * 100 if isinstance(cpu, (int, float)) else 0
        mem_percent = (mem_used / mem_total) * 100 if mem_total > 0 else 0

        active_tasks = sum(
            1
            for task in data.get("tasks", [])
            if task.get("node") == self._node
            and task.get("status") not in ["OK", "stopped"]
        )

        reason = []
        if cpu_percent > 85:
            reason.append("CPU high")
        if mem_percent > 90:
            reason.append("RAM high")
        if active_tasks > 5:
            reason.append("Many tasks")

        return {
            "cpu": round(cpu_percent, 2),
            "memory": round(mem_percent, 2),
            "active_tasks": active_tasks,
            "reason": ", ".join(reason) if reason else "OK",
        }


class ProxmoxNodeDiskOverloadedBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for disk pressure based on IO wait."""

    def __init__(self, coordinator, node, entry_id):
        super().__init__(coordinator)
        self._node = node
        self._entry_id = entry_id

        self._attr_name = f"{node} Disk Overloaded"
        self._attr_unique_id = f"{entry_id}_node_disk_overloaded_{node}"
        self._attr_device_class = "problem"

    @property
    def is_on(self):
        wait = self.coordinator.data.get("node", {}).get("wait", 0)
        percent = wait * 100 if isinstance(wait, (int, float)) else 0
        return percent > 10

    @property
    def icon(self):
        return "mdi:alert-circle" if self.is_on else "mdi:harddisk"

    @property
    def extra_state_attributes(self):
        wait = self.coordinator.data.get("node", {}).get("wait", 0)
        percent = wait * 100 if isinstance(wait, (int, float)) else 0
        return {
            "io_wait_percent": round(percent, 2),
            "threshold": 10,
            "status": "High IO Wait" if percent > 10 else "Normal",
        }


class ProxmoxNodeStressedBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for overall node stress (CPU + IO + Load)."""

    def __init__(self, coordinator, node, entry_id):
        super().__init__(coordinator)
        self._node = node
        self._entry_id = entry_id

        self._attr_name = f"{node} Stressed"
        self._attr_unique_id = f"{entry_id}_node_stressed_{node}"
        self._attr_device_class = "problem"

    def _get_metrics(self):
        data = self.coordinator.data.get("node", {})

        cpu = data.get("cpu", 0)
        wait = data.get("wait", 0)
        load = data.get("loadavg", [])
        cpuinfo = data.get("cpuinfo", {})

        cpu_percent = cpu * 100 if isinstance(cpu, (int, float)) else 0
        io_wait = wait * 100 if isinstance(wait, (int, float)) else 0

        try:
            load1 = float(load[0]) if len(load) > 0 else 0
        except Exception:
            load1 = 0

        cores = cpuinfo.get("cores") or cpuinfo.get("cpus") or 1

        return cpu_percent, io_wait, load1, cores

    @property
    def is_on(self):
        cpu, io_wait, load1, cores = self._get_metrics()
        return cpu > 85 or io_wait > 10 or load1 > cores

    @property
    def extra_state_attributes(self):
        cpu, io_wait, load1, cores = self._get_metrics()
        return {
            "cpu": round(cpu, 2),
            "io_wait": round(io_wait, 2),
            "load_1m": round(load1, 2),
            "cores": cores,
            "load_ratio": round(load1 / cores, 2) if cores else None,
        }


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Proxmox binary sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []

    node = entry.data.get("node")
    server_type = entry.data.get("platform_type", "PVE")

    if node and server_type == "PVE":
        entities.append(
            ProxmoxNodeOverloadedBinarySensor(coordinator, node, entry.entry_id)
        )
        entities.append(
            ProxmoxNodeDiskOverloadedBinarySensor(coordinator, node, entry.entry_id)
        )
        entities.append(
            ProxmoxNodeStressedBinarySensor(coordinator, node, entry.entry_id)
        )

    async_add_entities(entities)
