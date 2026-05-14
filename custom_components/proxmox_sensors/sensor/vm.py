"""Virtual Machine sensors for Proxmox Extended Sensors."""

from .base import ProxmoxBaseSensor
from ..const import DOMAIN
from ..logic.guest_keys import make_guest_key


class ProxmoxVMSensor(ProxmoxBaseSensor):

    def __init__(self, coordinator, vm_id, node, label, guest_key=None):
        name = "Status"
        uid = f"proxmox_vm_{node}_{vm_id}_status_v1"
        self._label = label
        self._vm_id = vm_id
        self._guest_key = guest_key or make_guest_key(node, vm_id)
        super().__init__(coordinator, self._guest_key, name, None, uid, node)
        self._attr_icon = "mdi:monitor"

    @property
    def device_info(self):
        node_id = self._node.lower()
        vmid = str(self._vm_id)

        return {
            "identifiers": {(DOMAIN, f"proxmox_vm_{node_id}_{vmid}_v1")},
            "name": f"4. VM: {self._label}-({self._vm_id})",
            "via_device": (DOMAIN, f"proxmox_node_{node_id}"),
            "manufacturer": "Proxmox",
            "model": "QEMU Virtual Machine",
        }

    def _get_vm_data(self):
        vm_map = self.coordinator.data.get("vms", {})
        return (
            vm_map.get(self._guest_key)
            or vm_map.get(self._sensor_id)
            or vm_map.get(str(self._vm_id))
            or vm_map.get(self._vm_id)
            or {}
        )

    def _get_value(self):
        vm_data = self._get_vm_data()
        return str(vm_data.get("status", "unknown")).capitalize()


class ProxmoxVMAttributeSensor(ProxmoxBaseSensor):

    def __init__(
        self, coordinator, vm_id, node, label, attr_name, unit, icon, guest_key=None
    ):
        self._vm_id = vm_id
        self._label = label
        self._attr_key = attr_name
        self._guest_key = guest_key or make_guest_key(node, vm_id)

        display_name = attr_name.replace("_", " ").title()
        uid = f"proxmox_vm_{node}_{vm_id}_{attr_name.lower()}_v1"

        super().__init__(coordinator, self._guest_key, display_name, unit, uid, node)
        self._attr_icon = icon

    @property
    def device_info(self):
        node_id = self._node.lower()
        vmid = str(self._vm_id)

        return {
            "identifiers": {(DOMAIN, f"proxmox_vm_{node_id}_{vmid}_v1")},
            "name": f"4. VM: {self._label}-({self._vm_id})",
            "via_device": (DOMAIN, f"proxmox_node_{node_id}"),
            "manufacturer": "Proxmox",
            "model": "QEMU Virtual Machine",
        }

    def _get_vm_data(self):
        vm_map = self.coordinator.data.get("vms", {})
        return (
            vm_map.get(self._guest_key)
            or vm_map.get(self._sensor_id)
            or vm_map.get(str(self._vm_id))
            or vm_map.get(self._vm_id)
            or {}
        )

    def _get_value(self):
        vm_data = self._get_vm_data()
        if not vm_data:
            return None

        try:
            if self._attr_key == "cpu_usage":
                val = vm_data.get("cpu")
                return round(float(val) * 100, 2) if val is not None else None

            # Network GB
            if self._attr_key == "network_rx":
                val = vm_data.get("netin")
                return round(float(val) / (1024**3), 2) if val is not None else None

            if self._attr_key == "network_tx":
                val = vm_data.get("netout")
                return round(float(val) / (1024**3), 2) if val is not None else None

            keys = {
                "memory_used": "mem",
                "memory_total": "maxmem",
                "disk_used": "disk",
                "disk_total": "maxdisk",
                "uptime": "uptime",
            }

            api_key = keys.get(self._attr_key)
            val = vm_data.get(api_key)

            if val is None:
                return None

            if self._attr_key == "uptime":
                return round(float(val) / 3600, 1)

            return round(float(val) / (1024**3), 2)

        except (ValueError, TypeError):
            return None

    @property
    def extra_state_attributes(self):
        """Extra attributes for additional VM info."""
        vm_data = self._get_vm_data()

        if not vm_data:
            return {}

        attrs = {}

        # CPU extra info
        if self._attr_key == "cpu_usage":
            cpu = vm_data.get("cpu")
            cores = vm_data.get("cpus")

            if cores:
                attrs["cores"] = cores

                if cpu is not None:
                    try:
                        attrs["cpu_per_core"] = round(float(cpu) * 100 / cores, 2)
                    except (ValueError, TypeError, ZeroDivisionError):
                        pass

        return attrs
