"""Guest identity helpers that do not read Home Assistant state or registries."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class LegacyGuestIdentity:
    cluster_id: str | None
    node: str | None
    ambiguous: bool = False


_METRICS = "status|cpu_usage|memory_used|memory_total|disk_total|disk_used|disk_usage|uptime|network_rx|network_tx"


def _legacy_entity_identity(unique_id, kind, vmid):
    if not isinstance(unique_id, str):
        return None
    escaped_kind = re.escape(kind)
    escaped_vmid = re.escape(str(vmid))
    cluster = re.fullmatch(
        rf"pve_cluster_(.+)_proxmox_{escaped_kind}_\1_{escaped_vmid}_(?:{_METRICS})_v1",
        unique_id.lower(),
    )
    if cluster:
        return ("cluster", cluster[1])
    cluster_button = re.fullmatch(
        rf"proxmox_{escaped_kind}_cluster_(.+)_{escaped_vmid}_(?:start|shutdown|stop|reboot|reset|pause|hibernate|resume)",
        unique_id.lower(),
    )
    if cluster_button:
        return ("cluster", cluster_button[1])
    node = re.fullmatch(
        rf"pve_.+?_proxmox_{escaped_kind}_(.+)_{escaped_vmid}_(?:{_METRICS})_v1",
        unique_id.lower(),
    )
    return ("node", node[1]) if node else None


def _legacy_device_identity(identifiers, kind, vmid):
    escaped_kind = re.escape(kind)
    escaped_vmid = re.escape(str(vmid))
    result = set()
    for _domain, identifier in identifiers or ():
        if not isinstance(identifier, str):
            continue
        cluster = re.fullmatch(rf"proxmox_{escaped_kind}_cluster_(.+)_{escaped_vmid}_v1", identifier.lower())
        if cluster:
            result.add(("cluster", cluster[1]))
            continue
        node = re.fullmatch(rf"proxmox_{escaped_kind}_(.+)_{escaped_vmid}_v1", identifier.lower())
        if node:
            result.add(("node", node[1]))
    return result


def resolve_legacy_guest_identity(kind, vmid, node, entity_rows=(), devices=()):
    entity_identities = {
        identity for row in entity_rows
        if (identity := _legacy_entity_identity(getattr(row, "unique_id", None), kind, vmid)) is not None
    }
    device_identities = set()
    for device in devices:
        device_identities.update(_legacy_device_identity(getattr(device, "identifiers", ()), kind, vmid))
    # Entities carry the identity Home Assistant is actually using. Devices can
    # outlive their entities (e.g. node-scoped devices left behind by the 5.0
    # cluster re-scope), so they only decide the identity when no entity does.
    identities = entity_identities or device_identities
    if len(identities) != 1:
        return LegacyGuestIdentity(None, None, bool(identities))
    mode, value = identities.pop()
    return LegacyGuestIdentity(value if mode == "cluster" else None,
                               value if mode == "node" else None)


def normalize_scope(scope) -> str:
    """Normalize scope fragments for stable identifiers."""
    return re.sub(r"\s+", "_", str(scope).strip().lower())


def sensor_unique_id(scope, kind, vmid, metric="status") -> str:
    scope = normalize_scope(scope)
    return f"pve_cluster_{scope}_proxmox_{kind}_{scope}_{vmid}_{metric}_v1"


def guest_device_identifier(scope, kind, vmid) -> str:
    return f"proxmox_{kind}_cluster_{normalize_scope(scope)}_{vmid}_v1"


def guest_button_unique_id(scope, kind, vmid, command) -> str:
    return f"proxmox_{kind}_cluster_{normalize_scope(scope)}_{vmid}_{command}"


def replication_summary_unique_id(scope, kind) -> str:
    return f"pve_cluster_{normalize_scope(scope)}_replication_{kind}"


def replication_job_unique_id(scope, job_id, kind) -> str:
    return f"pve_cluster_{normalize_scope(scope)}_replication_{job_id}_{kind}"
