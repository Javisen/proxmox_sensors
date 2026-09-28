"""Button entities for Proxmox Extended Sensors."""

import asyncio
import logging
import re
import socket
from homeassistant.components.button import ButtonEntity
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers import device_registry as dr
from .pbs_devices import pbs_device_identifier, pbs_parent_device
from homeassistant.helpers import entity_registry as er
from homeassistant.components import persistent_notification

from .logic.guest_cleanup import cleanup_excluded_guest_devices
from .pbs_actions import run_gc, run_prune, run_verify, run_sync
from .const import DOMAIN, CONF_NODE, CONF_PLATFORM_TYPE
from .logic.guest_keys import (
    make_guest_key,
    matches_selected_guest,
    resolve_cluster_id,
    find_guest_node_in_resources,
)
from .logic.guest_selection import (
    get_effective_guest_selections,
    get_entry_guest_selection, selection_guest_ids, _entry_cluster_id,
)
from .logic.guest_identity import (
    guest_button_unique_id,
    guest_device_identifier,
    resolve_legacy_guest_identity,
)
from .logic.guest_identity_diagnostics import warn_ambiguous_guest
from .logic.cluster_scope import guest_identity_context, scoped_migration_target
from .logic.pve_local_identity import (
    coordinator_pve_local_identity_context,
    local_entity_unique_id,
    node_device_identifier,
)

_LOGGER = logging.getLogger(__name__)

GRACE_CYCLES = 3


def _legacy_guest_identity_resolver(hass, entry):
    registry = er.async_get(hass)
    devices = dr.async_get(hass)
    rows = er.async_entries_for_config_entry(registry, entry.entry_id)
    device_rows = dr.async_entries_for_config_entry(devices, entry.entry_id)
    def resolve(kind, vmid, node):
        identity = resolve_legacy_guest_identity(
            kind, vmid, node, rows, device_rows
        )
        if identity.ambiguous:
            warn_ambiguous_guest(
                hass.data[DOMAIN][entry.entry_id], entry.entry_id, kind, vmid, node
            )
        return identity

    return resolve


def _guest_identity_values(identity_context, resolver, kind, vmid, node):
    if identity_context and identity_context.use_scoped_identity:
        return node, None, False
    identity = resolver(kind, vmid, node) if resolver else None
    if identity and identity.ambiguous:
        return node, None, True
    return (identity.node if identity and identity.node else node,
            identity.cluster_id if identity else None, False)


_CT_COMMANDS = [
    ("start", "mdi:play"),
    ("shutdown", "mdi:power"),
    ("stop", "mdi:stop"),
    ("reboot", "mdi:restart"),
]

_VM_COMMANDS = [
    ("start", "mdi:play"),
    ("shutdown", "mdi:power"),
    ("stop", "mdi:stop"),
    ("reboot", "mdi:restart"),
    ("reset", "mdi:restart-alert"),
    ("pause", "mdi:pause"),
    ("hibernate", "mdi:download"),
    ("resume", "mdi:play-pause"),
]


def _pbs_last_action_unique_id(server_id: str, datastore: str) -> str:
    return f"pbs_{server_id.lower()}_{datastore.lower()}_last_action"


def _pbs_maintenance_button_unique_id(
    server_id: str, datastore: str, command_name: str
) -> str:
    return f"pbs_{server_id.lower()}_{datastore.lower()}_{command_name}"


def _reconcile_pbs_button_unique_ids(ent_reg, entry, server_id: str, datastores) -> None:
    for datastore in datastores:
        for command_name in ("gc", "prune", "verify", "sync"):
            legacy_unique_id = f"{datastore.lower()}_{command_name}"
            scoped_unique_id = _pbs_maintenance_button_unique_id(
                server_id, datastore, command_name
            )

            legacy_entity_id = ent_reg.async_get_entity_id(
                "button", DOMAIN, legacy_unique_id
            )
            if not legacy_entity_id:
                continue

            legacy_entry = ent_reg.async_get(legacy_entity_id)
            if legacy_entry is None or legacy_entry.config_entry_id != entry.entry_id:
                continue

            target_entity_id = ent_reg.async_get_entity_id(
                "button", DOMAIN, scoped_unique_id
            )
            if target_entity_id == legacy_entity_id:
                continue

            if target_entity_id:
                target_entry = ent_reg.async_get(target_entity_id)
                _LOGGER.warning(
                    "Cannot migrate PBS button unique_id %s -> %s for %s: "
                    "target already belongs to %s",
                    legacy_unique_id,
                    scoped_unique_id,
                    entry.entry_id,
                    target_entry.config_entry_id if target_entry else target_entity_id,
                )
                continue

            ent_reg.async_update_entity(
                legacy_entity_id, new_unique_id=scoped_unique_id
            )
            _LOGGER.info(
                "Migrated PBS button unique_id %s -> %s",
                legacy_unique_id,
                scoped_unique_id,
            )


def _excluded_guest_buttons(hass, entry, data, registry):
    """Return exact registry rows authorized by an explicit cluster exclusion."""
    if entry.data.get(CONF_PLATFORM_TYPE) != "PVE" or data.get("cluster_resources_ok") is not True:
        return []
    cluster = data.get("cluster_id")
    if not isinstance(cluster, str) or not cluster.strip():
        return []
    cluster = cluster.lower()
    if _entry_cluster_id(hass, entry) != cluster:
        return []
    safe = {"vm": True, "ct": True}
    for other in hass.config_entries.async_entries(DOMAIN):
        if other.data.get(CONF_PLATFORM_TYPE) != "PVE":
            continue
        membership = _entry_cluster_id(hass, other)
        if membership is None:
            return []
        if membership != cluster:
            continue
        for kind, key in (("vm", "selected_vms"), ("ct", "selected_cts")):
            try:
                values = get_entry_guest_selection(other, key)
                safe[kind] &= selection_guest_ids(values) is not None
            except (ValueError, TypeError):
                safe[kind] = False
    # Validate before the existing union helper, which accepts legacy iterables.
    if not any(safe.values()):
        return []
    try:
        vms, cts = get_effective_guest_selections(hass, entry, cluster)
        selections = {"vm": vms, "ct": cts}
        selected = {kind: selection_guest_ids(values) if safe[kind] else None
                    for kind, values in selections.items()}
    except (ValueError, TypeError):
        return []
    pattern = re.compile(r"proxmox_(vm|ct)_cluster_" + re.escape(cluster)
                         + r"_([0-9]+)_([a-z]+)")
    excluded = []
    for row in er.async_entries_for_config_entry(registry, entry.entry_id):
        if row.domain != "button" or row.platform != DOMAIN:
            continue
        match = pattern.fullmatch(row.unique_id or "")
        if not match:
            continue
        kind, vmid, command = match.groups()
        commands = _VM_COMMANDS if kind == "vm" else _CT_COMMANDS
        if command not in {cmd for cmd, _icon in commands}:
            continue
        if selected[kind] is not None and vmid not in selected[kind]:
            excluded.append(row)
    return excluded


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up button entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    if data.get("server_type") == "PVE":
        client = getattr(coordinator, "client", data.get("client"))
    else:
        client = data.get("client")

    selected_vms = entry.options.get(
        "selected_vms", entry.data.get("selected_vms", None)
    )
    selected_cts = entry.options.get(
        "selected_cts", entry.data.get("selected_cts", None)
    )
    enable_node_controls = entry.options.get(
        "enable_node_controls", entry.data.get("enable_node_controls", True)
    )

    node = entry.data.get(CONF_NODE, "Proxmox")
    server_type = entry.data.get(CONF_PLATFORM_TYPE, "PVE")
    features = data.get("features", {})

    entities = []
    c_data = coordinator.data

    if not c_data:
        _LOGGER.warning("No data found in coordinator for %s", node)
        return

    cluster_id = resolve_cluster_id(hass, c_data)
    identity_context = guest_identity_context(entry, cluster_id)
    resolver_factory = globals().get("_legacy_guest_identity_resolver")
    legacy_identity_resolver = resolver_factory(hass, entry) if resolver_factory else None
    effective_selected_vms, effective_selected_cts = get_effective_guest_selections(
        hass, entry, cluster_id, selected_vms, selected_cts
    )

    # ========= PVE BUTTONS ===================
    if server_type == "PVE":

        device_registry = dr.async_get(hass)
        local_identity = coordinator_pve_local_identity_context(coordinator)
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(
                DOMAIN, node_device_identifier(local_identity, node)
            )},
            manufacturer="Proxmox",
            model="Proxmox Node",
            name=f"1. Node: {node}",
        )

        entry = coordinator.config_entry
        wol_macs = entry.options.get("wol_macs", {})

        # -------- NODE CONTROL BUTTONS --------
        if enable_node_controls:
            entities.append(
                ProxmoxNodeButton(
                    coordinator, client, node, "Node", "reboot", "mdi:restart"
                )
            )
            entities.append(
                ProxmoxNodeButton(
                    coordinator, client, node, "Node", "shutdown", "mdi:power"
                )
            )

        # -------- WOL BUTTON --------
        if wol_macs.get(node):
            entities.append(
                ProxmoxNodeButton(
                    coordinator, client, node, "Node", "wake", "mdi:power-on"
                )
            )

        # LXC buttons
        if features.get("enable_cts", True):
            ct_map = c_data.get("cts", {})
            for ct_key, ct_data in ct_map.items():
                ct_id = ct_data.get("vmid", ct_key)
                ct_node = ct_data.get("node", node)
                if matches_selected_guest(
                    effective_selected_cts, ct_node, ct_id, ct_key
                ):
                    identity_node, identity_cluster, ambiguous = _guest_identity_values(
                        identity_context, legacy_identity_resolver, "ct", ct_id, ct_node
                    )
                    if ambiguous:
                        continue
                    label = ct_data.get("name", ct_id)

                    ct_commands = _CT_COMMANDS

                    for cmd, icon in ct_commands:
                        entities.append(
                            ProxmoxContainerButton(
                                coordinator,
                                client,
                                ct_id,
                                identity_node,
                                label,
                                cmd,
                                icon,
                                guest_key=ct_key,
                                cluster_id=identity_cluster,
                                identity_context=identity_context,
                            )
                        )

        # VM buttons
        if features.get("enable_vms", True):
            vm_map = c_data.get("vms", {})
            for vm_key, vm_data in vm_map.items():
                vm_id = vm_data.get("vmid", vm_key)
                vm_node = vm_data.get("node", node)
                if matches_selected_guest(
                    effective_selected_vms, vm_node, vm_id, vm_key
                ):
                    identity_node, identity_cluster, ambiguous = _guest_identity_values(
                        identity_context, legacy_identity_resolver, "vm", vm_id, vm_node
                    )
                    if ambiguous:
                        continue
                    label = vm_data.get("name", vm_id)

                    vm_commands = _VM_COMMANDS

                    for cmd, icon in vm_commands:
                        entities.append(
                            ProxmoxVMButton(
                                coordinator,
                                client,
                                vm_id,
                                identity_node,
                                label,
                                cmd,
                                icon,
                                guest_key=vm_key,
                                cluster_id=identity_cluster,
                                identity_context=identity_context,
                            )
                        )

    # ========PBS BUTTONS====================
    elif server_type == "PBS":
        server_id = entry.data.get("server_id", "pbs_main")
        datastores = c_data.get("pbs_datastores", {})
        ent_reg = er.async_get(hass)

        _reconcile_pbs_button_unique_ids(
            ent_reg, entry, server_id, datastores.keys()
        )

        prune_jobs_by_datastore = entry.options.get(
            "pbs_prune_jobs_by_datastore", {}
        )
        verify_jobs_by_datastore = entry.options.get(
            "pbs_verify_jobs_by_datastore", {}
        )
        sync_jobs_by_datastore = entry.options.get(
            "pbs_sync_jobs_by_datastore", {}
        )

        for datastore_name in datastores.keys():
            entities.append(PBSGCButton(coordinator, client, server_id, datastore_name))

            entities.append(
                PBSPruneButton(
                    coordinator,
                    client,
                    server_id,
                    datastore_name,
                    prune_jobs_by_datastore.get(datastore_name),
                )
            )

            verify_job_id = next(
                (
                    job.get("id")
                    for job in coordinator.data.get("pbs_jobs", {}).get("verify", [])
                    if job.get("store") == datastore_name
                ),
                None,
            )

            entities.append(
                PBSVerifyButton(
                    coordinator,
                    client,
                    server_id,
                    datastore_name,
                    verify_job_id,
                )
            )

            entities.append(
                PBSSyncButton(
                    coordinator,
                    client,
                    server_id,
                    datastore_name,
                    sync_jobs_by_datastore.get(datastore_name),
                )
            )
        # -------- WOL BUTTON --------
        mac = entry.data.get("wol_mac")

        if mac:
            entities.append(PBSWakeButton(coordinator, client, server_id))

        # -------- NODE CONTROL BUTTONS --------
        enable_pbs_node_controls = entry.options.get(
            "enable_pbs_node_controls",
            entry.data.get("enable_pbs_node_controls", True),
        )

        if enable_pbs_node_controls:
            entities.append(PBSShutdownButton(coordinator, client, server_id))
            entities.append(PBSRebootButton(coordinator, client, server_id))

    if server_type == "PVE":
        registry = er.async_get(hass)
        for row in _excluded_guest_buttons(hass, entry, c_data, registry):
            registry.async_remove(row.entity_id)
        cleanup_excluded_guest_devices(hass)

    _LOGGER.info("Total button entities created: %d", len(entities))
    async_add_entities(entities)

    if server_type == "PVE":
        known_button_ids = {
            getattr(e, "_attr_unique_id", None)
            for e in entities
            if isinstance(e, (ProxmoxVMButton, ProxmoxContainerButton))
            and not ((identity_context and identity_context.use_scoped_identity)
                     or (cluster_id and getattr(e, "_cluster_id", None)))
        }
        known_button_ids.discard(None)

        initial_pending_groups = _group_existing_button_entities_by_guest(
            entities, cluster_id, identity_context
        )

        _setup_guest_button_reconciliation(
            hass,
            entry,
            coordinator,
            async_add_entities,
            node,
            client,
            effective_selected_vms,
            effective_selected_cts,
            features,
            known_button_ids,
            initial_pending_groups=initial_pending_groups,
        )


def _guest_identity_key(kind: str, cluster_id: str, vmid) -> str:
    """Stable, node-independent identity for a guest: kind + cluster + vmid."""
    return f"{kind}:{cluster_id}:{vmid}"


def _build_guest_button_groups(
    coordinator, client, c_data, node, selected_vms, selected_cts, features, cluster_id,
    identity_context, legacy_identity_resolver=None,
) -> dict:

    groups: dict = {}
    if not cluster_id and not (identity_context and identity_context.use_scoped_identity):
        return groups

    if features.get("enable_cts", True):
        ct_map = c_data.get("cts", {})
        for ct_key, ct_data in ct_map.items():
            ct_id = ct_data.get("vmid", ct_key)
            ct_node = ct_data.get("node", node)
            if not matches_selected_guest(selected_cts, ct_node, ct_id, ct_key):
                continue
            identity_node, identity_cluster, ambiguous = _guest_identity_values(
                identity_context, legacy_identity_resolver, "ct", ct_id, ct_node
            )
            if ambiguous:
                continue
            label = ct_data.get("name", ct_id)
            buttons = [
                ProxmoxContainerButton(
                    coordinator,
                    client,
                    ct_id,
                    identity_node,
                    label,
                    cmd,
                    icon,
                    guest_key=ct_key,
                    cluster_id=identity_cluster,
                    identity_context=identity_context,
                )
                for cmd, icon in _CT_COMMANDS
            ]
            scope = identity_context.scope if identity_context and identity_context.use_scoped_identity else (
                identity_cluster or identity_node
            )
            groups[_guest_identity_key("ct", scope, ct_id)] = buttons

    if features.get("enable_vms", True):
        vm_map = c_data.get("vms", {})
        for vm_key, vm_data in vm_map.items():
            vm_id = vm_data.get("vmid", vm_key)
            vm_node = vm_data.get("node", node)
            if not matches_selected_guest(selected_vms, vm_node, vm_id, vm_key):
                continue
            identity_node, identity_cluster, ambiguous = _guest_identity_values(
                identity_context, legacy_identity_resolver, "vm", vm_id, vm_node
            )
            if ambiguous:
                continue
            label = vm_data.get("name", vm_id)
            buttons = [
                ProxmoxVMButton(
                    coordinator,
                    client,
                    vm_id,
                    identity_node,
                    label,
                    cmd,
                    icon,
                    guest_key=vm_key,
                    cluster_id=identity_cluster,
                    identity_context=identity_context,
                )
                for cmd, icon in _VM_COMMANDS
            ]
            scope = identity_context.scope if identity_context and identity_context.use_scoped_identity else (
                identity_cluster or identity_node
            )
            groups[_guest_identity_key("vm", scope, vm_id)] = buttons

    return groups


def _group_existing_button_entities_by_guest(entities, cluster_id, identity_context=None) -> dict:

    groups: dict = {}
    scoped = bool(identity_context and identity_context.use_scoped_identity)
    if not cluster_id and not scoped:
        return groups

    for e in entities:
        scope = identity_context.scope if scoped else getattr(e, "_cluster_id", None)
        if not scope:
            continue
        if isinstance(e, ProxmoxVMButton):
            kind = "vm"
        elif isinstance(e, ProxmoxContainerButton):
            kind = "ct"
        else:
            continue
        gkey = _guest_identity_key(kind, scope, e._vmid)
        groups.setdefault(gkey, []).append(e)

    return groups


def _setup_guest_button_reconciliation(
    hass,
    entry,
    coordinator,
    async_add_entities,
    node,
    client,
    selected_vms,
    selected_cts,
    features,
    known_unique_ids: set,
    initial_pending_groups: dict | None = None,
):

    pending_groups: dict = dict(initial_pending_groups or {})
    live_guest_instances: dict = {}
    missing_everywhere_counter: dict = {}
    deleting_groups: dict = {}
    async def _delete_excluded(entities, rows, registry):
        for entity in entities:
            if getattr(entity, "hass", None) is not None:
                await entity.async_remove(force_remove=True)
        for row in rows:
            current = registry.async_get(row.entity_id)
            if (current is not None and current.unique_id == row.unique_id
                    and current.config_entry_id == entry.entry_id):
                registry.async_remove(row.entity_id)
        cleanup_excluded_guest_devices(hass)

    @callback
    def _reconcile():
        c_data = coordinator.data or {}
        cluster_id = resolve_cluster_id(hass, c_data)
        identity_context = guest_identity_context(entry, cluster_id)
        ent_reg = er.async_get(hass)
        resolver_factory = globals().get("_legacy_guest_identity_resolver")
        legacy_identity_resolver = resolver_factory(hass, entry) if resolver_factory else None

        if not cluster_id and not identity_context.use_scoped_identity:
            return

        effective_selected_vms, effective_selected_cts = get_effective_guest_selections(
            hass, entry, cluster_id, selected_vms, selected_cts
        )
        current_groups = _build_guest_button_groups(
            coordinator,
            client,
            c_data,
            node,
            effective_selected_vms,
            effective_selected_cts,
            features,
            cluster_id,
            identity_context,
            legacy_identity_resolver,
        )

        for gkey, task in list(deleting_groups.items()):
            if task.done() and not task.cancelled() and task.exception() is None:
                del deleting_groups[gkey]
        excluded = {}
        for row in _excluded_guest_buttons(hass, entry, c_data, ent_reg):
            match = re.fullmatch(
                r"proxmox_(vm|ct)_cluster_" + re.escape(cluster_id.lower())
                + r"_([0-9]+)_[a-z]+", row.unique_id
            )
            gkey = _guest_identity_key(match[1], cluster_id, match[2])
            excluded.setdefault(gkey, []).append(row)
        for gkey, rows in excluded.items():
            current_groups.pop(gkey, None)
            if gkey in deleting_groups:
                continue
            entities = live_guest_instances.pop(gkey, []) + pending_groups.pop(gkey, [])
            known_unique_ids.difference_update(row.unique_id for row in rows)
            missing_everywhere_counter.pop(gkey, None)
            deleting_groups[gkey] = hass.async_create_task(
                _delete_excluded(entities, rows, ent_reg)
            )

        for gkey, ents in list(pending_groups.items()):
            all_confirmed = all(
                (
                    reg_entity_id := ent_reg.async_get_entity_id(
                        "button", DOMAIN, e._attr_unique_id
                    )
                )
                and (reg_entry := ent_reg.async_get(reg_entity_id))
                and reg_entry.config_entry_id == entry.entry_id
                for e in ents
            )
            if all_confirmed:
                live_guest_instances[gkey] = ents
                known_unique_ids.update(e._attr_unique_id for e in ents)
                del pending_groups[gkey]
                _LOGGER.info(
                    "Guest buttons %s confirmed claimed by this entry (%s)",
                    gkey,
                    node,
                )
                continue

            was_rejected = any(
                getattr(e, "registry_entry", None) is None for e in ents
            )
            if was_rejected:
                _LOGGER.info(
                    "Guest buttons %s lost the claim race last cycle; "
                    "discarding rejected instances so they can be retried "
                    "this cycle",
                    gkey,
                )
                del pending_groups[gkey]

        # ---- Step 2: migration / disappearance classification. ----
        cluster_resources = c_data.get("cluster_resources", [])
        cluster_resources_ok = c_data.get("cluster_resources_ok", True)
        configured_pve_nodes = {
            (e.data.get(CONF_NODE) or "").lower()
            for e in hass.config_entries.async_entries(DOMAIN)
            if e.data.get(CONF_PLATFORM_TYPE) == "PVE"
        }

        for gkey in list(live_guest_instances.keys()):
            if gkey in current_groups:
                missing_everywhere_counter.pop(gkey, None)
                continue

            kind, _cluster, vmid_str = gkey.split(":", 2)
            located_node = find_guest_node_in_resources(
                cluster_resources, kind, vmid_str
            )

            if (
                located_node
                and located_node.lower() != node.lower()
                and located_node.lower() in configured_pve_nodes
            ):
                target_entry = None
                if identity_context and identity_context.use_scoped_identity:
                    target_entry = scoped_migration_target(
                        entry, hass.config_entries.async_entries(DOMAIN), located_node
                    )
                    if target_entry is None:
                        continue
                _LOGGER.info(
                    "Guest buttons %s %s migrated from %s to %s; releasing "
                    "local instances via entity.async_remove(force_remove="
                    "False) - Entity Registry untouched",
                    kind,
                    vmid_str,
                    node,
                    located_node,
                )
                entities_to_release = live_guest_instances.pop(gkey)
                for entity_obj in entities_to_release:
                    if getattr(entity_obj, "hass", None) is None:
                        continue
                    hass.async_create_task(entity_obj.async_remove(force_remove=False))
                known_unique_ids.difference_update(
                    e._attr_unique_id for e in entities_to_release
                )
                missing_everywhere_counter.pop(gkey, None)
                continue

            if not cluster_resources_ok:
                continue

            missing_everywhere_counter[gkey] = (
                missing_everywhere_counter.get(gkey, 0) + 1
            )
            if missing_everywhere_counter[gkey] >= GRACE_CYCLES:
                _LOGGER.info(
                    "Guest buttons %s %s missing for %d consecutive cycles "
                    "(not found locally or in cluster_resources). No action "
                    "taken: entity instances and Entity Registry left "
                    "exactly as-is, per design.",
                    kind,
                    vmid_str,
                    GRACE_CYCLES,
                )

        def _group_ready_to_claim(ents) -> bool:
            for entity_obj in ents:
                reg_entity_id = ent_reg.async_get_entity_id(
                    "button", DOMAIN, entity_obj._attr_unique_id
                )
                if not reg_entity_id:
                    continue

                reg_entry = ent_reg.async_get(reg_entity_id)
                if reg_entry and reg_entry.config_entry_id == entry.entry_id:
                    continue

                state = hass.states.get(reg_entity_id)
                if state is None or "restored" in state.attributes:
                    continue

                return False

            return True

        # ---- Step 3: (re)submit any guest not yet known to be live or
        # already awaiting confirmation. ----
        for gkey, ents in current_groups.items():
            if gkey in deleting_groups:
                continue
            if gkey in live_guest_instances or gkey in pending_groups:
                continue
            if not _group_ready_to_claim(ents):
                continue
            pending_groups[gkey] = ents
            async_add_entities(ents)

    entry.async_on_unload(coordinator.async_add_listener(_reconcile))


# =======PBS BUTTON CLASSES=============


class PBSBaseButton(CoordinatorEntity, ButtonEntity):
    """Base class for PBS maintenance buttons."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator, client, server_id, datastore, command_name, command_display
    ):
        super().__init__(coordinator)

        self._client = client
        self._server_id = server_id.lower()
        self._datastore = datastore

        self._last_action_unique_id = _pbs_last_action_unique_id(
            self._server_id, datastore
        )

        self._command_name = command_name
        self._command_display = command_display

        self._attr_unique_id = _pbs_maintenance_button_unique_id(
            self._server_id, datastore, command_name
        )
        self._attr_translation_key = f"pbs_{command_name}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, pbs_device_identifier("maintenance", self._server_id, datastore))},
            "via_device_id": pbs_parent_device(self.coordinator),
            "name": f"Maintenance: {datastore}",
            "manufacturer": "Proxmox",
            "model": "Proxmox Backup Server",
        }

    @property
    def available(self):
        return self.coordinator.last_update_success

    def _update_last_action(self, message: str):
        ent_reg = er.async_get(self.hass)
        entity_id = ent_reg.async_get_entity_id(
            "sensor", DOMAIN, self._last_action_unique_id
        )
        if not entity_id:
            _LOGGER.debug(
                "PBS LastAction sensor %s not found for datastore %s",
                self._last_action_unique_id,
                self._datastore,
            )
            return

        registry_entry = ent_reg.async_get(entity_id)
        current_entry_id = self.coordinator.config_entry.entry_id
        if registry_entry and registry_entry.config_entry_id != current_entry_id:
            _LOGGER.warning(
                "Not updating PBS LastAction sensor %s: it belongs to %s, not %s",
                entity_id,
                registry_entry.config_entry_id,
                current_entry_id,
            )
            return

        self.hass.states.async_set(entity_id, message)

    def _accept_action_upid(self, result) -> bool:
        """Remember the last accepted task, without claiming it has completed."""
        action = "GC" if self._command_name == "gc" else self._command_name.title()
        if not isinstance(result, str) or not result.startswith("UPID:"):
            self.hass.data[DOMAIN][self.coordinator.config_entry.entry_id].get(
                "pbs_action_upids", {}
            ).get(self._server_id, {}).get(self._datastore, {}).pop(
                self._command_name, None
            )
            _LOGGER.error(
                "PBS %s: %s failed to start for datastore %s: invalid UPID response",
                self._server_id, action, self._datastore,
            )
            self._update_last_action(f"{action} failed")
            return False

        entry_id = self.coordinator.config_entry.entry_id
        accepted = self.hass.data[DOMAIN][entry_id].setdefault("pbs_action_upids", {})
        actions = accepted.setdefault(self._server_id, {}).setdefault(self._datastore, {})
        # Dict order records acceptance order, including a repeated action.
        actions.pop(self._command_name, None)
        actions[self._command_name] = result
        self._update_last_action(f"{action} Iniciado")
        return True


class PBSGCButton(PBSBaseButton):
    """Garbage Collection button for PBS datastore."""

    def __init__(self, coordinator, client, server_id, datastore):
        super().__init__(
            coordinator, client, server_id, datastore, "gc", "Garbage Collect"
        )
        self._attr_icon = "mdi:recycle"

    async def async_press(self):
        upid = await run_gc(self._client, self.hass, self._datastore)
        if not self._accept_action_upid(upid):
            return
        await self.coordinator.async_request_refresh()


class PBSPruneButton(PBSBaseButton):
    """Prune button for PBS datastore."""

    def __init__(self, coordinator, client, server_id, datastore, job_id=None):
        super().__init__(coordinator, client, server_id, datastore, "prune", "Prune")
        self._job_id = job_id
        self._attr_icon = "mdi:delete-sweep"

    async def async_press(self):
        jobs = self.coordinator.data.get("pbs_jobs", {}).get("prune", [])
        candidates = {
            job["id"] for job in jobs
            if isinstance(job, dict) and job.get("store") == self._datastore
            and isinstance(job.get("id"), str) and job["id"]
        }
        legacy_id = self.coordinator.config_entry.options.get(
            "pbs_prune_jobs_by_datastore", {}
        ).get(self._datastore)
        if isinstance(legacy_id, str) and legacy_id in candidates:
            job_id = legacy_id
        elif len(candidates) == 1:
            job_id = next(iter(candidates))
        elif not candidates:
            message = f"No Prune Job discovered for {self._datastore}"
            _LOGGER.warning("PBS: %s", message)
            self._update_last_action(message)
            return
        else:
            message = f"Prune ambiguous: multiple jobs discovered for {self._datastore}"
            _LOGGER.warning("PBS: %s", message)
            self._update_last_action(message)
            return

        upid = await run_prune(self._client, self.hass, self._datastore, job_id)
        if not self._accept_action_upid(upid):
            return

        await self.coordinator.async_request_refresh()


class PBSVerifyButton(PBSBaseButton):
    """Verify button for PBS datastore."""

    def __init__(self, coordinator, client, server_id, datastore, job_id=None):
        super().__init__(coordinator, client, server_id, datastore, "verify", "Verify")
        self._job_id = job_id
        self._attr_icon = "mdi:check-decagram"

    async def async_press(self):
        if not self._job_id:
            _LOGGER.warning("PBS: Verify not configured for %s", self._datastore)
            self._update_last_action("Verify not configured")
            return

        upid = await run_verify(
            self._client,
            self.hass,
            self._datastore,
            self._job_id,
        )

        if not self._accept_action_upid(upid):
            return

        await self.coordinator.async_request_refresh()


class PBSSyncButton(PBSBaseButton):
    """Sync button for PBS datastore."""

    def __init__(self, coordinator, client, server_id, datastore, job_id=None):
        super().__init__(coordinator, client, server_id, datastore, "sync", "Sync")
        self._job_id = job_id
        self._attr_icon = "mdi:sync"

    async def async_press(self):
        jobs = self.coordinator.data.get("pbs_jobs", {}).get("sync", [])
        candidates = {
            job["id"] for job in jobs
            if isinstance(job, dict) and job.get("store") == self._datastore
            and isinstance(job.get("id"), str) and job["id"]
        }
        legacy_id = self.coordinator.config_entry.options.get(
            "pbs_sync_jobs_by_datastore", {}
        ).get(self._datastore)
        if isinstance(legacy_id, str) and legacy_id in candidates:
            job_id = legacy_id
        elif len(candidates) == 1:
            job_id = next(iter(candidates))
        elif not candidates:
            message = f"No Sync Job discovered for {self._datastore}"
            _LOGGER.warning("PBS: %s", message)
            self._update_last_action(message)
            return
        else:
            message = f"Sync ambiguous: multiple jobs discovered for {self._datastore}"
            _LOGGER.warning("PBS: %s", message)
            self._update_last_action(message)
            return

        upid = await run_sync(
            self._client,
            self.hass,
            self._datastore,
            job_id,
        )

        if not self._accept_action_upid(upid):
            return

        await self.coordinator.async_request_refresh()


# =======PBS NODE BUTTON CLASSES=============


class PBSNodeBaseButton(CoordinatorEntity, ButtonEntity):
    """Base class for PBS node control buttons (shutdown/reboot)."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator, client, server_id, command_name, command_display, icon
    ):
        super().__init__(coordinator)
        self._client = client
        self._server_id = server_id
        self._command_name = command_name
        self._command_display = command_display

        self._attr_unique_id = f"pbs_{server_id}_node_{command_name}"
        self._attr_translation_key = f"pbs_node_{command_name}"
        self._attr_icon = icon

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"pbs_server_{server_id.lower()}")},
            "name": f"PBS Server: {server_id}",
            "manufacturer": "Proxmox",
            "model": "Proxmox Backup Server",
        }

    @property
    def available(self):
        return self.coordinator.last_update_success

    async def async_press(self):
        """Execute node command on PBS."""
        try:
            # For PBS, the node is always "localhost" as it's a single node system
            node = "localhost"

            # Execute the command using the client
            result = await self._client.execute_pbs_node_command(
                self.hass, node, self._command_name
            )

            if result:
                _LOGGER.info(
                    "PBS node command %s accepted on %s",
                    self._command_name,
                    self._server_id,
                )
                try:
                    await asyncio.sleep(3)
                    await self.coordinator.async_request_refresh()
                    self.async_write_ha_state()
                except Exception as refresh_error:
                    _LOGGER.debug(
                        "PBS status refresh after accepted %s on %s: %s",
                        self._command_name, self._server_id, refresh_error,
                    )
            else:
                _LOGGER.error(
                    "PBS node command %s failed on %s",
                    self._command_name,
                    self._server_id,
                )

        except Exception as e:
            _LOGGER.error(
                "Error executing PBS node command %s on %s: %s",
                self._command_name,
                self._server_id,
                e,
            )


class PBSShutdownButton(PBSNodeBaseButton):
    """Shutdown button for PBS node."""

    def __init__(self, coordinator, client, server_id):
        super().__init__(
            coordinator, client, server_id, "shutdown", "Shutdown", "mdi:power"
        )


class PBSRebootButton(PBSNodeBaseButton):
    """Reboot button for PBS node."""

    def __init__(self, coordinator, client, server_id):
        super().__init__(
            coordinator, client, server_id, "reboot", "Reboot", "mdi:restart"
        )


class PBSWakeButton(PBSNodeBaseButton):
    """Wake (WOL) button for PBS node."""

    def __init__(self, coordinator, client, server_id):
        super().__init__(
            coordinator,
            client,
            server_id,
            "wake",
            "Wake",
            "mdi:power-on",
        )

    def _wol_mac(self):
        mac = self.coordinator.config_entry.data.get("wol_mac")
        if not isinstance(mac, str):
            return None
        mac = mac.strip()
        if not re.fullmatch(r"(?:[0-9a-fA-F]{12}|[0-9a-fA-F]{2}([:-])(?:[0-9a-fA-F]{2}\1){4}[0-9a-fA-F]{2})", mac):
            return None
        compact = mac.replace(":", "").replace("-", "").lower()
        if compact == "000000000000" or int(compact[:2], 16) & 1:
            return None
        return ":".join(compact[i:i + 2] for i in range(0, 12, 2))

    @property
    def available(self):
        return self._wol_mac() is not None

    async def async_press(self):
        """Send WOL packet."""
        try:
            mac = self._wol_mac()

            if not mac:
                _LOGGER.error("No valid MAC configured for PBS %s", self._server_id)
                return

            _LOGGER.info("Sending WOL to PBS %s (%s)", self._server_id, mac)

            await self.hass.async_add_executor_job(
                ProxmoxNodeButton._send_magic_packet, mac
            )

            persistent_notification.create(
                self.hass,
                f"WOL sent to PBS {self._server_id} ({mac})",
                "Proxmox PBS Wake",
            )

        except Exception as e:
            _LOGGER.error("Error sending WOL to PBS %s: %s", self._server_id, e)

            persistent_notification.create(
                self.hass,
                f"Error sending WOL to PBS {self._server_id}: {e}",
                "Proxmox PBS Wake ERROR",
            )


# =======PVE BUTTON CLASSES=========


class ProxmoxBaseButton(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        client,
        vmid,
        node,
        label,
        command,
        icon,
        guest_type=None,
        guest_key=None,
        cluster_id=None,
        identity_context=None,
    ):
        super().__init__(coordinator)
        self._client = client
        self._vmid = vmid
        self._node = node
        self._label = label
        self._command = command
        self._guest_type = guest_type
        self._guest_key = guest_key or make_guest_key(node, vmid)
        self._cluster_id = str(cluster_id).lower() if cluster_id else None
        self._identity_context = identity_context

        if identity_context and identity_context.use_scoped_identity:
            self._attr_unique_id = guest_button_unique_id(identity_context.scope, guest_type or "guest", vmid, command)
        elif self._cluster_id:
            # Node-independent identity: survives live migrations, mirrors
            # the scheme used by sensor/vm.py and sensor/ct.py.
            self._attr_unique_id = (
                f"proxmox_{guest_type or 'guest'}_cluster_{self._cluster_id}_{vmid}_{command}"
            )
        else:
            # Standalone node (no cluster context available): legacy id.
            self._attr_unique_id = f"proxmox_{node}_{vmid}_{command}"

        self._attr_translation_key = f"{guest_type or 'guest'}_{command}"
        self._attr_translation_placeholders = {"name": str(label)}
        self._attr_icon = icon

    def _resolve_current_node(self, c_data, guest_type):
        guest_map = c_data.get("vms" if guest_type == "vm" else "cts", {})
        guest_data = (
            guest_map.get(self._guest_key)
            or guest_map.get(str(self._vmid))
            or guest_map.get(self._vmid)
        )
        if guest_data and guest_data.get("node"):
            return guest_data["node"]

        cluster_resources = c_data.get("cluster_resources", [])
        located_node = find_guest_node_in_resources(
            cluster_resources, guest_type, self._vmid
        )
        if located_node:
            return located_node

        _LOGGER.warning(
            "Could not resolve current node for guest %s (%s); falling "
            "back to %s",
            self._vmid,
            guest_type,
            self._node,
        )
        return self._node

    async def async_press(self):
        try:
            data = self.coordinator.data or {}
            guest_type = self._guest_type

            if guest_type is None:
                vm_map = data.get("vms", {})
                ct_map = data.get("cts", {})
                if (
                    self._guest_key in vm_map
                    or str(self._vmid) in vm_map
                    or self._vmid in vm_map
                ):
                    guest_type = "vm"
                elif (
                    self._guest_key in ct_map
                    or str(self._vmid) in ct_map
                    or self._vmid in ct_map
                ):
                    guest_type = "ct"
                else:
                    _LOGGER.error(
                        "Guest %s (%s) not found in coordinator data",
                        self._vmid,
                        self._guest_key,
                    )
                    return

            current_node = self._resolve_current_node(data, guest_type)

            result = False
            if guest_type == "vm":
                result = await self._client.execute_vm_command(
                    self.hass, current_node, self._vmid, self._command
                )
            else:
                result = await self._client.execute_ct_command(
                    self.hass, current_node, self._vmid, self._command
                )

            if result:
                await asyncio.sleep(2)
                await self.coordinator.async_request_refresh()
                self.async_write_ha_state()
                _LOGGER.info("Command %s completed for %s", self._command, self._vmid)
            else:
                _LOGGER.error("Command %s failed for %s", self._command, self._vmid)

        except Exception as e:
            _LOGGER.error("Error executing command on %s: %s", self._vmid, e)


class ProxmoxVMButton(ProxmoxBaseButton):
    def __init__(
        self,
        coordinator,
        client,
        vmid,
        node,
        label,
        command,
        icon,
        guest_key=None,
        cluster_id=None,
        identity_context=None,
    ):
        super().__init__(
            coordinator,
            client,
            vmid,
            node,
            label,
            command,
            icon,
            guest_type="vm",
            guest_key=guest_key,
            cluster_id=cluster_id,
            identity_context=identity_context,
        )

    @property
    def device_info(self):
        node_id = self._node.lower()
        vmid = str(self._vmid)
        local_identity = coordinator_pve_local_identity_context(self.coordinator)

        if self._identity_context and self._identity_context.use_scoped_identity:
            identifiers = {(DOMAIN, guest_device_identifier(self._identity_context.scope, "vm", vmid))}
        elif self._cluster_id:
            identifiers = {(DOMAIN, f"proxmox_vm_cluster_{self._cluster_id}_{vmid}_v1")}
        else:
            identifiers = {(DOMAIN, f"proxmox_vm_{node_id}_{vmid}_v1")}

        info = {
            "identifiers": identifiers,
            "manufacturer": "Proxmox",
            "model": "Virtual Machine",
            "name": f"4. VM: {self._label}-({self._vmid})",
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


class ProxmoxContainerButton(ProxmoxBaseButton):
    def __init__(
        self,
        coordinator,
        client,
        vmid,
        node,
        label,
        command,
        icon,
        guest_key=None,
        cluster_id=None,
        identity_context=None,
    ):
        super().__init__(
            coordinator,
            client,
            vmid,
            node,
            label,
            command,
            icon,
            guest_type="ct",
            guest_key=guest_key,
            cluster_id=cluster_id,
            identity_context=identity_context,
        )

    @property
    def device_info(self):
        node_id = self._node.lower()
        vmid = str(self._vmid)
        local_identity = coordinator_pve_local_identity_context(self.coordinator)

        if self._identity_context and self._identity_context.use_scoped_identity:
            identifiers = {(DOMAIN, guest_device_identifier(self._identity_context.scope, "ct", vmid))}
        elif self._cluster_id:
            identifiers = {(DOMAIN, f"proxmox_ct_cluster_{self._cluster_id}_{vmid}_v1")}
        else:
            identifiers = {(DOMAIN, f"proxmox_ct_{node_id}_{vmid}_v1")}

        info = {
            "identifiers": identifiers,
            "manufacturer": "Proxmox",
            "model": "Container",
            "name": f"3. CT: {self._label}-({self._vmid})",
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


class ProxmoxNodeButton(CoordinatorEntity, ButtonEntity):
    def __init__(self, coordinator, client, node, label, command, icon):
        super().__init__(coordinator)
        self._client = client
        self._node = node
        self._command = command
        self._attr_icon = icon

        self._attr_has_entity_name = True
        server_id = coordinator.config_entry.data.get("server_id", "default").lower()
        node_id = node.lower()

        self._attr_unique_id = local_entity_unique_id(
            coordinator_pve_local_identity_context(coordinator),
            server_id,
            f"node_{node_id}_{command}",
        )
        self._attr_translation_key = f"node_{command}"
        self._attr_translation_placeholders = {"name": str(node)}

    @property
    def device_info(self):
        node_id = self._node.lower()

        return {
            "identifiers": {(
                DOMAIN,
                node_device_identifier(
                    coordinator_pve_local_identity_context(self.coordinator),
                    node_id,
                ),
            )},
            "manufacturer": "Proxmox",
            "model": "Proxmox Node",
            "name": f"1. Node: {self._node.capitalize()}",
        }

    def _wol_mac(self):
        macs = self.coordinator.config_entry.options.get("wol_macs", {})
        mac = macs.get(self._node) if isinstance(macs, dict) else None
        if not isinstance(mac, str):
            return None
        mac = mac.strip()
        if not re.fullmatch(r"(?:[0-9a-fA-F]{12}|[0-9a-fA-F]{2}([:-])(?:[0-9a-fA-F]{2}\1){4}[0-9a-fA-F]{2})", mac):
            return None
        compact = mac.replace(":", "").replace("-", "").lower()
        if compact == "000000000000" or int(compact[:2], 16) & 1:
            return None
        return ":".join(compact[i:i + 2] for i in range(0, 12, 2))

    @property
    def available(self):
        if self._command == "wake":
            return self._wol_mac() is not None
        return super().available

    @staticmethod
    def _send_magic_packet(mac):
        payload = b"\xff" * 6 + bytes.fromhex(mac.replace(":", "")) * 16
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(payload, ("255.255.255.255", 9))

    async def async_press(self):
        if self._command == "wake":
            mac = self._wol_mac()
            if mac is None:
                _LOGGER.error("Cannot send WOL to node %s: missing or invalid configured MAC", self._node)
                return
            try:
                await self.hass.async_add_executor_job(self._send_magic_packet, mac)
            except Exception as err:
                _LOGGER.error("Error sending WOL to node %s: %s", self._node, err)
            else:
                _LOGGER.info("WOL packet sent to node %s; startup not confirmed", self._node)
            return

        try:
            if hasattr(self._client, "execute_node_command"):
                result = await self._client.execute_node_command(
                    self.hass, self._node, self._command
                )
            else:
                path = f"nodes/{self._node}/status"
                data = {"command": self._command}
                result = await self._client.post(self.hass, path, data)

            if result:
                await asyncio.sleep(3)
                await self.coordinator.async_request_refresh()
                self.async_write_ha_state()
                _LOGGER.info("Node command %s executed successfully", self._command)
            else:
                _LOGGER.error("Node command %s failed", self._command)

        except Exception as e:
            _LOGGER.error(
                "Error executing %s on node %s: %s", self._command, self._node, e
            )
