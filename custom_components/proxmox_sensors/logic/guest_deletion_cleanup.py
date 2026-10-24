"""Remove registry data for guests confirmed absent from a fresh cluster inventory."""

import asyncio
import re
from types import SimpleNamespace

from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_platform import async_get_platforms

from ..const import DOMAIN


def cluster_inventory_is_fresh(coordinator, cluster_resources):
    """Return whether this cycle contains a complete successful inventory."""
    data = coordinator.data or {}
    return (
        coordinator.last_update_success
        and data.get("cluster_resources_ok") is True
        and "cluster_resources" in data
        and data["cluster_resources"] == cluster_resources
        and isinstance(cluster_resources, list)
        and all(
            isinstance(resource, dict)
            and isinstance(resource.get("type"), str)
            and bool(resource["type"])
            and (
                resource["type"] not in {"qemu", "lxc"}
                or (resource.get("vmid") is not None
                    and isinstance(resource.get("node"), str)
                    and bool(resource["node"]))
            )
            for resource in cluster_resources
        )
    )


def guest_is_absent(coordinator, cluster_resources, kind, vmid):
    """Require a fresh, complete inventory with no matching guest resource."""
    if not cluster_inventory_is_fresh(coordinator, cluster_resources):
        return False
    resource_type = "qemu" if kind == "vm" else "lxc"
    return not any(
        isinstance(resource, dict)
        and resource.get("type") == resource_type
        and str(resource.get("vmid")) == str(vmid)
        for resource in cluster_resources
    )


def registered_guest_groups(hass, entry, node, cluster_id, identity_context):
    """Build tracked placeholders for registered guests with no live entities."""
    devices = dr.async_get(hass)
    registry = er.async_get(hass)
    candidates = {}
    ambiguous = set()
    scoped = bool(identity_context and identity_context.use_scoped_identity)
    scope = identity_context.scope if scoped else (str(cluster_id).lower() if cluster_id else None)
    node = str(node).lower()

    for device in dr.async_entries_for_config_entry(devices, entry.entry_id):
        rows = [
            row for row in er.async_entries_for_device(
                registry, device.id, include_disabled_entities=True
            )
            if row.platform == DOMAIN and row.config_entry_id == entry.entry_id
        ]
        if not rows:
            continue
        for domain, identifier in device.identifiers:
            if domain != DOMAIN or not isinstance(identifier, str):
                continue
            for kind in ("vm", "ct"):
                patterns = []
                if scope:
                    patterns.append((scope, rf"proxmox_{kind}_cluster_{re.escape(scope)}_([0-9]+)_v1"))
                if not scoped and node:
                    patterns.append((node, rf"proxmox_{kind}_{re.escape(node)}_([0-9]+)_v1"))
                for identity_scope, pattern in patterns:
                    match = re.fullmatch(pattern, identifier.lower())
                    if not match:
                        continue
                    vmid = match[1]
                    key = f"{kind}:{identity_scope}:{vmid}"
                    placeholder = SimpleNamespace(
                        device_info={"identifiers": {(DOMAIN, identifier)}},
                        _attr_unique_id=rows[0].unique_id,
                        hass=None,
                        _registry_only=True,
                    )
                    if key in candidates and candidates[key][0] != device.id:
                        ambiguous.add(key)
                    else:
                        candidates[key] = (device.id, [placeholder])
                    break

    return {
        key: value[1]
        for key, value in candidates.items()
        if key not in ambiguous
    }


async def async_cleanup_deleted_guest(hass, entry, coordinator, kind, vmid,
                                     cluster_resources, entities):
    """Remove only rows/device identified by this guest's live entity objects."""
    locks = hass.data.setdefault(DOMAIN, {}).setdefault(
        "deleted_guest_cleanup_locks", {}
    )
    key = (entry.entry_id, kind, str(vmid))
    lock = locks.setdefault(key, asyncio.Lock())
    async with lock:
        return await _async_cleanup_deleted_guest(
            hass, entry, coordinator, kind, vmid, cluster_resources, entities
        )


async def _async_cleanup_deleted_guest(hass, entry, coordinator, kind, vmid,
                                       cluster_resources, entities):
    if not guest_is_absent(coordinator, cluster_resources, kind, vmid):
        return False

    expected = set()
    for entity in entities:
        info = entity.device_info or {}
        expected.update(
            (domain, identifier)
            for domain, identifier in info.get("identifiers", ())
            if domain == DOMAIN
        )
    if not expected:
        return False

    devices = dr.async_get(hass)
    registry = er.async_get(hass)
    targets = [
        device for device in dr.async_entries_for_config_entry(devices, entry.entry_id)
        if device.config_entry_id == entry.entry_id
        and device.identifiers.intersection(expected)
        and device.identifiers.issubset(expected)
    ]
    if len(targets) != 1:
        return False

    platforms = async_get_platforms(hass, DOMAIN) or ()
    for device in targets:
        if not guest_is_absent(coordinator, (coordinator.data or {}).get("cluster_resources"), kind, vmid):
            return False
        rows = er.async_entries_for_device(
            registry, device.id, include_disabled_entities=True
        )
        row_ids = {row.entity_id for row in rows if row.platform == DOMAIN}
        for platform in platforms:
            for entity in list(platform.entities.values()):
                row = getattr(entity, "registry_entry", None)
                if row is not None and row.entity_id in row_ids:
                    await entity.async_remove(force_remove=True)

        # Disabled entities and any rows not represented by a live object are
        # removed explicitly, but only from this exact guest device.
        for row in rows:
            current = registry.async_get(row.entity_id)
            if (row.platform == DOMAIN and current is not None
                    and current.unique_id == row.unique_id
                    and current.device_id == device.id):
                registry.async_remove(row.entity_id)

        remaining = er.async_entries_for_device(
            registry, device.id, include_disabled_entities=True
        )
        referenced = (
            dr.async_entries_for_parent_device(devices, device.id)
            or any(other.via_device_id == device.id
                   for other in devices.async_get_devices())
        )
        try:
            referenced = referenced or any(
                info and (
                    device.identifiers.intersection(info.get("identifiers", ()))
                    or info.get("via_device_id") == device.id
                )
                for platform in platforms
                for entity in platform.entities.values()
                if (info := entity.device_info)
            )
        except Exception:
            referenced = True
        if (not remaining and not referenced and not device.connections
                and devices.async_get(device.id) == device):
            devices.async_remove_device(device.id)
    return True
