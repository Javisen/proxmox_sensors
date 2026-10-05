"""Base classes for Proxmox and PBS sensors."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from ..const import DOMAIN
from ..logic.pve_local_identity import (
    coordinator_pve_local_identity_context,
    local_entity_unique_id,
    node_device_identifier,
)


def same_node(first, second):
    """Compare two non-empty PVE node names without regard to case."""
    if not isinstance(first, str) or not isinstance(second, str):
        return False
    if not first.strip() or not second.strip():
        return False
    return first.casefold() == second.casefold()


def node_section(data, section, node):
    """Return one unambiguous node-keyed coordinator section."""
    if not isinstance(data, dict):
        return {}
    nodes = data.get(section) or {}
    if not isinstance(nodes, dict) or not isinstance(node, str) or not node.strip():
        return {}
    if node in nodes:
        value = nodes[node]
        return value if isinstance(value, dict) else {}
    matches = [value for key, value in nodes.items() if same_node(key, node)]
    if len(matches) != 1:
        return {}
    return matches[0] if isinstance(matches[0], dict) else {}


# ============== BASE SENSOR FOR PVE ==========================


class ProxmoxBaseSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self, coordinator, sensor_id, name, unit, unique_id, node=None, id_scope=None,
        full_unique_id=None,
    ):
        super().__init__(coordinator)
        self._sensor_id = sensor_id
        self._node = node.lower() if node else "proxmox_server"
        if name is not None:
            self._attr_name = name
        self._attr_native_unit_of_measurement = unit

        if full_unique_id is not None:
            full_id = full_unique_id
        elif id_scope:
            full_id = f"pve_{id_scope}_{unique_id}"
        else:
            server_id = coordinator.config_entry.data.get(
                "server_id", "default"
            ).lower()
            full_id = local_entity_unique_id(
                coordinator_pve_local_identity_context(coordinator),
                server_id,
                unique_id,
            )

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
            "identifiers": {(
                DOMAIN,
                node_device_identifier(
                    coordinator_pve_local_identity_context(self.coordinator),
                    node_id,
                ),
            )},
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
