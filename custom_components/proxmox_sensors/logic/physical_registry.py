"""Registry preflight and lifecycle limited to PVE physical disks."""

from __future__ import annotations

import logging

from homeassistant.components import persistent_notification
from homeassistant.helpers import device_registry as dr, entity_registry as er

from ..const import DOMAIN
from .physical_disks import (
    BINDINGS_KEY, DiskIdentityError, capacity_unique_id, hardware_value, plan_disks,
    legacy_capacity_path, prove_legacy_rows,
)
from .pve_local_identity import (
    coordinator_pve_local_identity_context, disks_group_identifier,
    node_device_identifier,
)


_LOGGER = logging.getLogger(__name__)
DEVICE_PREFIX = "proxmox_physical_disk_v2_"


def _physical_device(device):
    return any(domain == DOMAIN and identifier.startswith(DEVICE_PREFIX)
               for domain, identifier in device.identifiers)


def _disk_rows(registry, entry):
    return [row for row in er.async_entries_for_config_entry(registry, entry.entry_id)
            if row.domain in {"sensor", "select", "switch"} and row.platform == DOMAIN
            and ((row.domain == "sensor" and "proxmox_disk_" in (row.unique_id or ""))
                 or (row.unique_id or "").startswith(DEVICE_PREFIX))]


def _safe_remove_device(devices, registry, device):
    if er.async_entries_for_device(registry, device.id, include_disabled_entities=True):
        return False
    if dr.async_entries_for_parent_device(devices, device.id):
        return False
    if any(other.via_device_id == device.id for other in devices.async_get_devices()):
        return False
    devices.async_remove_device(device.id)
    return True


def reconcile_physical_registry(hass, entry, coordinator, node, enabled):
    """Return safe path-to-ID mapping and protected devices for this setup."""
    registry = er.async_get(hass)
    devices = dr.async_get(hass)
    rows = _disk_rows(registry, entry)
    existing_devices = dr.async_entries_for_config_entry(devices, entry.entry_id)
    old_device_ids = {device.id for device in existing_devices if _physical_device(device)}
    protected = set(old_device_ids)
    context = coordinator_pve_local_identity_context(coordinator)
    group_identifier = disks_group_identifier(context, node.lower())
    group = devices.async_get_device_by_identifier(
        (DOMAIN, group_identifier), config_entry_id=entry.entry_id,
    )
    if group is not None:
        protected.add(group.id)

    for device in existing_devices:
        if device.id not in old_device_ids:
            continue
        if (len(device.identifiers) != 1 or
                any(row.config_entry_id != entry.entry_id or
                    not (row.unique_id or "").startswith(DEVICE_PREFIX)
                    for row in er.async_entries_for_device(
                        registry, device.id, include_disabled_entities=True,
                    ))):
            _LOGGER.warning("Physical disk device has conflicting Registry ownership")
            return {}, protected

    if not enabled:
        # Preserve row customizations while the live entities and empty device
        # objects disappear. Re-enabling relinks the same rows by unique ID.
        for row in rows:
            if row.unique_id.startswith(DEVICE_PREFIX) and row.device_id in old_device_ids:
                registry.async_update_entity(row.entity_id, device_id=None)
        for device in existing_devices:
            if device.id in old_device_ids:
                _safe_remove_device(devices, registry, device)
        if group is not None and not _safe_remove_device(devices, registry, group):
            return {}, {group.id}
        return {}, set()

    data = coordinator.data or {}
    if data.get("_cleanup_confirmed", {}).get("node_disks") is not True:
        _LOGGER.warning("Physical disk inventory is unconfirmed; retaining Registry identities")
        return {}, protected
    disks = data.get("disks")
    scope = context.identity_id if not context.is_legacy else entry.entry_id
    node_device = devices.async_get_device_by_identifier(
        (DOMAIN, node_device_identifier(context, node.lower())),
        config_entry_id=entry.entry_id,
    )
    try:
        identities, bindings = plan_disks(scope, disks, entry.data.get(BINDINGS_KEY, {}))
        server_id = entry.data.get("server_id", "default")
        old_rows = [
            row for row in rows
            if row.domain == "sensor" and legacy_capacity_path(
                row.unique_id, context, server_id, node.lower()
            ) is not None
        ]
        migrations = []
        retirements = []
        for row in old_rows:
            if row.device_id is not None and (group is None or row.device_id != group.id):
                raise DiskIdentityError("Legacy disk row belongs to another device")
            try:
                migration = prove_legacy_rows(
                    [row], hass.states, entry.entry_id, context,
                    server_id, node.lower(), disks, identities,
                )
            except DiskIdentityError:
                retirements.append(row)
            else:
                migrations.extend(migration)
        target_ids = {target for _, _, target in migrations}
        if len(target_ids) != len(migrations):
            raise DiskIdentityError("Duplicate legacy migration target")
        for path, identifier in identities.items():
            uid = capacity_unique_id(identifier)
            existing_id = registry.async_get_entity_id("sensor", DOMAIN, uid)
            if existing_id:
                existing = registry.async_get(existing_id)
                if existing.config_entry_id != entry.entry_id:
                    raise DiskIdentityError("Physical disk identity belongs to another entry")
                if uid in target_ids:
                    migration = next(item for item in migrations if item[2] == uid)
                    migrations.remove(migration)
                    retirements.append(migration[0])
            existing_device = devices.async_get_device_by_identifier(
                (DOMAIN, identifier), config_entry_id=entry.entry_id,
            )
            if existing_id and existing.device_id is not None:
                owner = devices.async_get(existing.device_id)
                if owner is None or (DOMAIN, identifier) not in owner.identifiers:
                    raise DiskIdentityError("Physical capacity row belongs to another device")
            if (existing_device is not None and node_device is not None
                    and existing_device.via_device_id not in (None, node_device.id)):
                raise DiskIdentityError("Physical disk device has another parent")
    except DiskIdentityError as err:
        _LOGGER.warning("Physical disk migration deferred for entry %s: %s", entry.entry_id, err)
        persistent_notification.async_create(
            hass,
            "Physical Disks could not be migrated safely. Existing Registry rows were kept. "
            "Check disk serial/WWN values and the integration log before retrying.",
            title="Physical Disks migration pending",
            notification_id=f"{DOMAIN}_physical_disk_{entry.entry_id}",
        )
        return {}, protected

    created = []
    changed = []
    try:
        for path, identifier in identities.items():
            disk = disks[path]
            existing = devices.async_get_device_by_identifier(
                (DOMAIN, identifier), config_entry_id=entry.entry_id,
            )
            if existing is not None and existing.id not in old_device_ids:
                protected.add(existing.id)
                continue
            model = str(disk.get("model") or "Disk")
            kind = str(disk.get("type") or "Disk").upper()
            size = disk.get("size")
            size_tb = round(size / (1024**4), 1) if isinstance(size, (int, float)) else None
            name = f"2. {kind} {model} {size_tb:g} TB" if size_tb else f"2. {kind} {model}"
            info = {
                "config_entry_id": entry.entry_id,
                "identifiers": {(DOMAIN, identifier)},
                "name": name,
                "manufacturer": str(disk.get("vendor") or "Proxmox"),
                "model": model,
            }
            if node_device is not None:
                info["via_device_id"] = node_device.id
            if serial := hardware_value(disk.get("serial")):
                info["serial_number"] = serial
            physical = devices.async_get_or_create(**info)
            protected.add(physical.id)
            if existing is None:
                created.append(physical.id)
        for row, path, target in migrations:
            physical = devices.async_get_device_by_identifier(
                (DOMAIN, identities[path]), config_entry_id=entry.entry_id,
            )
            if physical is None:
                raise DiskIdentityError("Physical device disappeared during migration")
            changed.append((row.entity_id, row.unique_id, row.device_id))
            registry.async_update_entity(
                row.entity_id, new_unique_id=target, device_id=physical.id,
            )
        # Reattach disabled or detached new-schema rows on reactivation.
        for row in rows:
            if not row.unique_id.startswith(DEVICE_PREFIX) or row.device_id is not None:
                continue
            identifier = next(
                (candidate for candidate in identities.values()
                 if row.unique_id.startswith(f"{candidate}_")), None,
            )
            if identifier is None:
                continue
            physical = devices.async_get_device_by_identifier(
                (DOMAIN, identifier), config_entry_id=entry.entry_id,
            )
            if physical is not None:
                changed.append((row.entity_id, row.unique_id, row.device_id))
                registry.async_update_entity(row.entity_id, device_id=physical.id)
        if bindings != entry.data.get(BINDINGS_KEY, {}):
            hass.config_entries.async_update_entry(
                entry, data={**entry.data, BINDINGS_KEY: bindings},
            )
    except Exception:
        for entity_id, old_uid, old_device in reversed(changed):
            current = registry.async_get(entity_id)
            if current is not None:
                registry.async_update_entity(
                    entity_id, new_unique_id=old_uid, device_id=old_device,
                )
        for device_id in reversed(created):
            device = devices.async_get(device_id)
            if device is not None:
                _safe_remove_device(devices, registry, device)
        raise

    for row in retirements:
        registry.async_remove(row.entity_id)

    group_removed = group is not None and _safe_remove_device(devices, registry, group)
    if group_removed:
        protected.discard(group.id)
    if retirements or group_removed:
        persistent_notification.async_dismiss(
            hass, f"{DOMAIN}_physical_disk_{entry.entry_id}",
        )
        persistent_notification.async_create(
            hass,
            "Physical disks now have separate devices. Legacy capacity entities without "
            "proven serial correspondence were replaced; review their customizations and "
            "automations. The former `2. Disks` device ID cannot follow multiple disks. "
            "Use your pre-install Home Assistant backup to recover old settings if needed.",
            title="Physical Disks device migration",
            notification_id=f"{DOMAIN}_physical_disk_migrated_{entry.entry_id}",
        )
    for device in existing_devices:
        if device.id not in old_device_ids:
            continue
        if not any((DOMAIN, identifier) in device.identifiers
                   for identifier in identities.values()):
            for row in er.async_entries_for_device(
                registry, device.id, include_disabled_entities=True,
            ):
                if row.config_entry_id == entry.entry_id and row.unique_id.startswith(DEVICE_PREFIX):
                    registry.async_update_entity(row.entity_id, device_id=None)
            if _safe_remove_device(devices, registry, device):
                protected.discard(device.id)
    return identities, protected
