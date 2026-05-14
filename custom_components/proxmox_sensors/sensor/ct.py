"""Container (LXC) sensors for Proxmox Extended Sensors."""

from .base import ProxmoxBaseSensor
from ..const import DOMAIN
from ..logic.guest_keys import make_guest_key


class ProxmoxContainerSensor(ProxmoxBaseSensor):
    """Main CT status sensor."""

    def __init__(self, coordinator, ct_id, node, label, guest_key=None):
        self._label = label
        self._ct_id = ct_id
        self._guest_key = guest_key or make_guest_key(node, ct_id)
        uid = f"proxmox_ct_{node}_{ct_id}_status_v1"

        super().__init__(
            coordinator,
            self._guest_key,
            None,
            None,
            uid,
            node,
        )

        self._attr_translation_key = "ct_status"
        self._attr_icon = "mdi:label-outline"

    @property
    def device_info(self):
        node_id = self._node.lower()
        ctid = str(self._ct_id)

        return {
            "identifiers": {(DOMAIN, f"proxmox_ct_{node_id}_{ctid}_v1")},
            "name": f"3. CT: {self._label}-({ctid})",
            "via_device": (DOMAIN, f"proxmox_node_{node_id}"),
            "manufacturer": "Proxmox",
            "model": "LXC Container",
        }

    def _get_ct_data(self):
        ct_map = self.coordinator.data.get("cts", {})
        return (
            ct_map.get(self._guest_key)
            or ct_map.get(self._sensor_id)
            or ct_map.get(str(self._ct_id))
            or ct_map.get(self._ct_id)
            or {}
        )

    def _get_value(self):
        ct_data = self._get_ct_data()
        return str(ct_data.get("status", "unknown")).capitalize()


class ProxmoxContainerAttributeSensor(ProxmoxBaseSensor):
    """Attribute sensors for CTs (CPU, memory, disk, network, uptime)."""

    def __init__(
        self, coordinator, ct_id, node, label, attr_name, unit, icon, guest_key=None
    ):
        self._label = label
        self._ct_id = ct_id
        self._guest_key = guest_key or make_guest_key(node, ct_id)
        self._attr_key = attr_name

        uid = f"proxmox_ct_{node}_{ct_id}_{attr_name}_v1"

        names = {
            "cpu_usage": "CPU Usage",
            "memory_used": "RAM Used",
            "memory_total": "RAM Total",
            "disk_used": "Disk Used",
            "disk_total": "Disk Total",
            "network_rx": "Network RX",
            "network_tx": "Network TX",
            "uptime": "Uptime",
        }

        pretty = names.get(attr_name, attr_name.replace("_", " ").title())
        name = pretty

        super().__init__(
            coordinator,
            self._guest_key,
            name,
            unit,
            uid,
            node,
        )

        self._attr_translation_key = f"ct_{attr_name}"
        self._attr_icon = icon

    @property
    def device_info(self):
        node_id = self._node.lower()
        ctid = str(self._ct_id)

        return {
            "identifiers": {(DOMAIN, f"proxmox_ct_{node_id}_{ctid}_v1")},
            "name": f"3. CT: {self._label}-({ctid})",
            "via_device": (DOMAIN, f"proxmox_node_{node_id}"),
            "manufacturer": "Proxmox",
            "model": "LXC Container",
        }

    def _get_ct_data(self):
        ct_map = self.coordinator.data.get("cts", {})
        return (
            ct_map.get(self._guest_key)
            or ct_map.get(self._sensor_id)
            or ct_map.get(str(self._ct_id))
            or ct_map.get(self._ct_id)
            or {}
        )

    def _get_value(self):
        ct_data = self._get_ct_data()
        if not ct_data:
            return None

        try:
            # CPU %
            if self._attr_key == "cpu_usage":
                cpu = ct_data.get("cpu")
                return round(float(cpu) * 100, 2) if cpu is not None else None

            # Network GB
            if self._attr_key == "network_rx":
                val = ct_data.get("netin")
                return round(float(val) / (1024**3), 2) if val is not None else None

            if self._attr_key == "network_tx":
                val = ct_data.get("netout")
                return round(float(val) / (1024**3), 2) if val is not None else None

            keys = {
                "memory_used": "mem",
                "memory_total": "maxmem",
                "disk_used": "disk",
                "disk_total": "maxdisk",
                "uptime": "uptime",
            }

            api_key = keys.get(self._attr_key)
            val = ct_data.get(api_key)

            if val is None:
                return None

            if self._attr_key == "uptime":
                return round(float(val) / 3600, 1)

            return round(float(val) / (1024**3), 2)

        except (ValueError, TypeError):
            return None

    @property
    def extra_state_attributes(self):
        """Extra attributes for additional CT info."""
        ct_data = self._get_ct_data()

        if not ct_data:
            return {}

        attrs = {}

        # CPU extra info
        if self._attr_key == "cpu_usage":
            cpu = ct_data.get("cpu")
            cores = ct_data.get("cpus")

            if cores:
                attrs["cores"] = cores

                if cpu is not None:
                    try:
                        attrs["cpu_per_core"] = round(float(cpu) * 100 / cores, 2)
                    except (ValueError, TypeError, ZeroDivisionError):
                        pass

        return attrs
