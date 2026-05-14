"""memory sensors for Proxmox Extended Sensors."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from ..const import DOMAIN
from .base import ProxmoxBaseSensor


class ProxmoxDimmSensor(ProxmoxBaseSensor):
    def __init__(self, coordinator, node, dimm_id):
        unique_id = f"proxmox_{node}_{dimm_id.lower()}"
        name = f"{dimm_id} ({node})"

        super().__init__(
            coordinator,
            dimm_id,
            name,
            "GB",
            unique_id,
            node,
        )

        self._dimm_id = dimm_id

        self._attr_icon = "mdi:memory"
        self._attr_state_class = "measurement"

    def _get_dimm(self):
        return (
            self.coordinator.data.get("memory", {})
            .get(self._node, {})
            .get("dimms", {})
            .get(self._dimm_id, {})
        )

    @property
    def native_value(self):
        dimm = self._get_dimm()
        if not dimm:
            return None

        size = dimm.get("size")  # Ej: "16 GB"
        if not size:
            return None

        # Convertir "16 GB" → 16
        if "GB" in size:
            return float(size.replace("GB", "").strip())
        if "MB" in size:
            return round(float(size.replace("MB", "").strip()) / 1024, 2)

        return None

    @property
    def extra_state_attributes(self):
        dimm = self._get_dimm()
        if not dimm:
            return {}

        return {
            "speed": dimm.get("speed"),  # Ej: "2666 MT/s"
            "configured_speed": dimm.get("configured_speed"),
            "type": dimm.get("type"),
            "manufacturer": dimm.get("manufacturer"),
            "locator": dimm.get("locator"),
        }
