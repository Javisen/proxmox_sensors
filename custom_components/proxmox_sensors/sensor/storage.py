"""Storage sensors for Proxmox storage pools."""

from .base import ProxmoxBaseSensor
from ..const import DOMAIN


class ProxmoxStorageSensor(ProxmoxBaseSensor):
    """Main storage usage sensor."""

    def __init__(self, coordinator, storage_name, st, node=None):
        uid = f"proxmox_storage_{node}_{storage_name}_percent_v1"
        super().__init__(coordinator, storage_name, "Usage", "%", uid, node)

        self._storage_name = storage_name
        self._attr_state_class = "measurement"

        stype = (st.get("type") or "").lower()

        if stype == "pbs":
            self._attr_icon = "mdi:database-sync"
        elif stype == "nfs":
            self._attr_icon = "mdi:nas"
        elif stype in ["lvm", "lvmthin"]:
            self._attr_icon = "mdi:harddisk"
        elif stype == "dir":
            self._attr_icon = "mdi:folder"
        elif stype == "zfspool":
            self._attr_icon = "mdi:database"
        elif stype in ["ceph", "rbd"]:
            self._attr_icon = "mdi:database-outline"
        else:
            self._attr_icon = "mdi:database"

    @property
    def device_info(self):
        node_id = (self._node or "node").lower()
        return {
            "identifiers": {
                (DOMAIN, f"proxmox_storage_{node_id}_{self._storage_name}")
            },
            "name": f"5. Storage: {self._storage_name}",
            "via_device": (DOMAIN, f"proxmox_node_{node_id}"),
            "manufacturer": "Proxmox",
            "model": "Storage Resource",
        }

    def _get_value(self):
        storage_data = self.coordinator.data.get("storage", {}).get(
            self._storage_name, {}
        )

        used = storage_data.get("used") or 0
        total = storage_data.get("total") or 0

        if total == 0:
            return 0

        return round((used / total) * 100, 2)


class ProxmoxStorageAttributeSensor(ProxmoxBaseSensor):
    """Additional sensors for storage attributes."""

    def __init__(self, coordinator, storage_name, st, label, key, node=None):
        uid = f"proxmox_storage_{node}_{storage_name}_{key}_v1"
        unit = "GB" if key in ("used", "avail", "total") else None

        super().__init__(coordinator, storage_name, label, unit, uid, node)

        self._storage_name = storage_name
        self._key = key

        stype = (st.get("type") or "").lower()

        if key == "type":

            if stype == "pbs":
                self._attr_icon = "mdi:database-sync"
            elif stype == "nfs":
                self._attr_icon = "mdi:nas"
            elif stype in ["lvm", "lvmthin"]:
                self._attr_icon = "mdi:harddisk"
            elif stype == "dir":
                self._attr_icon = "mdi:folder"
            elif stype == "zfspool":
                self._attr_icon = "mdi:database"
            elif stype in ["ceph", "rbd"]:
                self._attr_icon = "mdi:database-outline"
            else:
                self._attr_icon = "mdi:database"

        else:
            icon_map = {
                "used": "mdi:database-arrow-up",
                "avail": "mdi:database-arrow-down",
                "total": "mdi:database",
                "path": "mdi:folder-network",
            }

            self._attr_icon = icon_map.get(key, "mdi:information-outline")

        if key in ("used", "avail", "total"):
            self._attr_device_class = "data_size"
            self._attr_state_class = "measurement"

    @property
    def device_info(self):
        node_id = (self._node or "node").lower()
        return {
            "identifiers": {
                (DOMAIN, f"proxmox_storage_{node_id}_{self._storage_name}")
            },
            "name": f"5. Storage: {self._storage_name}",
        }

    def _get_value(self):
        storage_data = self.coordinator.data.get("storage", {}).get(
            self._storage_name, {}
        )

        value = storage_data.get(self._key)

        if value is None or value == "":
            return "Unknown" if not self.unit_of_measurement else 0

        if self._key in ("used", "avail", "total"):
            try:
                return round(float(value) / (1024**3), 2)
            except (ValueError, TypeError):
                return 0

        return str(value).capitalize() if self._key == "type" else value
