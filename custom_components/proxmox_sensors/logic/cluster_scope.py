"""Pure helpers for explicit, locally-persisted PVE cluster scopes.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import logging
import re
from uuid import UUID, uuid4
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


CLUSTER_SCOPE_ID = "cluster_scope_id"
CLUSTER_SCOPE_STATE = "cluster_scope_state"
LEGACY_SCOPE = "legacy"
VALID_SCOPE = "valid"
INVALID_SCOPE = "invalid"
PENDING_SCOPE = "pending"
ACTIVE_SCOPE = "active"
ASSOCIATION_ALLOWED = "allowed"
ASSOCIATION_SOURCE_NOT_PVE = "source_not_pve"
ASSOCIATION_SOURCE_SCOPE_NOT_ACTIVE = "source_scope_not_active"
ASSOCIATION_TARGET_NOT_CLUSTER = "target_not_cluster"
ASSOCIATION_TARGET_SCOPE_INVALID = "target_scope_invalid"
ASSOCIATION_TARGET_SCOPE_CONFLICT = "target_scope_conflict"
ASSOCIATION_SCOPE_ALREADY_ASSOCIATED = "scope_already_associated"


@dataclass(frozen=True)
class GuestIdentityContext:
    scope: object
    use_scoped_identity: bool


@dataclass(frozen=True)
class ClusterAssociationPreflight:
    allowed: bool
    reason: str


def new_cluster_scope_id() -> str:
    """Return a canonical UUID4 generated from the local secure RNG."""
    return str(uuid4())


def normalize_cluster_scope_id(value) -> str | None:
    """Return a canonical UUID scope, or ``None`` for absent/invalid input."""
    if not isinstance(value, str):
        return None
    try:
        parsed = UUID(value)
    except (TypeError, ValueError, AttributeError):
        return None
    return str(parsed) if parsed.version == 4 else None


def _entry_data(entry) -> dict:
    """Read mapping-like entry data without mutating the supplied object."""
    if isinstance(entry, dict):
        return entry.get("data", entry)
    return getattr(entry, "data", {}) or {}


def cluster_scope_status(entry) -> str:
    """Classify an entry as legacy, valid, or carrying invalid scope data."""
    data = _entry_data(entry)
    if CLUSTER_SCOPE_ID not in data or data.get(CLUSTER_SCOPE_ID) is None:
        return LEGACY_SCOPE
    if not normalize_cluster_scope_id(data.get(CLUSTER_SCOPE_ID)):
        return INVALID_SCOPE
    state = data.get(CLUSTER_SCOPE_STATE)
    return state if state in (PENDING_SCOPE, ACTIVE_SCOPE) else VALID_SCOPE


def cluster_entry_scope_status(entry) -> str:
    value = _entry_data(entry).get(CLUSTER_SCOPE_ID)
    if value in (None, ""):
        return LEGACY_SCOPE
    if normalize_cluster_scope_id(value) is None:
        return INVALID_SCOPE
    state = _entry_data(entry).get(CLUSTER_SCOPE_STATE)
    return state if state in (PENDING_SCOPE, ACTIVE_SCOPE) else VALID_SCOPE


def _entry_platform(entry) -> str | None:
    value = _entry_data(entry).get("platform_type")
    return value.upper() if isinstance(value, str) else None


def _same_entry(first, second) -> bool:
    if first is second:
        return True
    first_id = getattr(first, "entry_id", None)
    second_id = getattr(second, "entry_id", None)
    return bool(first_id) and first_id == second_id


def cluster_association_preflight(pve_entry, cluster_entry, cluster_entries: Iterable) -> ClusterAssociationPreflight:
    if _entry_platform(pve_entry) != "PVE":
        return ClusterAssociationPreflight(False, ASSOCIATION_SOURCE_NOT_PVE)
    scope = entry_cluster_scope_id(pve_entry)
    if scope is None or cluster_scope_status(pve_entry) not in (PENDING_SCOPE, ACTIVE_SCOPE):
        return ClusterAssociationPreflight(False, ASSOCIATION_SOURCE_SCOPE_NOT_ACTIVE)
    if _entry_platform(cluster_entry) != "CLUSTER":
        return ClusterAssociationPreflight(False, ASSOCIATION_TARGET_NOT_CLUSTER)
    target_status = cluster_entry_scope_status(cluster_entry)
    if target_status == INVALID_SCOPE:
        return ClusterAssociationPreflight(False, ASSOCIATION_TARGET_SCOPE_INVALID)
    target_scope = entry_cluster_scope_id(cluster_entry)
    if target_scope is not None and target_scope != scope:
        return ClusterAssociationPreflight(False, ASSOCIATION_TARGET_SCOPE_CONFLICT)
    for candidate in cluster_entries:
        if _same_entry(candidate, cluster_entry) or _entry_platform(candidate) != "CLUSTER":
            continue
        if entry_cluster_scope_id(candidate) == scope:
            return ClusterAssociationPreflight(False, ASSOCIATION_SCOPE_ALREADY_ASSOCIATED)
    return ClusterAssociationPreflight(True, ASSOCIATION_ALLOWED)


def _active_pve_scope(entry) -> str | None:
    if _entry_platform(entry) != "PVE" or cluster_scope_status(entry) != ACTIVE_SCOPE:
        return None
    return entry_cluster_scope_id(entry)


def _valid_cluster_scope(entry) -> str | None:
    if _entry_platform(entry) != "CLUSTER" or cluster_entry_scope_status(entry) != ACTIVE_SCOPE:
        return None
    return entry_cluster_scope_id(entry)


def associated_cluster_for_pve(pve_entry, entries: Iterable):
    scope = _active_pve_scope(pve_entry)
    if scope is None:
        return None
    matches = [entry for entry in entries if _valid_cluster_scope(entry) == scope]
    return matches[0] if len(matches) == 1 else None


def associated_pves_for_cluster(cluster_entry, entries: Iterable) -> list:
    scope = _valid_cluster_scope(cluster_entry)
    if scope is None:
        return []
    entries = list(entries)
    clusters = [entry for entry in entries if _valid_cluster_scope(entry) == scope]
    if len(clusters) != 1 or not _same_entry(clusters[0], cluster_entry):
        return []
    return [entry for entry in entries if _active_pve_scope(entry) == scope]


def scoped_migration_target(source, entries: Iterable, node):
    entries = list(entries)
    scope = _active_pve_scope(source)
    source_cluster = associated_cluster_for_pve(source, entries)
    active_clusters = [entry for entry in entries if _valid_cluster_scope(entry) == scope]
    if scope is None:
        _LOGGER.debug(
            "Scoped migration target rejected: reason=source_scope_not_active "
            "source_entry_id=%s source_platform=%s source_raw_scope=%s "
            "source_status=%s requested_node=%s",
            getattr(source, "entry_id", None),
            _entry_platform(source),
            _entry_data(source).get(CLUSTER_SCOPE_ID),
            cluster_scope_status(source),
            node,
        )
        return None
    if source_cluster is None:
        _LOGGER.debug(
            "Scoped migration target rejected: reason=source_cluster_not_unique "
            "source_entry_id=%s source_scope=%s active_clusters=%s requested_node=%s",
            getattr(source, "entry_id", None),
            scope,
            [
                {
                    "entry_id": getattr(entry, "entry_id", None),
                    "scope": entry_cluster_scope_id(entry),
                    "status": cluster_entry_scope_status(entry),
                }
                for entry in active_clusters
            ],
            node,
        )
        return None
    candidates = []
    pve_entries = []
    for entry in entries:
        if entry is source:
            continue
        entry_scope = _active_pve_scope(entry)
        entry_cluster = associated_cluster_for_pve(entry, entries)
        entry_node = str(_entry_data(entry).get("node", "")).lower()
        pve_entries.append(
            {
                "entry_id": getattr(entry, "entry_id", None),
                "platform": _entry_platform(entry),
                "scope": entry_scope,
                "raw_scope": _entry_data(entry).get(CLUSTER_SCOPE_ID),
                "status": cluster_scope_status(entry),
                "node": entry_node,
                "associated_cluster_entry_id": getattr(entry_cluster, "entry_id", None),
                "same_source_cluster": entry_cluster is source_cluster,
                "node_matches": entry_node == str(node).lower(),
            }
        )
        if (
            entry_scope == scope
            and entry_cluster is source_cluster
            and entry_node == str(node).lower()
        ):
            candidates.append(entry)
    if len(candidates) != 1:
        _LOGGER.debug(
            "Scoped migration target rejected: reason=target_not_unique "
            "source_entry_id=%s source_scope=%s source_cluster_entry_id=%s "
            "requested_node=%s active_clusters=%s pve_entries=%s candidates=%s",
            getattr(source, "entry_id", None),
            scope,
            getattr(source_cluster, "entry_id", None),
            node,
            [getattr(entry, "entry_id", None) for entry in active_clusters],
            pve_entries,
            [getattr(entry, "entry_id", None) for entry in candidates],
        )
        return None
    _LOGGER.debug(
        "Scoped migration target accepted: source_entry_id=%s source_scope=%s "
        "source_cluster_entry_id=%s target_entry_id=%s requested_node=%s",
        getattr(source, "entry_id", None),
        scope,
        getattr(source_cluster, "entry_id", None),
        getattr(candidates[0], "entry_id", None),
        node,
    )
    return candidates[0]


def pending_associated_cluster_for_pve(pve_entry, entries: Iterable):
    if _entry_platform(pve_entry) != "PVE" or cluster_scope_status(pve_entry) != PENDING_SCOPE:
        return None
    scope = entry_cluster_scope_id(pve_entry)
    if scope is None:
        return None
    matches = [entry for entry in entries if _entry_platform(entry) == "CLUSTER"
               and cluster_entry_scope_status(entry) == PENDING_SCOPE
               and entry_cluster_scope_id(entry) == scope]
    return matches[0] if len(matches) == 1 else None


def cluster_scope_membership(entry):
    """Return ``(state, uuid)`` only for explicitly valid lifecycle states."""
    scope = entry_cluster_scope_id(entry)
    state = cluster_scope_status(entry)
    return (state, scope) if scope is not None and state in (PENDING_SCOPE, ACTIVE_SCOPE) else None


def guest_identity_context(entry, legacy_scope) -> GuestIdentityContext:
    membership = cluster_scope_membership(entry)
    if membership is not None and membership[0] == ACTIVE_SCOPE:
        return GuestIdentityContext(membership[1], True)
    return GuestIdentityContext(legacy_scope, False)


def cluster_guest_identity_context(cluster_entry, entries: Iterable, legacy_scope) -> GuestIdentityContext:
    scope = _valid_cluster_scope(cluster_entry)
    if scope is None:
        return GuestIdentityContext(legacy_scope, False)
    matches = [entry for entry in entries if _valid_cluster_scope(entry) == scope]
    if len(matches) == 1 and _same_entry(matches[0], cluster_entry):
        return GuestIdentityContext(scope, True)
    return GuestIdentityContext(legacy_scope, False)


def entry_cluster_scope_id(entry) -> str | None:
    """Return an entry's valid explicit scope; legacy and invalid values do not group."""
    return normalize_cluster_scope_id(_entry_data(entry).get(CLUSTER_SCOPE_ID))


def recoverable_pve_scopes(entries: Iterable) -> dict[str, tuple[str, ...]]:
    entries = tuple(entries)
    groups: dict[str, list] = {}
    for entry in entries:
        if _entry_platform(entry) == "PVE":
            scope = entry_cluster_scope_id(entry)
            if scope is not None:
                groups.setdefault(scope, []).append(entry)
    result = {}
    for scope, members in groups.items():
        ids = [getattr(entry, "entry_id", None) for entry in members]
        if (not all(ids) or len(ids) != len(set(ids))
                or any(_entry_data(entry).get(CLUSTER_SCOPE_ID) != scope
                       or cluster_scope_status(entry) != ACTIVE_SCOPE for entry in members)
                or any(_entry_platform(entry) == "CLUSTER"
                       and entry_cluster_scope_id(entry) == scope for entry in entries)):
            continue
        result[scope] = tuple(sorted(ids))
    return result


def recovery_registry_conflict(scope, pve_entry_ids, entity_rows, devices) -> bool:
    escaped = re.escape(scope)
    guest_sensor = re.compile(rf"pve_cluster_{escaped}_proxmox_(?:vm|ct)_{escaped}_")
    guest_button = re.compile(rf"proxmox_(?:vm|ct)_cluster_{escaped}_")
    guest_device = re.compile(rf"proxmox_(?:vm|ct)_cluster_{escaped}_[0-9]+_v1$")
    replication = re.compile(rf"pve_cluster_{escaped}_replication_")
    members = set(pve_entry_ids)
    for row in entity_rows:
        if getattr(row, "platform", None) != "proxmox_sensors":
            continue
        uid = getattr(row, "unique_id", None) or ""
        if guest_sensor.match(uid) or guest_button.match(uid):
            if getattr(row, "config_entry_id", None) not in members:
                return True
        elif replication.match(uid) or uid == f"proxmox_cluster_firewall_{scope}":
            return True
    for device in devices:
        identifiers = getattr(device, "identifiers", ()) or ()

        proxmox_ids = [
            id_data[1] for id_data in identifiers
            if isinstance(id_data, tuple) and len(id_data) == 2 and id_data[0] == DOMAIN
        ]

        if not proxmox_ids:
            continue

        if not any(isinstance(i, str) and guest_device.fullmatch(i) for i in proxmox_ids):
            continue

        owners = getattr(device, "config_entries", None)
        if owners is None:
            owners = {getattr(device, "config_entry_id", None)}
        if not owners or not set(owners) <= members:
            return True

    return False


def cluster_scope_members(entries: Iterable, scope_id) -> list:
    """Return only entries whose valid explicit scope exactly matches ``scope_id``."""
    normalized = normalize_cluster_scope_id(scope_id)
    if normalized is None:
        return []
    return [entry for entry in entries if entry_cluster_scope_id(entry) == normalized]


def shares_cluster_scope(first, second) -> bool:
    """Whether two entries explicitly opt into the same valid scope."""
    first_scope = entry_cluster_scope_id(first)
    return first_scope is not None and first_scope == entry_cluster_scope_id(second)
