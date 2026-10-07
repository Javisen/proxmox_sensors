"""PDM aggregate and remote overview sensors."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from math import isfinite

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from ..logic.pdm import (
    pdm_remote_identifier,
    pdm_root_identifier,
    pdm_unique_id,
    is_owned_orphan_pdm_remote_device,
)

_LOGGER = logging.getLogger(__name__)

_GIB = 1024 ** 3


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if isfinite(value) else None


def _counter(value):
    value = _number(value)
    if value is None or not float(value).is_integer():
        return None
    return int(value)


def _gib(value):
    value = _number(value)
    return round(value / _GIB, 2) if value is not None else None


def _percent(value):
    value = _number(value)
    return round(value * 100, 2) if value is not None else None


def _rounded_number(value):
    value = _number(value)
    if value is None:
        return None
    return int(value) if float(value).is_integer() else round(value, 2)


def _used_percent(used, total):
    used = _number(used)
    total = _number(total)
    if used is None or total is None or total <= 0:
        return None
    return round(used / total * 100, 2)


def _present_counts(value):
    if not isinstance(value, dict):
        return None
    return {key: _counter(count) for key, count in value.items()}


def _present_capacity_section(value, kind):
    if not isinstance(value, dict):
        return None
    if kind == "cpu":
        used = _number(value.get("used"))
        maximum = _number(value.get("max"))
        result = {
            "used_threads": _rounded_number(used),
            "max_threads": _rounded_number(maximum),
            "used_percent": _used_percent(used, maximum),
        }
        if "allocated" in value:
            result["allocated_cores"] = _rounded_number(value.get("allocated"))
        return result
    result = {}
    for key, item in value.items():
        if key == "usage":
            result["used_percent"] = _percent(item)
        elif kind in ("memory", "storage") and key in (
            "used",
            "total",
            "avail",
            "available",
            "free",
        ):
            result[f"{key}_gib"] = _gib(item)
        elif key == "count":
            result[key] = _counter(item)
        else:
            result[key] = item
    if kind in ("memory", "storage"):
        calculated = _used_percent(value.get("used"), value.get("total"))
        if calculated is not None or "used_percent" not in result:
            result["used_percent"] = calculated
    return result


def _present_remote_capacity(value):
    if not isinstance(value, dict):
        return None
    maximum = _number(value.get("cpu_cores"))
    used_percent = _number(value.get("cpu_usage_percent"))
    used = (
        maximum * used_percent / 100
        if maximum is not None and used_percent is not None
        else None
    )
    return {
        "used_threads": _rounded_number(used),
        "max_threads": _rounded_number(maximum),
        "used_percent": round(used_percent, 2) if used_percent is not None else None,
        "memory_used_gib": _gib(value.get("memory_used")),
        "memory_total_gib": _gib(value.get("memory_total")),
        "memory_used_percent": _number(value.get("memory_usage_percent")),
        "storage_used_gib": _gib(value.get("storage_used")),
        "storage_total_gib": _gib(value.get("storage_total")),
        "storage_used_percent": _number(value.get("storage_usage_percent")),
    }


def _timestamp(value):
    value = _counter(value)
    if value is None or value <= 0:
        return None
    try:
        return datetime.fromtimestamp(value, timezone.utc).isoformat(timespec="seconds")
    except (OverflowError, OSError, ValueError):
        return None


def _duration(value):
    value = _counter(value)
    if value is None or value < 0:
        return None
    days, remainder = divmod(value, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def _present_updates_remotes(value):
    if not isinstance(value, dict):
        return None
    remotes = {}
    for remote_id, remote in value.items():
        if not isinstance(remote, dict):
            remotes[remote_id] = None
            continue
        nodes = remote.get("nodes")
        presented_nodes = None
        if isinstance(nodes, dict):
            presented_nodes = {}
            for node_id, node in nodes.items():
                if not isinstance(node, dict):
                    presented_nodes[node_id] = None
                    continue
                presented_nodes[node_id] = {
                    "status": node.get("status"),
                    "repository_status": node.get("repository_status"),
                    "number_of_updates": _counter(node.get("number_of_updates")),
                    "last_refresh": _timestamp(node.get("last_refresh")),
                    "versions": node.get("versions"),
                }
        remotes[remote_id] = {
            "remote_type": remote.get("remote_type"),
            "status": remote.get("status"),
            "nodes": presented_nodes,
        }
    return remotes


def _pdm_root_device_info(coordinator, scope):
    version = (coordinator.data or {}).get("pdm_version", {})
    release = version.get("release")
    sw_version = version.get("version")
    if sw_version and release is not None:
        sw_version = f"{sw_version}-{release}"
    return {
        "identifiers": {(DOMAIN, pdm_root_identifier(scope))},
        "manufacturer": "Proxmox",
        "model": "Proxmox Datacenter Manager",
        "name": getattr(
            coordinator,
            "pdm_display_name",
            "Proxmox Datacenter Manager",
        ),
        "sw_version": sw_version,
    }


class PDMBaseSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, scope, metric):
        super().__init__(coordinator)
        self._scope = scope
        self._attr_unique_id = pdm_unique_id(scope, metric)

    @property
    def device_info(self):
        return _pdm_root_device_info(self.coordinator, self._scope)


class PDMStatusSensor(PDMBaseSensor):
    _attr_translation_key = "pdm_status"
    _attr_icon = "mdi:server-network"

    def __init__(self, coordinator, scope):
        super().__init__(coordinator, scope, "status")

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        status = data.get("pdm_status", {})
        remotes = data.get("pdm_remotes", {})
        failed = status.get("failed_remotes")
        healthy = failed == 0 and all(
            str(remote.get("status", "")).casefold() == "good"
            for remote in remotes.values()
        )
        return "Good" if healthy else "Degraded"

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        remotes = data.get("pdm_remotes")
        has_remotes = isinstance(remotes, dict)
        remotes = remotes if has_remotes else {}
        return {
            "remotes": int(len(remotes)) if has_remotes else None,
            "pve_remotes": (
                int(sum(remote.get("type") == "pve" for remote in remotes.values()))
                if has_remotes
                else None
            ),
            "pbs_remotes": (
                int(sum(remote.get("type") == "pbs" for remote in remotes.values()))
                if has_remotes
                else None
            ),
            "failed_remotes": _counter(data.get("pdm_status", {}).get("failed_remotes")),
            "sections_fresh": data.get("pdm_sections_ok", {}),
        }


class PDMInventorySensor(PDMBaseSensor):
    _attr_translation_key = "pdm_inventory"
    _attr_icon = "mdi:view-dashboard-outline"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, scope):
        super().__init__(coordinator, scope, "inventory")

    @property
    def native_value(self):
        status = (self.coordinator.data or {}).get("pdm_status", {})
        sections = [status.get("pve_nodes"), status.get("pbs_nodes")]
        values = [
            count
            for section in sections
            if isinstance(section, dict)
            for value in section.values()
            if (count := _counter(value)) is not None
        ]
        return sum(values) if values else None

    @property
    def extra_state_attributes(self):
        status = (self.coordinator.data or {}).get("pdm_status", {})
        return {
            key: _present_counts(status.get(key))
            for key in (
                "pve_nodes",
                "pbs_nodes",
                "qemu",
                "lxc",
                "storages",
                "pbs_datastores",
                "sdn_zones",
            )
        }


class PDMCapacitySensor(PDMBaseSensor):
    _attr_translation_key = "pdm_capacity"
    _attr_icon = "mdi:database"
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, scope):
        super().__init__(coordinator, scope, "capacity")

    @property
    def native_value(self):
        status = (self.coordinator.data or {}).get("pdm_status", {})
        sections = [status.get("pve_storage_stats"), status.get("pbs_storage_stats")]
        sections = [section for section in sections if isinstance(section, dict)]
        pairs = [
            (used, total)
            for section in sections
            if (used := _number(section.get("used"))) is not None
            and (total := _number(section.get("total"))) is not None
        ]
        used = sum(pair[0] for pair in pairs)
        total = sum(pair[1] for pair in pairs)
        return round(used / total * 100, 2) if pairs and total > 0 else None

    @property
    def extra_state_attributes(self):
        status = (self.coordinator.data or {}).get("pdm_status", {})
        return {
            "pve_cpu_stats": _present_capacity_section(
                status.get("pve_cpu_stats"), "cpu"
            ),
            "pve_memory_stats": _present_capacity_section(
                status.get("pve_memory_stats"), "memory"
            ),
            "pve_storage_stats": _present_capacity_section(
                status.get("pve_storage_stats"), "storage"
            ),
            "pbs_cpu_stats": _present_capacity_section(
                status.get("pbs_cpu_stats"), "cpu"
            ),
            "pbs_memory_stats": _present_capacity_section(
                status.get("pbs_memory_stats"), "memory"
            ),
            "pbs_storage_stats": _present_capacity_section(
                status.get("pbs_storage_stats"), "storage"
            ),
        }


class PDMUpdatesSensor(PDMBaseSensor):
    _attr_translation_key = "pdm_updates"
    _attr_icon = "mdi:package-up"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, scope):
        super().__init__(coordinator, scope, "updates")

    @property
    def available(self):
        sections = (self.coordinator.data or {}).get("pdm_sections_available", {})
        return super().available and sections.get("updates") is True

    @property
    def native_value(self):
        updates = (self.coordinator.data or {}).get("pdm_updates") or {}
        return updates.get("total_updates")

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        updates = data.get("pdm_updates") or {}
        oldest = updates.get("oldest_last_refresh")
        age_seconds = None
        if isinstance(oldest, int) and not isinstance(oldest, bool):
            age_seconds = max(0, int(time.time()) - oldest)
        return {
            "remotes": _present_updates_remotes(updates.get("remotes")),
            "oldest_last_refresh": _timestamp(oldest),
            "newest_last_refresh": _timestamp(updates.get("newest_last_refresh")),
            "oldest_refresh_age": _duration(age_seconds),
            "endpoint_fresh": data.get("pdm_sections_ok", {}).get("updates", False),
            "snapshot_complete": data.get("pdm_updates_snapshot_complete", False),
        }


class PDMRemoteBaseSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, scope, remote_id, metric, root_device_id):
        super().__init__(coordinator)
        self._scope = scope
        self._remote_id = remote_id
        self._root_device_id = root_device_id
        self._attr_unique_id = pdm_unique_id(scope, metric, remote_id)

    def _remote(self):
        return (self.coordinator.data or {}).get("pdm_remotes", {}).get(self._remote_id, {})

    @property
    def device_info(self):
        remote = self._remote()
        remote_type = str(remote.get("type") or "").upper()
        return {
            "identifiers": {(DOMAIN, pdm_remote_identifier(self._scope, self._remote_id))},
            "manufacturer": "Proxmox",
            "model": f"PDM {remote_type} Remote" if remote_type else "PDM Remote",
            "name": f"PDM Remote: {self._remote_id}",
            "via_device_id": self._root_device_id,
        }


class PDMRemoteStatusSensor(PDMRemoteBaseSensor):
    _attr_translation_key = "pdm_remote_status"
    _attr_icon = "mdi:lan-connect"

    def __init__(self, coordinator, scope, remote_id, root_device_id):
        super().__init__(coordinator, scope, remote_id, "status", root_device_id)

    @property
    def native_value(self):
        return self._remote().get("status") or "Unknown"

    @property
    def extra_state_attributes(self):
        remote = self._remote()
        return {
            "remote_type": remote.get("type"),
            "subscription": remote.get("subscription"),
            "status_fresh": (self.coordinator.data or {}).get("pdm_sections_ok", {}).get("status", False),
        }


class PDMRemoteOverviewSensor(PDMRemoteBaseSensor):
    _attr_translation_key = "pdm_remote_overview"
    _attr_icon = "mdi:chart-box-outline"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, scope, remote_id, root_device_id):
        super().__init__(coordinator, scope, remote_id, "overview", root_device_id)

    @property
    def native_value(self):
        return self._remote().get("inventory", {}).get("total_resources")

    @property
    def available(self):
        sections = (self.coordinator.data or {}).get("pdm_sections_available", {})
        return super().available and sections.get("resources") is True

    @property
    def extra_state_attributes(self):
        remote = self._remote()
        return {
            "inventory": _present_counts(remote.get("inventory")),
            "capacity": _present_remote_capacity(remote.get("capacity")),
            "resources_fresh": (self.coordinator.data or {}).get("pdm_sections_ok", {}).get("resources", False),
        }


def setup_pdm_sensors(hass, coordinator, entry, async_add_entities):
    scope = entry.data["pdm_identity_id"]
    registry = er.async_get(hass)
    devices = dr.async_get(hass)
    root_device = devices.async_get_or_create(
        config_entry_id=entry.entry_id,
        **_pdm_root_device_info(coordinator, scope),
    )
    remote_unique_id_prefix = f"pdm_{scope}_remote_"
    instances = {}
    removing = {}
    async_add_entities([
        PDMStatusSensor(coordinator, scope),
        PDMInventorySensor(coordinator, scope),
        PDMCapacitySensor(coordinator, scope),
        PDMUpdatesSensor(coordinator, scope),
    ])

    def cleanup_orphan_remote_devices(current_remote_ids):
        root = devices.async_get_device_by_identifier(
            (DOMAIN, pdm_root_identifier(scope)), config_entry_id=entry.entry_id
        )
        if root is None:
            return
        expected_identifiers = {
            (DOMAIN, pdm_remote_identifier(scope, remote_id))
            for remote_id in current_remote_ids
        }
        for device in list(dr.async_entries_for_config_entry(devices, entry.entry_id)):
            if not is_owned_orphan_pdm_remote_device(
                device,
                entry.entry_id,
                scope,
                root.id,
                expected_identifiers,
            ):
                continue
            if er.async_entries_for_device(
                registry, device.id, include_disabled_entities=True
            ):
                continue
            if dr.async_entries_for_parent_device(devices, device.id):
                continue
            if any(
                other.id != device.id and other.via_device_id == device.id
                for other in devices.async_get_devices()
            ):
                continue
            devices.async_remove_device(device.id)

    async def remove_remote(remote_id, entities):
        completed = False
        try:
            data = coordinator.data or {}
            current = data.get("pdm_remotes", {})
            if (
                data.get("pdm_sections_ok", {}).get("remotes") is not True
                or not isinstance(current, dict)
                or remote_id in current
            ):
                return
            for entity in entities:
                if getattr(entity, "hass", None) is not None:
                    await entity.async_remove(force_remove=True)
                entity_id = registry.async_get_entity_id("sensor", DOMAIN, entity.unique_id)
                row = registry.async_get(entity_id) if entity_id else None
                if row is not None and row.config_entry_id == entry.entry_id:
                    registry.async_remove(row.entity_id)
            cleanup_orphan_remote_devices(current)
            completed = True
        except Exception:
            _LOGGER.exception("Failed to remove PDM remote %s entities", remote_id)
        finally:
            if completed and instances.get(remote_id) is entities:
                instances.pop(remote_id, None)
            removing.pop(remote_id, None)
            reconcile()

    @callback
    def reconcile():
        data = coordinator.data or {}
        if data.get("pdm_sections_ok", {}).get("remotes") is not True:
            return
        current = data.get("pdm_remotes", {})
        if not isinstance(current, dict):
            return
        expected_unique_ids = {
            pdm_unique_id(scope, metric, remote_id)
            for remote_id in current
            for metric in ("status", "overview")
        }
        live_unique_ids = {
            entity._attr_unique_id
            for entities in instances.values()
            for entity in entities
        }
        for row in er.async_entries_for_config_entry(registry, entry.entry_id):
            if (
                row.platform == DOMAIN
                and row.domain == "sensor"
                and isinstance(row.unique_id, str)
                and row.unique_id.startswith(remote_unique_id_prefix)
                and row.unique_id not in expected_unique_ids
                and row.unique_id not in live_unique_ids
            ):
                registry.async_remove(row.entity_id)
        for remote_id in current:
            if remote_id in instances or remote_id in removing:
                continue
            entities = [
                PDMRemoteStatusSensor(coordinator, scope, remote_id, root_device.id),
                PDMRemoteOverviewSensor(
                    coordinator, scope, remote_id, root_device.id
                ),
            ]
            instances[remote_id] = entities
            async_add_entities(entities)
        for remote_id in set(instances) - set(current):
            entities = instances[remote_id]
            removing[remote_id] = hass.async_create_task(remove_remote(remote_id, entities))
        protected_remote_ids = set(current) | set(instances) | set(removing)
        cleanup_orphan_remote_devices(protected_remote_ids)

    reconcile()
    entry.async_on_unload(coordinator.async_add_listener(reconcile))
