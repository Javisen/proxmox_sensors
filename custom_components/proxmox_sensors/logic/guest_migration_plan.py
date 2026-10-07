from __future__ import annotations

from dataclasses import dataclass
import re

from .cluster_scope import (
    ACTIVE_SCOPE,
    PENDING_SCOPE,
    pending_associated_cluster_for_pve,
    cluster_scope_status,
    entry_cluster_scope_id,
)
from .guest_identity import (
    guest_button_unique_id,
    guest_device_identifier,
    replication_job_unique_id,
    replication_summary_unique_id,
    sensor_unique_id,
)


@dataclass(frozen=True)
class GuestMigrationUpdate:
    resource_type: str
    config_entry_id: str
    record_id: str
    old_identity: str
    new_identity: str

    @property
    def entity_id(self):
        return self.record_id

    @property
    def old_unique_id(self):
        return self.old_identity

    @property
    def new_unique_id(self):
        return self.new_identity


@dataclass(frozen=True)
class GuestMigrationExclusion:
    resource_type: str
    config_entry_id: str | None
    record_id: str
    identity: str | None
    reason: str
    blocking: bool = False


@dataclass(frozen=True)
class GuestMigrationPlan:
    updates: tuple[GuestMigrationUpdate, ...]
    exclusions: tuple[GuestMigrationExclusion, ...]
    noops: tuple[GuestMigrationUpdate, ...] = ()

    @property
    def entity_updates(self):
        return tuple(update for update in self.updates if update.resource_type.endswith("entity"))

    @property
    def device_updates(self):
        return tuple(update for update in self.updates if update.resource_type.endswith("device"))

    @property
    def skipped(self):
        return tuple(exclusion.record_id for exclusion in self.exclusions)

    @property
    def blocking_exclusions(self):
        return tuple(exclusion for exclusion in self.exclusions if exclusion.blocking)


_SENSOR = re.compile(
    r"pve_cluster_(?P<scope>.+)_proxmox_(?P<kind>vm|ct)_(?P=scope)_(?P<guest>[0-9]+)_(?P<metric>status|cpu_usage|memory_used|memory_total|disk_total|disk_used|disk_usage|uptime|network_rx|network_tx)_v1$"
)
_LEGACY_SENSOR = re.compile(
    r"proxmox_(?P<kind>vm|ct)_(?P<scope>.+)_(?P<guest>[0-9]+)_(?P<metric>status|cpu_usage|memory_used|memory_total|disk_total|disk_used|disk_usage|uptime|network_rx|network_tx)_v1$"
)
_VM_BUTTON = re.compile(
    r"proxmox_(?P<kind>vm)_cluster_(?P<scope>.+)_(?P<guest>[0-9]+)_(?P<command>start|shutdown|stop|reboot|reset|pause|hibernate|resume)$"
)
_CT_BUTTON = re.compile(
    r"proxmox_(?P<kind>ct)_cluster_(?P<scope>.+)_(?P<guest>[0-9]+)_(?P<command>start|shutdown|stop|reboot)$"
)
_DEVICE = re.compile(
    r"proxmox_(?P<kind>vm|ct)_cluster_(?P<scope>.+)_(?P<guest>[0-9]+)_v1$"
)
_SUMMARY = re.compile(r"pve_cluster_(?P<scope>.+)_replication_(?P<kind>jobs|status)$")
_REPLICATION = re.compile(
    r"pve_cluster_(?P<scope>.+)_replication_(?P<job_id>.+)_(?P<kind>last_sync|next_sync|duration)$"
)
_FIREWALL = re.compile(r"proxmox_cluster_firewall_(?P<scope>.+)$")


def _entry_id(entry):
    return getattr(entry, "entry_id", None)


def _same_entry(first, second):
    return first is second or (_entry_id(first) is not None and _entry_id(first) == _entry_id(second))


def _platform(entry):
    data = getattr(entry, "data", {}) or {}
    return data.get("platform_type", "").upper() if isinstance(data, dict) else ""


def _entity_owner(row):
    return getattr(row, "config_entry_id", None)


def _device_owner(device, entry_id):
    owners = getattr(device, "config_entries", None)
    singular = getattr(device, "config_entry_id", None)
    if owners is not None:
        try:
            owners = set(owners)
        except TypeError:
            return False
        if owners != {entry_id}:
            return False
        return singular in (None, entry_id)
    return singular == entry_id


def _identifiers(device):
    value = getattr(device, "identifiers", None)
    if not isinstance(value, (set, frozenset, tuple, list)):
        return None
    result = set()
    for identifier in value:
        if not isinstance(identifier, tuple) or len(identifier) != 2:
            return None
        result.add(identifier)
    return result


def _guest_identity(old, scope):
    sensor = _SENSOR.fullmatch(old) or _LEGACY_SENSOR.fullmatch(old)
    if sensor:
        values = sensor.groupdict()
        return "guest_entity", sensor_unique_id(scope, values["kind"], values["guest"], values["metric"])
    button = _VM_BUTTON.fullmatch(old) or _CT_BUTTON.fullmatch(old)
    if button:
        values = button.groupdict()
        return "guest_entity", guest_button_unique_id(scope, values["kind"], values["guest"], values["command"])
    device = _DEVICE.fullmatch(old)
    if device:
        values = device.groupdict()
        return "guest_device", guest_device_identifier(scope, values["kind"], values["guest"])
    return None


def _replication_identity(old, scope):
    summary = _SUMMARY.fullmatch(old)
    if summary:
        return replication_summary_unique_id(scope, summary.group("kind"))
    job = _REPLICATION.fullmatch(old)
    if job:
        return replication_job_unique_id(scope, job.group("job_id"), job.group("kind"))
    return None


def _cluster_identity(old, scope):
    if _FIREWALL.fullmatch(old):
        return f"proxmox_cluster_firewall_{scope}"
    return None


def _association_failure(source_entry, cluster_entry, entries):
    state = cluster_scope_status(source_entry)
    if _platform(source_entry) != "PVE":
        return "source_not_pve"
    if state != PENDING_SCOPE:
        return f"source_scope_{state}"
    scope = entry_cluster_scope_id(source_entry)
    if scope is None:
        return "source_scope_invalid"
    matches = [entry for entry in entries if _platform(entry) == "CLUSTER" and entry_cluster_scope_id(entry) == scope
               and cluster_scope_status(entry) == PENDING_SCOPE]
    if not matches:
        return "associated_cluster_missing"
    if len(matches) != 1:
        return "associated_cluster_ambiguous"
    if not _same_entry(matches[0], cluster_entry):
        return "associated_cluster_mismatch"
    if not _same_entry(pending_associated_cluster_for_pve(source_entry, entries), cluster_entry):
        return "associated_cluster_invalid"
    return None


def plan_guest_identity_migration(source_entry, cluster_entry, entries, rows, devices=()) -> GuestMigrationPlan:
    entries, rows, devices = tuple(entries), tuple(rows), tuple(devices)
    failure = _association_failure(source_entry, cluster_entry, entries)
    if failure:
        return GuestMigrationPlan((), (GuestMigrationExclusion(
            "association", _entry_id(source_entry), _entry_id(source_entry) or "", None, failure),))
    scope = entry_cluster_scope_id(cluster_entry)
    owners = ((_entry_id(source_entry), "guest_entity"), (_entry_id(cluster_entry), "replication_entity"))
    updates, exclusions, noops = [], [], []
    occupied_entities = {}
    for row in rows:
        unique_id = getattr(row, "unique_id", None)
        if isinstance(unique_id, str):
            occupied_entities.setdefault(unique_id, []).append(row)
    for row in rows:
        old = getattr(row, "unique_id", None)
        record_id = getattr(row, "entity_id", "")
        owner = _entity_owner(row)
        identity = _guest_identity(old, scope) if isinstance(old, str) else None
        resource_type = identity[0] if identity else None
        new = identity[1] if identity else _replication_identity(old, scope) if isinstance(old, str) else None
        if new is not None and resource_type is None:
            resource_type = "replication_entity"
        if new is None and isinstance(old, str):
            new = _cluster_identity(old, scope)
            if new is not None:
                resource_type = "cluster_entity"
        expected_owner = _entry_id(source_entry) if resource_type == "guest_entity" else _entry_id(cluster_entry)
        if new is None:
            if owner in {item[0] for item in owners}:
                exclusions.append(GuestMigrationExclusion("entity", owner, record_id, old, "irrelevant_identity"))
            continue
        if owner != expected_owner:
            exclusions.append(GuestMigrationExclusion(resource_type, owner, record_id, old, "foreign_config_entry", True))
            continue
        platform = getattr(row, "platform", None)
        if platform not in (None, "proxmox_sensors"):
            exclusions.append(GuestMigrationExclusion(resource_type, owner, record_id, old, "foreign_platform", True))
            continue
        update = GuestMigrationUpdate(resource_type, owner, record_id, old, new)
        targets = occupied_entities.get(new, [])
        if old == new or (targets and all(target is row for target in targets)):
            noops.append(update)
        elif targets:
            exclusions.append(GuestMigrationExclusion(resource_type, owner, record_id, old, "target_entity_occupied", True))
        else:
            updates.append(update)

    replication_device_ids = {
        getattr(row, "device_id", None)
        for row in rows
        if (_entity_owner(row) == _entry_id(cluster_entry)
            and isinstance(getattr(row, "unique_id", None), str)
            and _replication_identity(row.unique_id, scope) is not None
            and getattr(row, "device_id", None) is not None)
    }
    occupied_identifiers = {}
    for device in devices:
        identifiers = _identifiers(device)
        if identifiers is None:
            continue
        for identifier in identifiers:
            occupied_identifiers.setdefault(identifier, []).append(device)
    for device in devices:
        device_id = getattr(device, "id", "")
        identifiers = _identifiers(device)
        if identifiers is None:
            exclusions.append(GuestMigrationExclusion("device", None, device_id, None, "invalid_identifiers", True))
            continue
        candidates = []
        for domain, identifier in identifiers:
            if domain != "proxmox_sensors" or not isinstance(identifier, str):
                continue
            parsed = _guest_identity(identifier, scope)
            if parsed and parsed[0] == "guest_device":
                candidates.append((identifier, parsed[1]))
        if not candidates:
            continue
        if len(candidates) != 1:
            exclusions.append(GuestMigrationExclusion("device", None, device_id, None, "ambiguous_device_identity", True))
            continue
        old, new = candidates[0]
        if _device_owner(device, _entry_id(source_entry)):
            owner_id, resource_type = _entry_id(source_entry), "guest_device"
        elif device_id in replication_device_ids and _device_owner(device, _entry_id(cluster_entry)):
            owner_id, resource_type = _entry_id(cluster_entry), "replication_device"
        else:
            owner_id, resource_type = _entry_id(source_entry), "guest_device"
            exclusions.append(GuestMigrationExclusion(resource_type, owner_id, device_id, old, "foreign_config_entry", True))
            continue
        update = GuestMigrationUpdate(resource_type, owner_id, device_id, old, new)
        targets = occupied_identifiers.get(("proxmox_sensors", new), [])
        if old == new or (targets and all(target is device for target in targets)):
            noops.append(update)
        elif targets:
            exclusions.append(GuestMigrationExclusion(resource_type, owner_id, device_id, old, "target_device_identifier_occupied", True))
        else:
            updates.append(update)
    return GuestMigrationPlan(tuple(updates), tuple(exclusions), tuple(noops))
