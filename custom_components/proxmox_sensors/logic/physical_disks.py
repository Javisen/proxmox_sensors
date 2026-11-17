"""Conservative, entry-scoped identity for physical PVE disks."""

from __future__ import annotations

from hashlib import sha256
import re


BINDINGS_KEY = "physical_disk_bindings_v2"
INVALID = {
    "", "unknown", "none", "null", "n/a", "na", "not available",
    "not specified", "to be filled by o.e.m.", "serialnumber", "123456789",
}


class DiskIdentityError(ValueError):
    """Inventory does not prove a one-to-one physical identity."""


def hardware_value(value):
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    candidate = cleaned.removeprefix("0x").removeprefix("0X")
    if (cleaned.casefold() in INVALID or not candidate
            or re.fullmatch(r"0+", candidate)
            or not any(c.isalnum() for c in candidate)):
        return None
    return cleaned


def sas_wwn(value):
    if not isinstance(value, str):
        return None
    candidate = value.strip().lower().removeprefix("0x")
    if re.fullmatch(r"[0-9a-f]{16}", candidate) and int(candidate, 16):
        return candidate
    return None


def smart_identity_matches(inventory_disk, smart_data, inventory_disks):
    if not isinstance(inventory_disk, dict) or not isinstance(smart_data, dict):
        return False
    expected = hardware_value(inventory_disk.get("serial"))
    observed = hardware_value(smart_data.get("serial"))
    if expected and observed and expected.casefold() == observed.casefold():
        expected_wwn = sas_wwn(expected)
        observed_wwn = sas_wwn(smart_data.get("wwn"))
        if smart_data.get("device_type") == "scsi" and expected_wwn and observed_wwn:
            return expected_wwn == observed_wwn
        return True
    if smart_data.get("device_type") != "scsi" or not isinstance(inventory_disks, dict):
        return False
    observed_wwn = sas_wwn(smart_data.get("wwn"))
    if not observed_wwn:
        return False
    expected_serial_wwn = sas_wwn(expected)
    expected_wwn = sas_wwn(inventory_disk.get("wwn"))
    if expected_serial_wwn != observed_wwn:
        return False
    if (hardware_value(inventory_disk.get("wwn"))
            and expected_wwn != observed_wwn):
        return False
    owners = [disk for disk in inventory_disks.values()
              if isinstance(disk, dict) and observed_wwn in (
                  sas_wwn(disk.get("serial")), sas_wwn(disk.get("wwn")),
              )]
    if len(owners) != 1 or owners[0] is not inventory_disk:
        return False
    if observed and any(
        disk is not inventory_disk and isinstance(disk, dict)
        and (hardware_value(disk.get("serial")) or "").casefold() == observed.casefold()
        for disk in inventory_disks.values()
    ):
        return False
    return True


def _key(value):
    return value.casefold() if value else None


def disk_identifier(scope, kind, value):
    digest = sha256(f"{kind}\0{value}".encode()).hexdigest()[:32]
    return f"proxmox_physical_disk_v2_{scope}_{digest}"


def capacity_unique_id(identifier):
    return f"{identifier}_capacity"


def plan_disks(scope, disks, bindings):
    """Return path to identifier and updated bindings; raise before any mutation."""
    if not isinstance(disks, dict) or not isinstance(bindings, dict):
        raise DiskIdentityError("Invalid disk inventory or bindings")
    proposed = {key: dict(value) for key, value in bindings.items()
                if isinstance(key, str) and isinstance(value, dict)}
    if len(proposed) != len(bindings):
        raise DiskIdentityError("Invalid persisted disk binding")
    wwn_counts = {}
    for disk in disks.values():
        if isinstance(disk, dict) and (wwn := hardware_value(disk.get("wwn"))):
            key = _key(wwn)
            wwn_counts[key] = wwn_counts.get(key, 0) + 1
    bound_wwn_counts = {}
    for old in proposed.values():
        if wwn := hardware_value(old.get("wwn")):
            key = _key(wwn)
            bound_wwn_counts[key] = bound_wwn_counts.get(key, 0) + 1
    seen = {"wwn": set(), "serial": set()}
    used = set()
    result = {}
    for path, disk in disks.items():
        if not isinstance(path, str) or not path.startswith("/dev/") or not isinstance(disk, dict):
            raise DiskIdentityError("Invalid disk path or record")
        values = {kind: hardware_value(disk.get(kind)) for kind in ("wwn", "serial")}
        if not any(values.values()):
            raise DiskIdentityError("Disk lacks a reliable WWN or serial")
        shared_wwn = values["wwn"] and wwn_counts[_key(values["wwn"])] > 1
        if shared_wwn and not values["serial"]:
            raise DiskIdentityError("Shared disk WWN lacks a unique serial")
        if shared_wwn and any(
            _key(old.get("wwn")) == _key(values["wwn"]) and not hardware_value(old.get("serial"))
            for old in proposed.values()
        ):
            raise DiskIdentityError("Shared disk WWN has an unproven persisted binding")
        for kind, value in values.items():
            if value:
                key = _key(value)
                if key in seen[kind] and not (kind == "wwn" and shared_wwn):
                    raise DiskIdentityError(f"Duplicate disk {kind}")
                seen[kind].add(key)
        reliable_wwn = values["wwn"] and not shared_wwn and (
            bound_wwn_counts.get(_key(values["wwn"]), 0) <= 1
        )
        if not reliable_wwn and not values["serial"]:
            raise DiskIdentityError("Disk lacks an unambiguous serial")
        matches = [identifier for identifier, old in proposed.items()
                   if (reliable_wwn and _key(old.get("wwn")) == _key(values["wwn"]))
                   or (values["serial"] and _key(old.get("serial")) == _key(values["serial"]))]
        if len(matches) > 1:
            raise DiskIdentityError("Conflicting persisted disk identities")
        if matches:
            identifier = matches[0]
            old = proposed[identifier]
            if any(value and old.get(kind) and _key(old[kind]) != _key(value)
                   for kind, value in values.items()):
                raise DiskIdentityError("Contradictory disk identity")
            old.update({kind: value for kind, value in values.items() if value})
        else:
            kind = "wwn" if reliable_wwn else "serial"
            identifier = disk_identifier(scope, kind, values[kind])
            if identifier in proposed:
                raise DiskIdentityError("Disk identity hash collision")
            proposed[identifier] = {kind: value for kind, value in values.items() if value}
        if identifier in used:
            raise DiskIdentityError("Two paths resolve to one disk")
        used.add(identifier)
        result[path] = identifier
    return result, proposed


def legacy_capacity_unique_id(context, server_id, node, path):
    namespace = server_id.lower() if context.is_legacy else context.identity_id
    return f"pve_{namespace}_proxmox_disk_{node}_{path}_v1".lower().replace(" ", "_")


def legacy_capacity_path(unique_id, context, server_id, node):
    """Recognize only the exact old capacity ID family for this PVE entry."""
    if not isinstance(unique_id, str):
        return None
    prefix = legacy_capacity_unique_id(context, server_id, node, "/dev/").removesuffix("_v1")
    if not unique_id.startswith(prefix) or not unique_id.endswith("_v1"):
        return None
    suffix = unique_id[len(prefix):-3]
    parts = suffix.split("/")
    if not parts or any(not re.fullmatch(r"[a-z0-9_.-]+", part) or part in {".", ".."}
                        for part in parts):
        return None
    path = f"/dev/{suffix}"
    return path if unique_id == legacy_capacity_unique_id(
        context, server_id, node, path
    ) else None


def prove_legacy_rows(rows, states, entry_id, context, server_id, node, disks, identities):
    """Map old rows to new IDs only with an exact historical serial match."""
    planned = []
    seen = set()
    for row in rows:
        if row.domain != "sensor" or row.platform != "proxmox_sensors" or row.config_entry_id != entry_id:
            continue
        uid = row.unique_id or ""
        if "proxmox_disk_" not in uid or not uid.endswith("_v1"):
            continue
        candidates = [path for path in disks
                      if uid == legacy_capacity_unique_id(context, server_id, node, path)]
        if len(candidates) != 1:
            raise DiskIdentityError("Legacy disk row has no unique inventory path")
        path = candidates[0]
        state = states.get(row.entity_id)
        historical = hardware_value((getattr(state, "attributes", None) or {}).get("Serial"))
        current = hardware_value(disks[path].get("serial"))
        if not historical or not current or _key(historical) != _key(current):
            raise DiskIdentityError("Legacy disk serial cannot be proved")
        target = capacity_unique_id(identities[path])
        if target in seen:
            raise DiskIdentityError("Duplicate legacy disk target")
        seen.add(target)
        planned.append((row, path, target))
    return planned
