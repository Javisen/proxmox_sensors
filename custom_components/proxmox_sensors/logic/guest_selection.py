"""Shared VM/CT selection helpers."""

from __future__ import annotations

from ..const import CONF_PLATFORM_TYPE, DOMAIN
from .guest_keys import matches_selected_guest
from .cluster_scope import (
    ACTIVE_SCOPE,
    LEGACY_SCOPE,
    associated_cluster_for_pve,
    cluster_scope_membership,
    cluster_scope_status,
)

EFFECTIVE_SELECTED_VMS = "_effective_selected_vms"
EFFECTIVE_SELECTED_CTS = "_effective_selected_cts"


def get_entry_guest_selection(entry, key, default=None):
    """Return a guest selection, preferring options over config entry data."""
    options = entry.options or {}
    return options.get(key, entry.data.get(key, default))


def _normalize_cluster_id(cluster_id):
    if cluster_id in (None, ""):
        return None
    return str(cluster_id).lower()


def _merge_guest_selection(base_selection, other_selection):
    """Merge two guest selections preserving None as the legacy 'all' marker."""
    if base_selection is None or other_selection is None:
        return None

    merged = {str(value) for value in base_selection or []}
    merged.update(str(value) for value in other_selection or [])
    return list(merged)


def _entry_cluster_id(hass, entry):
    """Prefer runtime; use explicit membership while a sibling is starting."""
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = runtime.get("coordinator")
    data = getattr(coordinator, "data", None) or {}
    if data:
        # Preserve normal-cycle behavior, including an unknown runtime cluster.
        return _normalize_cluster_id(data.get("cluster_id"))

    persisted = entry.data.get("cluster_id")
    if persisted is not None and (
        not isinstance(persisted, str) or not persisted.strip()
    ):
        return None
    persisted = _normalize_cluster_id(persisted)
    parents = [
        candidate for candidate in hass.config_entries.async_entries(DOMAIN)
        if candidate.data.get(CONF_PLATFORM_TYPE) == "CLUSTER"
        and candidate.data.get("parent_entry_id") == entry.entry_id
    ]
    if len(parents) > 1:
        return None
    if not parents:
        return persisted
    parent_cluster = parents[0].data.get("cluster_name")
    if not isinstance(parent_cluster, str) or not parent_cluster.strip():
        return None
    parent_cluster = _normalize_cluster_id(parent_cluster)
    if persisted is not None and persisted != parent_cluster:
        # Conflicting stored evidence must not mix selections across clusters.
        return None
    return persisted or parent_cluster


def _selection_membership_key(hass, entry):
    """Return an explicit scope, or the legacy name-only compatibility key.

    Scope membership is never inferred.  Only entries with no scope field at
    all retain the pre-scope cluster-name behavior among other legacy entries.
    """
    scope = cluster_scope_membership(entry)
    if scope is not None:
        return scope
    if cluster_scope_status(entry) != LEGACY_SCOPE:
        return None
    cluster = _entry_cluster_id(hass, entry)
    return ("legacy", _normalize_cluster_id(cluster)) if cluster else None


def get_effective_guest_selections(
    hass,
    entry,
    cluster_id,
    selected_vms=None,
    selected_cts=None,
):
    """Return effective VM and CT selections using one cluster membership pass."""
    selected_vms = get_entry_guest_selection(entry, "selected_vms", selected_vms)
    selected_cts = get_entry_guest_selection(entry, "selected_cts", selected_cts)

    membership = _selection_membership_key(hass, entry)
    if membership is None:
        return selected_vms, selected_cts

    effective_selected_vms = selected_vms
    effective_selected_cts = selected_cts
    entries = list(hass.config_entries.async_entries(DOMAIN))

    for other_entry in entries:
        if other_entry.entry_id == entry.entry_id:
            continue
        if other_entry.data.get(CONF_PLATFORM_TYPE) != "PVE":
            continue
        if _selection_membership_key(hass, other_entry) != membership:
            continue

        effective_selected_vms = _merge_guest_selection(
            effective_selected_vms,
            get_entry_guest_selection(other_entry, "selected_vms", []),
        )
        effective_selected_cts = _merge_guest_selection(
            effective_selected_cts,
            get_entry_guest_selection(other_entry, "selected_cts", []),
        )

    return effective_selected_vms, effective_selected_cts


def guest_selection_entries(hass, entry):
    """Use exactly the same membership evidence as the effective selection."""
    membership = _selection_membership_key(hass, entry)
    return [entry] + [
        other for other in hass.config_entries.async_entries(DOMAIN)
        if membership and other.entry_id != entry.entry_id
        and other.data.get(CONF_PLATFORM_TYPE) == "PVE"
        and _selection_membership_key(hass, other) == membership
    ]


def selection_guest_ids(selection):
    """Normalize supported legacy VMID and node:VMID selections for the form."""
    if selection is None:
        return None
    if not isinstance(selection, (list, tuple, set)):
        raise ValueError("Invalid saved guest selection; no changes saved")
    result = set()
    for value in selection:
        vmid = str(value).rsplit(":", 1)[-1]
        if not vmid.isdecimal():
            raise ValueError("Invalid saved guest identifier; no changes saved")
        result.add(vmid)
    return result


def plan_guest_selection(entries, key, chosen, visible, inventory_valid, previous_ids=()):
    """Plan all sibling writes before mutating any entry. Never drop absent IDs."""
    if not inventory_valid:
        raise ValueError("Guest discovery failed or is incomplete; no selection changes saved")
    visible = set(visible)
    chosen = selection_guest_ids(chosen)
    if chosen is None or not chosen <= visible:
        raise ValueError("Guest inventory changed; reopen Options before saving")
    saved = [selection_guest_ids(get_entry_guest_selection(e, key, [])) for e in entries]
    absent = set().union(*(values - visible for values in saved if values is not None))
    if any(values is None for values in saved):
        absent.update(set(previous_ids) - visible)
    # None absorbs explicit selections, as in the existing union semantics.
    effective = visible if any(values is None for values in saved) else set().union(*saved) & visible
    if chosen == effective:
        return {}
    result = sorted(chosen | absent)
    return {entry.entry_id: result for entry in entries}


def set_effective_guest_selections(data, selected_vms, selected_cts):
    """Store the effective selections used to build one coordinator data cycle."""
    data[EFFECTIVE_SELECTED_VMS] = selected_vms
    data[EFFECTIVE_SELECTED_CTS] = selected_cts


def get_cycle_guest_selections(
    hass,
    entry,
    c_data,
    selected_vms,
    selected_cts,
    cluster_id,
):
    """Return the effective selections stored by the coordinator for this cycle."""
    membership = cluster_scope_membership(entry)
    scoped_active = (
        membership is not None
        and membership[0] == ACTIVE_SCOPE
        and associated_cluster_for_pve(
            entry, hass.config_entries.async_entries(DOMAIN)
        ) is not None
    )
    if membership is not None and membership[0] == ACTIVE_SCOPE and not scoped_active:
        return selected_vms, selected_cts
    if not _normalize_cluster_id(cluster_id) and not scoped_active:
        return selected_vms, selected_cts

    if (
        isinstance(c_data, dict)
        and EFFECTIVE_SELECTED_VMS in c_data
        and EFFECTIVE_SELECTED_CTS in c_data
    ):
        return c_data[EFFECTIVE_SELECTED_VMS], c_data[EFFECTIVE_SELECTED_CTS]

    return get_effective_guest_selections(
        hass, entry, cluster_id, selected_vms, selected_cts
    )


def allow_excluded_cluster_guest_cleanup(hass, entry, data, unique_id):
    """Authorize only a known VM/CT identity excluded by current configuration."""
    import re

    if entry.data.get(CONF_PLATFORM_TYPE) != "PVE" or data.get("cluster_resources_ok") is not True:
        return False
    cluster = data.get("cluster_id")
    if not isinstance(cluster, str) or not cluster.strip():
        return False
    cluster = _normalize_cluster_id(cluster)
    if _entry_cluster_id(hass, entry) != cluster:
        return False
    scope = re.escape(cluster.replace(" ", "_"))
    match = re.fullmatch(
        rf"pve_cluster_{scope}_proxmox_(vm|ct)_{scope}_([0-9]+)_"
        r"(status|cpu_usage|memory_used|memory_total|disk_total|disk_used|disk_usage|uptime|network_rx|network_tx)_v1",
        unique_id or "",
    )
    if not match or (match[1] == "vm" and match[3] == "disk_used"):
        return False
    key = "selected_vms" if match[1] == "vm" else "selected_cts"
    try:
        for sibling in hass.config_entries.async_entries(DOMAIN):
            if sibling.data.get(CONF_PLATFORM_TYPE) != "PVE":
                continue
            sibling_cluster = _entry_cluster_id(hass, sibling)
            # An unresolved entry could contribute a selection to this cluster.
            if sibling_cluster is None:
                return False
            if sibling_cluster == cluster:
                values = get_entry_guest_selection(sibling, key)
                if values is None:
                    return False
                selection_guest_ids(values)
        vms, cts = get_effective_guest_selections(hass, entry, cluster)
        selected = selection_guest_ids(vms if match[1] == "vm" else cts)
    except (TypeError, ValueError):
        return False
    return selected is not None and match[2] not in selected
