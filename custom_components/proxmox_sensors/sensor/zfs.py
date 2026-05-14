"""ZFS sensors for Proxmox Extended Sensors."""

from .base import ProxmoxBaseSensor
from homeassistant.components.sensor import SensorStateClass


class ProxmoxZFSPoolSensor(ProxmoxBaseSensor):
    """Sensor for ZFS pool health."""

    def __init__(self, coordinator, node, pool_name):
        self._pool = pool_name
        self._node = node

        name = f"ZFS {pool_name} ({node})"
        unique_id = f"proxmox_zfs_{node}_{pool_name}"

        super().__init__(
            coordinator,
            sensor_id="zfs_health",
            name=name,
            unit=None,
            unique_id=unique_id,
            node=node,
        )

        self._attr_icon = "mdi:database"
        self._attr_state_class = None

    # ================= MAIN VALUE ==================

    def _get_value(self):
        zfs = self.coordinator.data.get("zfs_pools", {})
        pool = zfs.get(self._pool, {})

        health = pool.get("health")

        if not health:
            return "unknown"

        return health

    # ================= ATTRIBUTES ==================

    @property
    def extra_state_attributes(self):
        zfs = self.coordinator.data.get("zfs_pools", {})
        pool = zfs.get(self._pool, {})

        if not pool:
            return {}

        def _bytes_to_gb(value):
            try:
                return round(int(value) / (1024**3), 2)
            except Exception:
                return 0

        return {
            "pool": self._pool,
            "node": self._node,
            "health": pool.get("health"),
            "size_gb": _bytes_to_gb(pool.get("size")),
            "used_gb": _bytes_to_gb(pool.get("alloc")),
            "free_gb": _bytes_to_gb(pool.get("free")),
            "fragmentation": pool.get("frag"),
            "deduplication": pool.get("dedup"),
        }

    # ================= ICON DYNAMIC ==================

    @property
    def icon(self):
        zfs = self.coordinator.data.get("zfs_pools", {})
        pool = zfs.get(self._pool, {})
        health = pool.get("health", "").upper()

        if health == "ONLINE":
            return "mdi:check-circle"
        elif health == "DEGRADED":
            return "mdi:alert"
        elif health in ["FAULTED", "OFFLINE"]:
            return "mdi:close-circle"
        else:
            return "mdi:database"
