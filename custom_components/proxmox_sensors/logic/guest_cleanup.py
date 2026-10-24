"""Final device cleanup after explicitly excluded guest entities are removed."""
import re

from homeassistant.helpers import device_registry as dr, entity_registry as er

from ..const import DOMAIN, CONF_PLATFORM_TYPE
from .guest_selection import _entry_cluster_id, allow_excluded_cluster_guest_cleanup
from .guest_keys import find_guest_node_in_resources
from .cluster_scope import (
    ACTIVE_SCOPE,
    associated_cluster_for_pve,
    cluster_scope_status,
    entry_cluster_scope_id,
)


def cleanup_excluded_guest_devices(hass):
    """Recheck live configuration and registry; never infer exclusion from emptiness."""
    devices = dr.async_get(hass)
    registry = er.async_get(hass)
    for owner in hass.config_entries.async_entries(DOMAIN):
        if owner.data.get(CONF_PLATFORM_TYPE) != "PVE":
            continue
        coordinator = hass.data.get(DOMAIN, {}).get(owner.entry_id, {}).get("coordinator")
        if coordinator is None or not coordinator.last_update_success:
            continue
        data = coordinator.data or {}
        cluster = _entry_cluster_id(hass, owner)
        scope_id = entry_cluster_scope_id(owner)
        scoped = (
            cluster_scope_status(owner) == ACTIVE_SCOPE
            and scope_id is not None
            and associated_cluster_for_pve(
                owner, hass.config_entries.async_entries(DOMAIN)
            ) is not None
        )
        if (not cluster or data.get("cluster_resources_ok") is not True
                or not isinstance(data.get("cluster_resources"), list)
                or any(not isinstance(item, dict) for item in data["cluster_resources"])):
            continue
        identity_scope = scope_id if scoped else cluster
        pattern = re.compile(
            r"proxmox_(vm|ct)_cluster_" + re.escape(identity_scope) + r"_([0-9]+)_v1"
        )
        for device in list(dr.async_entries_for_config_entry(devices, owner.entry_id)):
            if device.connections or len(device.identifiers) != 1:
                continue
            domain, identifier = next(iter(device.identifiers))
            match = pattern.fullmatch(identifier) if domain == DOMAIN else None
            if not match:
                continue
            kind, vmid = match.groups()
            if not find_guest_node_in_resources(data.get("cluster_resources", []), kind, vmid):
                continue
            uid = f"pve_cluster_{identity_scope}_proxmox_{kind}_{identity_scope}_{vmid}_status_v1".lower().replace(" ", "_")
            if not allow_excluded_cluster_guest_cleanup(hass, owner, data, uid):
                continue
            # Include disabled entities and other integrations: never delete their device.
            if er.async_entries_for_device(registry, device.id, include_disabled_entities=True):
                continue
            if dr.async_entries_for_parent_device(devices, device.id):
                continue
            if any(other.via_device_id == device.id for other in devices.async_get_devices()):
                continue
            devices.async_remove_device(device.id)
