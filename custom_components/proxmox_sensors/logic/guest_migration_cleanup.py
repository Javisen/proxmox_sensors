"""Retire an empty source device after an observed guest handoff.

This is deliberately independent of selection/exclusion cleanup. Registry
entries are only read here; the existing platforms remain responsible for claims.
"""


from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr, entity_registry as er

from ..const import CONF_NODE, CONF_PLATFORM_TYPE, DOMAIN
from .guest_selection import (
    _entry_cluster_id, get_effective_guest_selections, get_entry_guest_selection,
    selection_guest_ids,
)
from .cluster_scope import ACTIVE_SCOPE, associated_cluster_for_pve, cluster_scope_status, entry_cluster_scope_id
from .pve_local_identity import node_device_identifier, pve_local_identity_context









def reconcile_claimed_guest_rows(registry, source_id, destination_id, rows,
                                 source_entry_id, target_entry_id, states):
    """Attach already claimed rows to the destination after a complete preflight."""
    pending = []
    for entity_id, (unique_id, owner_id) in rows.items():
        row = registry.async_get(entity_id)
        expected_owner = target_entry_id if owner_id == source_entry_id else owner_id
        if (row is None or row.unique_id != unique_id
                or row.config_entry_id != expected_owner
                or row.device_id not in (source_id, destination_id)):
            return False
        if row.device_id == source_id:
            if owner_id not in (source_entry_id, target_entry_id):
                return False
            state = states.get(entity_id)
            if row.disabled_by is None and (state is None or "restored" in state.attributes):
                return False
            pending.append(entity_id)

    moved = []
    try:
        for entity_id in pending:
            registry.async_update_entity(entity_id, device_id=destination_id)
            moved.append(entity_id)
    except Exception:
        for entity_id in reversed(moved):
            registry.async_update_entity(entity_id, device_id=source_id)
        return False
    return True


def setup_guest_migration_cleanup(hass, entry, coordinator):
    """Return a release observer whose lifetime is the source config entry."""
    devices = dr.async_get(hass)
    registry = er.async_get(hass)
    pending = {}
    subscriptions = {}
    scheduled = None
    closed = False
    source_node = str(entry.data.get(CONF_NODE, "")).lower()

    def scoped_member(owner, scope):
        entries = list(hass.config_entries.async_entries(DOMAIN))
        return (
            cluster_scope_status(owner) == ACTIVE_SCOPE
            and entry_cluster_scope_id(owner) == scope
            and associated_cluster_for_pve(owner, entries) is not None
        )

    def runtime(owner):
        return hass.data.get(DOMAIN, {}).get(owner.entry_id, {}).get("coordinator")


    def location(data, kind, vmid):
        # Conflicting/absent inventory is not evidence of a completed migration.
        nodes = {
            str(row.get("node", "")).lower()
            for row in data.get("cluster_resources", [])
            if isinstance(row, dict)
            and row.get("type") == ("qemu" if kind == "vm" else "lxc")
            and str(row.get("vmid")) == vmid
        }
        return next(iter(nodes)) if len(nodes) == 1 and "" not in nodes else None

    def selected(cluster, kind, vmid):
        members = hass.config_entries.async_entries(DOMAIN)
        scoped = scoped_member(entry, cluster)
        if not scoped and any(e.data.get(CONF_PLATFORM_TYPE) == "PVE"
                              and _entry_cluster_id(hass, e) is None for e in members):
            return None
        try:
            for owner in members:
                member = scoped_member(owner, cluster) if scoped else _entry_cluster_id(hass, owner) == cluster
                if owner.data.get(CONF_PLATFORM_TYPE) == "PVE" and member:
                    selection_guest_ids(get_entry_guest_selection(
                        owner, "selected_vms" if kind == "vm" else "selected_cts",
                    ))
            selections = get_effective_guest_selections(hass, entry, cluster)
            values = selection_guest_ids(selections[0 if kind == "vm" else 1])
        except (TypeError, ValueError):
            return None
        return values is None or vmid in values

    def fresh(owner, cluster):
        current = runtime(owner)
        member = scoped_member(owner, cluster) if scoped_member(entry, cluster) else _entry_cluster_id(hass, owner) == cluster
        return (current is not None and current.last_update_success
                and member
                and (current.data or {}).get("cluster_resources_ok") is True)

    def valid_device(device, owner, identifier):
        local_identity = (getattr(runtime(owner), "pve_local_identity_context", None)
                          or pve_local_identity_context(owner))
        parent = devices.async_get_device_by_identifier(
            (
                DOMAIN,
                node_device_identifier(
                    local_identity,
                    str(owner.data.get(CONF_NODE, "")).lower(),
                ),
            ),
            config_entry_id=owner.entry_id,
        )
        return (device is not None and device.config_entry_id == owner.entry_id
                and device.identifiers == {identifier} and not device.connections
                and parent is not None and device.via_device_id == parent.id)

    def invalidate():
        for did, item in list(pending.items()):
            cluster, kind, vmid, target, target_node, _identifier, _status_id, _rows, observed = item
            if (str(entry.data.get(CONF_NODE, "")).lower() != source_node
                    or str(target.data.get(CONF_NODE, "")).lower() != target_node):
                pending.pop(did, None)
                continue
            if selected(cluster, kind, vmid) is False:
                pending.pop(did, None)
                continue
            # Observe a reversal synchronously, before any queued retry can run.
            for owner in hass.config_entries.async_entries(DOMAIN):
                if owner.data.get(CONF_PLATFORM_TYPE) != "PVE" or not fresh(owner, cluster):
                    continue
                node = location(runtime(owner).data, kind, vmid)
                if node == target_node:
                    observed.add(owner.entry_id)
                elif node is not None and owner.entry_id in observed:
                    pending.pop(did, None)
                    break
            section = "vms" if kind == "vm" else "cts"
            if (fresh(entry, cluster)
                    and location(coordinator.data, kind, vmid) != target_node
                    and any(
                        str(guest.get("vmid")) == vmid
                        for guest in (coordinator.data or {}).get(section, {}).values()
                    )):
                pending.pop(did, None)

    @callback
    def retry():
        nonlocal scheduled
        scheduled = None
        if closed:
            return
        invalidate()
        for did, item in list(pending.items()):
            cluster, kind, vmid, target, target_node, identifier, status_id, rows, _observed = item
            source = devices.async_get(did)
            if source is None:
                pending.pop(did, None)
                continue
            if (hass.config_entries.async_get_entry(entry.entry_id) is not entry
                    or hass.config_entries.async_get_entry(target.entry_id) is not target
                    or not fresh(entry, cluster) or not fresh(target, cluster)
                    or selected(cluster, kind, vmid) is not True):
                continue
            if any(location(runtime(owner).data, kind, vmid) != target_node
                   for owner in (entry, target)):
                continue
            if any(location(runtime(owner).data, kind, vmid) not in (None, target_node)
                   for owner in hass.config_entries.async_entries(DOMAIN)
                   if owner.data.get(CONF_PLATFORM_TYPE) == "PVE" and fresh(owner, cluster)):
                continue
            section = "vms" if kind == "vm" else "cts"
            local = (runtime(target).data or {}).get(section, {})
            if not any(str(guest.get("vmid")) == vmid
                       and str(guest.get("node", "")).lower() == target_node
                       for guest in local.values()):
                continue
            # Retain the handoff while waiting for the source local list to catch
            # up. A confirmed reversal is handled by invalidate().
            if any(str(guest.get("vmid")) == vmid
                   for guest in (coordinator.data or {}).get(section, {}).values()):
                continue
            destination = devices.async_get_device_by_identifier(
                identifier, config_entry_id=target.entry_id,
            )
            if (not valid_device(source, entry, identifier)
                    or not valid_device(destination, target, identifier)
                    or destination.id == did):
                continue
            status = registry.async_get(status_id)
            if (status is None or status.config_entry_id != target.entry_id
                    or status.device_id != destination.id):
                continue
            attached = er.async_entries_for_device(
                registry, did, include_disabled_entities=True,
            )
            # Include late-registered buttons/Replication in the completion check.
            for row in attached:
                rows.setdefault(row.entity_id, (row.unique_id, row.config_entry_id))
            if not reconcile_claimed_guest_rows(
                registry, did, destination.id, rows, entry.entry_id,
                target.entry_id, hass.states,
            ):
                continue
            attached = er.async_entries_for_device(
                registry, did, include_disabled_entities=True,
            )
            if attached:
                continue
            complete = True
            for eid, (uid, owner_id) in rows.items():
                row = registry.async_get(eid)
                expected_owner = target.entry_id if owner_id == entry.entry_id else owner_id
                if (row is None or row.unique_id != uid
                        or row.device_id != destination.id
                        or row.config_entry_id != expected_owner):
                    complete = False
                    break
                if owner_id == entry.entry_id and not row.disabled_by:
                    state = hass.states.get(eid)
                    if state is None or "restored" in state.attributes:
                        complete = False
                        break
            if not complete:
                continue
            if dr.async_entries_for_parent_device(devices, did):
                continue
            if any(other.via_device_id == did for other in devices.async_get_devices()):
                continue
            # No await between the final registry checks and this official API.
            pending.pop(did, None)
            devices.async_remove_device(did)

    @callback
    def changed(_event=None):
        nonlocal scheduled
        if closed:
            return
        invalidate()
        if pending and scheduled is None:
            scheduled = hass.loop.call_soon(retry)

    @callback
    def observe_release(kind, cluster, vmid, target_node):
        """Record evidence before the existing release removes live instances."""
        if closed:
            return
        vmid = str(vmid)
        cluster = str(cluster).lower()
        target_node = str(target_node).lower()
        if (target_node == source_node or not fresh(entry, cluster)
                or location(coordinator.data, kind, vmid) != target_node
                or not selected(cluster, kind, vmid)):
            return
        targets = [owner for owner in hass.config_entries.async_entries(DOMAIN)
                   if owner.data.get(CONF_PLATFORM_TYPE) == "PVE"
                   and (scoped_member(owner, cluster) if scoped_member(entry, cluster)
                        else _entry_cluster_id(hass, owner) == cluster)
                   and str(owner.data.get(CONF_NODE, "")).lower() == target_node]
        if len(targets) != 1:
            return
        target = targets[0]
        identifier = (DOMAIN, f"proxmox_{kind}_cluster_{cluster}_{vmid}_v1")
        source = devices.async_get_device_by_identifier(identifier, config_entry_id=entry.entry_id)
        uid = f"pve_cluster_{cluster}_proxmox_{kind}_{cluster}_{vmid}_status_v1".lower().replace(" ", "_")
        status_id = registry.async_get_entity_id("sensor", DOMAIN, uid)
        status = registry.async_get(status_id) if status_id else None
        if (not valid_device(source, entry, identifier) or status is None
                or status.config_entry_id != entry.entry_id or status.device_id != source.id):
            return
        rows = {row.entity_id: (row.unique_id, row.config_entry_id)
                for row in er.async_entries_for_device(registry, source.id, include_disabled_entities=True)}
        pending[source.id] = (
            cluster, kind, vmid, target, target_node, identifier, status_id, rows,
            {entry.entry_id},
        )
        target_coordinator = runtime(target)
        if target_coordinator is not None and target.entry_id not in subscriptions:
            subscriptions[target.entry_id] = target_coordinator.async_add_listener(changed)
        changed()

    @callback
    def close():
        nonlocal closed
        closed = True
        pending.clear()
        if scheduled is not None:
            scheduled.cancel()
        for unsubscribe in subscriptions.values():
            unsubscribe()

    subscriptions[entry.entry_id] = coordinator.async_add_listener(changed)
    subscriptions["entities"] = hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, changed)
    subscriptions["devices"] = hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, changed)
    entry.async_on_unload(close)
    return observe_release
