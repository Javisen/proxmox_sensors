"""Normalize ConfigEntry, Entity Registry and Device Registry snapshots read-only."""

from ..const import DOMAIN
from .classification import classify_entity


# Attributes displayed as native attribute rows, not copied as arbitrary payloads.
DISPLAY_ATTRIBUTES = frozenset({
    "SMART Status", "SMART Temp", "Health", "Power On Hours", "Reallocated Sectors",
    "Pending Sectors", "Uncorrectable Errors", "Media Errors", "Wear Level",
    "pool", "health", "size_gb", "used_gb", "free_gb", "fragmentation", "deduplication",
    "sensors_status", "smart_status", "memory_status", "mounts_status",
    "replication_status", "replication_jobs", "replication_failed_jobs",
    "ram_total_bytes",
})

PDM_DISPLAY_ATTRIBUTES = frozenset({
    "remotes", "pve_remotes", "pbs_remotes", "failed_remotes", "sections_fresh",
    "pve_nodes", "pbs_nodes", "qemu", "lxc", "storages", "pbs_datastores", "sdn_zones",
    "pve_cpu_stats", "pve_memory_stats", "pve_storage_stats",
    "pbs_cpu_stats", "pbs_memory_stats", "pbs_storage_stats",
    "oldest_last_refresh", "newest_last_refresh", "oldest_refresh_age",
    "endpoint_fresh", "snapshot_complete",
    "remote_type", "subscription", "status_fresh", "inventory", "capacity", "resources_fresh",
})

# Only the existing node overview (translation_key=proxmox_node) exposes these
# header references. Values/payloads are never copied into the inventory.
NODE_HEADER_ATTRIBUTES = frozenset({
    "node_name", "status", "pve_version", "kernel_version", "uptime_seconds",
    "vm_count", "ct_count", "storage_count",
})


def _device_class(row, attrs):
    """Preserve registered override/platform class, with state as fallback."""
    for value in (getattr(row, "device_class", None),
                  getattr(row, "original_device_class", None), attrs.get("device_class")):
        if value is not None:
            return value
    return None


def build_inventory(entries, rows, devices, states, selections=None):
    """Build a deterministic JSON-compatible snapshot without HA dependencies.

    entries: sanitized entry dictionaries; rows/devices: registry entries;
    states: entity_id -> HA State; selections: entry_id -> {vm/ct: IDs or None}.
    None means all. Unknown selection is represented by the string 'unknown'
    and suppresses guest resources rather than exposing deselected guests.
    """
    owners = {e["entry_id"]: dict(e) for e in entries}
    devices = {d.id: d for d in devices}
    selections = selections or {}
    records = []
    for row in sorted(rows, key=lambda r: r.entity_id):
        if row.platform != DOMAIN or row.config_entry_id not in owners:
            continue
        owner = owners[row.config_entry_id]
        device = devices.get(row.device_id)
        identifiers = {ident for domain, ident in getattr(device, "identifiers", ()) if domain == DOMAIN}
        classification = classify_entity(row, owner, identifiers)
        records.append((row, owner, device, classification))

    # Status registry ownership is authoritative, even when hidden/disabled.
    # Old source devices and CLUSTER-owned replication cannot create guest copies.
    authorities = {}
    for row, owner, device, info in records:
        if (info.get("guest") and owner["platform_type"] == "PVE"
                and row.entity_id.startswith("sensor.") and row.unique_id.endswith("_status_v1")):
            authorities.setdefault(info["key"], []).append((owner, device, info))

    resources = {}
    excluded = {"disabled": 0, "hidden": 0, "guest_selection": 0, "guest_owner_unknown": 0}
    for row, owner, device, info in records:
        if getattr(row, "disabled_by", None) is not None:
            excluded["disabled"] += 1
            continue
        if getattr(row, "hidden_by", None) is not None:
            excluded["hidden"] += 1
            continue
        if reference := info.get("guest_reference"):
            matches = [candidate[2] for group in authorities.values() for candidate in group
                       if candidate[2]["guest"][1:] == reference]
            if len(matches) != 1:
                excluded["guest_owner_unknown"] += 1
                continue
            info = {**matches[0], "family": "replication"}
        display_owner = owner
        if guest := info.get("guest"):
            candidates = authorities.get(info["key"], [])
            if len(candidates) != 1:
                excluded["guest_owner_unknown"] += 1
                continue
            display_owner, authoritative_device, _status_info = candidates[0]
            kind, cluster, vmid = guest
            if cluster and display_owner.get("cluster_id") != cluster:
                excluded["guest_owner_unknown"] += 1
                continue
            chosen = selections.get(display_owner["entry_id"], {}).get(kind, "unknown")
            if chosen == "unknown" or (chosen is not None and vmid not in chosen):
                excluded["guest_selection"] += 1
                continue
            device_for_name = authoritative_device
        else:
            device_for_name = device
        resource = resources.setdefault(info["key"], {
            "resource_id": info["key"], "kind": info["kind"],
            "title": (getattr(device_for_name, "name_by_user", None)
                      or getattr(device_for_name, "name", None) or info["label"])
                     if info["kind"] in ("vm", "ct", "datastore", "pdm_remote") else info["label"],
            "entry_id": display_owner["entry_id"], "cluster_id": display_owner.get("cluster_id"),
            "node": display_owner.get("node"), "server_id": display_owner.get("server_id"),
            "guest_id": info["guest"][2] if info.get("guest") else None,
            "entities": [],
        })
        state = states.get(row.entity_id)
        attrs = getattr(state, "attributes", {})
        value = getattr(state, "state", None)
        translation_key = getattr(row, "translation_key", None)
        allowed_attributes = DISPLAY_ATTRIBUTES
        if owner["platform_type"] == "PDM":
            allowed_attributes = allowed_attributes | PDM_DISPLAY_ATTRIBUTES
        elif owner["platform_type"] == "PVE" and translation_key == "proxmox_node":
            allowed_attributes = allowed_attributes | NODE_HEADER_ATTRIBUTES
        resource["entities"].append({
            "entity_id": row.entity_id, "unique_id": row.unique_id,
            "config_entry_id": row.config_entry_id, "device_id": row.device_id,
            "domain": row.entity_id.split(".", 1)[0], "family": info["family"],
            "name": getattr(row, "name", None) or getattr(row, "original_name", None) or row.entity_id,
            "state": value, "availability": "missing" if state is None else
                "restored" if "restored" in attrs else value if value in ("unknown", "unavailable") else "available",
            "translation_key": translation_key,
            "device_class": _device_class(row, attrs),
            "unit": attrs.get("unit_of_measurement", getattr(row, "unit_of_measurement", None)),
            "attributes": sorted(allowed_attributes.intersection(attrs)),
        })
    return {"schema_version": 1, "entries": sorted(owners.values(), key=lambda e: e["entry_id"]),
            "resources": sorted(resources.values(), key=lambda r: r["resource_id"]), "excluded": excluded}


def discover_inventory(hass):
    """Read current HA registries; never refresh coordinators or mutate registries."""
    from homeassistant.helpers import device_registry as dr, entity_registry as er
    from ..logic.guest_selection import (
        _entry_cluster_id, get_effective_guest_selections, get_entry_guest_selection,
        selection_guest_ids,
    )
    from ..logic.cluster_scope import (
        associated_cluster_for_pve,
        associated_pves_for_cluster,
        cluster_guest_identity_context,
        entry_cluster_scope_id,
        guest_identity_context,
    )
    from ..logic.pve_local_identity import PveLocalIdentityError, pve_local_identity_context

    entries = list(hass.config_entries.async_entries(DOMAIN))
    normalized, rows, selections = [], [], {}
    registry = er.async_get(hass)
    for entry in entries:
        platform = (entry.data.get("platform_type") or entry.data.get("server_type") or "").upper()
        legacy_cluster = ((str(entry.data.get("cluster_name", "")).lower() or None)
                          if platform == "CLUSTER" else _entry_cluster_id(hass, entry))
        context = (cluster_guest_identity_context(entry, entries, legacy_cluster)
                   if platform == "CLUSTER" else guest_identity_context(entry, legacy_cluster)
                   if platform == "PVE" else None)
        if platform == "PVE" and context and context.use_scoped_identity:
            matching_clusters = [candidate for candidate in entries
                                 if candidate.data.get("platform_type") == "CLUSTER"
                                 and entry_cluster_scope_id(candidate) == context.scope]
            if matching_clusters and associated_cluster_for_pve(entry, entries) is None:
                context = None
        cluster = context.scope if context and context.use_scoped_identity else legacy_cluster
        pve_identity_id = None
        if platform == "PVE":
            try:
                pve_identity_id = pve_local_identity_context(entry, entries).identity_id
            except PveLocalIdentityError:
                pass
        normalized.append({"entry_id": entry.entry_id, "platform_type": platform,
                           "title": entry.title or platform, "node": entry.data.get("node") if platform == "PVE" else None,
                           "server_id": entry.data.get("server_id") if platform == "PBS" else None,
                           "cluster_id": cluster, "pve_identity_id": pve_identity_id,
                           "pdm_identity_id": entry.data.get("pdm_identity_id") if platform == "PDM" else None})
        rows.extend(er.async_entries_for_config_entry(registry, entry.entry_id))
        if platform == "PVE":
            try:
                members = [entry]
                if context and context.use_scoped_identity:
                    cluster_entry = associated_cluster_for_pve(entry, entries)
                    if cluster_entry is not None:
                        members = associated_pves_for_cluster(cluster_entry, entries)
                else:
                    members = [member for member in entries if member.entry_id == entry.entry_id or (
                        cluster and member.data.get("platform_type") == "PVE"
                        and _entry_cluster_id(hass, member) == cluster)]
                for member in members:
                    for option in ("selected_vms", "selected_cts"):
                        selection_guest_ids(get_entry_guest_selection(member, option))
                vms, cts = get_effective_guest_selections(hass, entry, cluster)
                selections[entry.entry_id] = {"vm": selection_guest_ids(vms), "ct": selection_guest_ids(cts)}
            except (ValueError, TypeError):
                selections[entry.entry_id] = {"vm": "unknown", "ct": "unknown"}
    states = {row.entity_id: hass.states.get(row.entity_id) for row in rows}
    device_registry = dr.async_get(hass)
    # async_get_devices() searches identifiers/connections; without filters it
    # is not an enumeration. Resolve the exact IDs referenced by registry rows.
    devices = [device for device_id in sorted({row.device_id for row in rows if row.device_id})
               if (device := device_registry.async_get(device_id)) is not None]
    return build_inventory(normalized, rows, devices, states, selections)
