"""Base classes for Proxmox and PBS sensors."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from ..const import DOMAIN

# ============== BASE SENSOR FOR PVE ==========================


class ProxmoxBaseSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, sensor_id, name, unit, unique_id, node=None):
        super().__init__(coordinator)
        self._sensor_id = sensor_id
        self._node = node.lower() if node else "proxmox_server"
        if name is not None:
            self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        server_id = coordinator.config_entry.data.get("server_id", "default").lower()

        full_id = f"pve_{server_id}_{unique_id}"
        self._attr_unique_id = full_id.lower().replace(" ", "_")

    @property
    def native_value(self):
        try:
            return self._get_value()
        except Exception:
            return None

    def _get_value(self):
        raise NotImplementedError

    @property
    def device_info(self):
        node_id = self._node.lower()
        display_node = self._node.capitalize()

        return {
            "identifiers": {(DOMAIN, f"proxmox_node_{node_id}")},
            "name": f"1. Node: {display_node}",
            "manufacturer": "Proxmox",
            "model": "Proxmox Node",
        }

    def is_valid(self) -> bool:
        return self.native_value is not None


# ============ BASE SENSOR FOR PBS ===============


class ProxmoxPbsBaseSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self, coordinator, server_id: str, sensor_id: str, name: str, unit=None
    ):
        super().__init__(coordinator)
        self._server_id = server_id.lower()
        self._sensor_id = sensor_id
        if name is not None:
            self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        safe_id = (
            f"pbs_{self._server_id}_{sensor_id}".lower()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("-", "_")
        )

        self._attr_unique_id = safe_id

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"pbs_server_{self._server_id}")},
            "name": f"PBS Server {self._server_id.upper()}",
            "manufacturer": "Proxmox",
            "model": "Backup Server",
        }

    @property
    def native_value(self):
        try:
            return self._get_value()
        except Exception:
            return None

    def _get_value(self):
        raise NotImplementedError
