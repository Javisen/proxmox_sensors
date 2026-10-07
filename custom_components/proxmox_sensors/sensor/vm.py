"""Virtual Machine sensors for Proxmox Extended Sensors."""

import logging
from math import isfinite

from homeassistant.components.sensor import SensorStateClass
from homeassistant.helpers import device_registry as dr

from .base import ProxmoxBaseSensor
from .replication import GuestReplicationMixin
from ..const import DOMAIN
from ..logic.guest_keys import make_guest_key
from ..logic.guest_identity import guest_device_identifier, sensor_unique_id
from ..logic.pve_local_identity import (
    coordinator_pve_local_identity_context,
    node_device_identifier,
)

_LOGGER = logging.getLogger(__name__)


class ProxmoxVMSensor(GuestReplicationMixin, ProxmoxBaseSensor):

    def __init__(self, coordinator, vm_id, node, label, guest_key=None, cluster_id=None, identity_context=None):
        self._label = label
        self._vm_id = vm_id
        self._guest_key = guest_key or make_guest_key(node, vm_id)
        self._cluster_id = str(cluster_id).lower() if cluster_id else None
        self._identity_context = identity_context

        scoped = bool(identity_context and identity_context.use_scoped_identity)
        if scoped:
            uid = sensor_unique_id(identity_context.scope, "vm", vm_id)
            id_scope = None
        elif self._cluster_id:
            # Node-independent identity: survives live migrations.
            uid = f"proxmox_vm_{self._cluster_id}_{vm_id}_status_v1"
            id_scope = f"cluster_{self._cluster_id}"
        else:
            uid = f"proxmox_vm_{node}_{vm_id}_status_v1"
            id_scope = None

        super().__init__(
            coordinator, self._guest_key, None, None, uid, node, id_scope=id_scope,
            full_unique_id=uid if scoped else None,
        )
        self._attr_translation_key = "vm_status"
        self._attr_icon = "mdi:monitor"

    @property
    def device_info(self):
        node_id = self._node.lower()
        vmid = str(self._vm_id)
        local_identity = coordinator_pve_local_identity_context(self.coordinator)

        if self._identity_context and self._identity_context.use_scoped_identity:
            identifiers = {(DOMAIN, guest_device_identifier(self._identity_context.scope, "vm", vmid))}
        elif self._cluster_id:
            identifiers = {(DOMAIN, f"proxmox_vm_cluster_{self._cluster_id}_{vmid}_v1")}
        else:
            identifiers = {(DOMAIN, f"proxmox_vm_{node_id}_{vmid}_v1")}

        info = {
            "identifiers": identifiers,
            "name": f"4. VM: {self._label}-({self._vm_id})",
            "manufacturer": "Proxmox",
            "model": "QEMU Virtual Machine",
        }

        try:
            info["via_device_id"] = dr.async_get_device_id_by_identifier(
                self.coordinator.hass,
                (DOMAIN, node_device_identifier(local_identity, node_id)),
                config_entry_id=self.coordinator.config_entry.entry_id,
            )
        except ValueError:
            _LOGGER.debug(
                "Parent node device %s not found in config entry %s; omitting via_device_id",
                node_id,
                self.coordinator.config_entry.entry_id,
            )
        return info

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

    @property
    def extra_state_attributes(self):
        """Extra attributes for the VM status sensor."""
        vm_data = self._get_vm_data()

        if not vm_data:
            return self._replication_attributes()

        attrs = self._replication_attributes()

        if node := vm_data.get("node"):
            attrs["node"] = node

        onboot = bool(vm_data.get("onboot", False))
        attrs["onboot"] = onboot

        expected_state = "running" if onboot else None
        attrs["expected_state"] = expected_state

        if expected_state is not None:
            actual_state = str(vm_data.get("status", "")).lower()
            attrs["state_matches_onboot"] = actual_state == expected_state
        else:
            attrs["state_matches_onboot"] = None

        return attrs
    
class ProxmoxVMAttributeSensor(ProxmoxBaseSensor):

    def __init__(
        self,
        coordinator,
        vm_id,
        node,
        label,
        attr_name,
        unit,
        icon,
        guest_key=None,
        cluster_id=None,
        identity_context=None,
    ):
        self._vm_id = vm_id
        self._label = label
        self._attr_key = attr_name
        self._guest_key = guest_key or make_guest_key(node, vm_id)
        self._cluster_id = str(cluster_id).lower() if cluster_id else None
        self._identity_context = identity_context

        scoped = bool(identity_context and identity_context.use_scoped_identity)
        if scoped:
            uid = sensor_unique_id(identity_context.scope, "vm", vm_id, attr_name.lower())
            id_scope = None
        elif self._cluster_id:
            uid = f"proxmox_vm_{self._cluster_id}_{vm_id}_{attr_name.lower()}_v1"
            id_scope = f"cluster_{self._cluster_id}"
        else:
            uid = f"proxmox_vm_{node}_{vm_id}_{attr_name.lower()}_v1"
            id_scope = None

        super().__init__(
            coordinator, self._guest_key, None, unit, uid, node, id_scope=id_scope,
            full_unique_id=uid if scoped else None,
        )
        self._attr_translation_key = f"vm_{attr_name}"
        self._attr_icon = icon
        if attr_name in ("cpu_usage", "memory_used", "memory_total", "disk_total", "uptime"):
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def device_info(self):
        node_id = self._node.lower()
        vmid = str(self._vm_id)
        local_identity = coordinator_pve_local_identity_context(self.coordinator)

        if self._identity_context and self._identity_context.use_scoped_identity:
            identifiers = {(DOMAIN, guest_device_identifier(self._identity_context.scope, "vm", vmid))}
        elif self._cluster_id:
            identifiers = {(DOMAIN, f"proxmox_vm_cluster_{self._cluster_id}_{vmid}_v1")}
        else:
            identifiers = {(DOMAIN, f"proxmox_vm_{node_id}_{vmid}_v1")}

        info = {
            "identifiers": identifiers,
            "name": f"4. VM: {self._label}-({self._vm_id})",
            "manufacturer": "Proxmox",
            "model": "QEMU Virtual Machine",
        }

        try:
            info["via_device_id"] = dr.async_get_device_id_by_identifier(
                self.coordinator.hass,
                (DOMAIN, node_device_identifier(local_identity, node_id)),
                config_entry_id=self.coordinator.config_entry.entry_id,
            )
        except ValueError:
            _LOGGER.debug(
                "Parent node device %s not found in config entry %s; omitting via_device_id",
                node_id,
                self.coordinator.config_entry.entry_id,
            )
        return info

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

        attrs = {}
        if self._attr_key == "memory_used":
            attrs["usage_percent"] = None
            used_key, total_key = ("mem", "maxmem")
            used = vm_data.get(used_key)
            total = vm_data.get(total_key)
            if not isinstance(used, bool) and not isinstance(total, bool):
                try:
                    used = float(used)
                    total = float(total)
                    if isfinite(used) and isfinite(total) and used >= 0 and total > 0:
                        percent = used / total * 100
                        if isfinite(percent):
                            attrs["usage_percent"] = round(percent, 2)
                except (TypeError, ValueError, OverflowError):
                    pass
             
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


class ProxmoxVMDiskUsageSensor(ProxmoxVMAttributeSensor):
    """Linux root filesystem usage reported by QEMU Guest Agent."""

    def __init__(
        self,
        coordinator,
        vm_id,
        node,
        label,
        guest_key=None,
        cluster_id=None,
        identity_context=None,
    ):
        super().__init__(
            coordinator,
            vm_id,
            node,
            label,
            "disk_usage",
            "%",
            "mdi:chart-donut",
            guest_key=guest_key,
            cluster_id=cluster_id,
            identity_context=identity_context,
        )
        self._attr_state_class = SensorStateClass.MEASUREMENT

    def _get_disk_usage_data(self):
        data = self.coordinator.data or {}
        metrics = data.get("guest_agent_disk_usage", {})
        return metrics.get(self._guest_key)

    def _get_value(self):
        metrics = self._get_disk_usage_data()
        return metrics.get("usage") if isinstance(metrics, dict) else None

    @property
    def available(self):
        return super().available and isinstance(self._get_disk_usage_data(), dict)

    @property
    def extra_state_attributes(self):
        metrics = self._get_disk_usage_data()
        if not isinstance(metrics, dict):
            return {}
        return {
            "total": metrics.get("total"),
            "used": metrics.get("used"),
            "free": metrics.get("free"),
            "filesystem_type": metrics.get("filesystem_type"),
            "additional_filesystems": metrics.get("additional_filesystems", []),
        }
