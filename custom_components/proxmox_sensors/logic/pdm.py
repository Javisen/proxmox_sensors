"""Identity and aggregation helpers for Proxmox Datacenter Manager."""

from __future__ import annotations

from hashlib import sha256
from math import isfinite
import re
from uuid import UUID, uuid4


PDM_IDENTITY_VERSION = 1


class PDMIdentityError(ValueError):
    pass


def normalize_pdm_identity_id(value) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = UUID(value)
    except (TypeError, ValueError, AttributeError):
        return None
    canonical = str(parsed)
    return canonical if parsed.version == 4 and value == canonical else None


def new_pdm_identity_id(entries=()) -> str:
    reserved = {
        value
        for entry in entries
        if (value := (getattr(entry, "data", {}) or {}).get("pdm_identity_id"))
    }
    while True:
        candidate = str(uuid4())
        if candidate not in reserved:
            return candidate


def pdm_identity_scope(entry, entries=()) -> str:
    data = getattr(entry, "data", {}) or {}
    if data.get("pdm_identity_version") != PDM_IDENTITY_VERSION:
        raise PDMIdentityError("Invalid PDM identity version")
    identity_id = normalize_pdm_identity_id(data.get("pdm_identity_id"))
    if identity_id is None:
        raise PDMIdentityError("Invalid PDM identity UUID")
    entry_id = getattr(entry, "entry_id", None)
    if any(
        getattr(candidate, "entry_id", None) != entry_id
        and (getattr(candidate, "data", {}) or {}).get("platform_type") == "PDM"
        and (getattr(candidate, "data", {}) or {}).get("pdm_identity_id") == identity_id
        for candidate in entries
    ):
        raise PDMIdentityError("Duplicate PDM identity UUID")
    return identity_id


def pdm_root_identifier(scope: str) -> str:
    return f"pdm_server_{scope}"


def pdm_remote_key(remote_id: str) -> str:
    if not isinstance(remote_id, str) or not remote_id:
        raise ValueError("PDM remote ID must be a non-empty string")
    return sha256(remote_id.encode("utf-8")).hexdigest()


def pdm_remote_identifier(scope: str, remote_id: str) -> str:
    return f"pdm_remote_{scope}_{pdm_remote_key(remote_id)}"


def pdm_unique_id(scope: str, metric: str, remote_id: str | None = None) -> str:
    if remote_id is None:
        return f"pdm_{scope}_{metric}"
    return f"pdm_{scope}_remote_{pdm_remote_key(remote_id)}_{metric}"


def is_owned_orphan_pdm_remote_device(
    device,
    entry_id: str,
    scope: str,
    root_device_id: str,
    expected_identifiers: set[tuple[str, str]],
) -> bool:
    """Validate PDM ownership and identity before registry cleanup."""
    identifiers = set(getattr(device, "identifiers", ()) or ())
    if len(identifiers) != 1 or identifiers.intersection(expected_identifiers):
        return False
    domain, identifier = next(iter(identifiers))
    if domain != "proxmox_sensors" or re.fullmatch(
        rf"pdm_remote_{re.escape(scope)}_[0-9a-f]{{64}}", identifier
    ) is None:
        return False
    return (
        set(getattr(device, "config_entries", ()) or ()) == {entry_id}
        and not getattr(device, "connections", ())
        and getattr(device, "via_device_id", None) == root_device_id
    )


def validate_pdm_resource_groups(value) -> list[dict]:
    if not isinstance(value, list):
        raise ValueError("Invalid PDM resources/list response: expected a list")
    seen = set()
    result = []
    for group in value:
        if not isinstance(group, dict):
            raise ValueError("Invalid PDM resources/list group")
        remote = group.get("remote")
        resources = group.get("resources")
        if not isinstance(remote, str) or not remote or not isinstance(resources, list):
            raise ValueError("Invalid PDM resources/list group fields")
        if remote in seen or any(not isinstance(resource, dict) for resource in resources):
            raise ValueError("Ambiguous PDM resources/list response")
        seen.add(remote)
        result.append({"remote": remote, "resources": resources})
    return result


def validate_pdm_remote_inventory(value) -> list[dict]:
    if not isinstance(value, list):
        raise ValueError("Invalid PDM remotes/remote response: expected a list")
    seen = set()
    result = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("Invalid PDM remote inventory item")
        remote_id = item.get("id")
        remote_type = item.get("type")
        if (
            not isinstance(remote_id, str)
            or not remote_id
            or remote_id in seen
            or remote_type not in ("pve", "pbs")
        ):
            raise ValueError("Ambiguous PDM remote inventory response")
        seen.add(remote_id)
        result.append({"id": remote_id, "type": remote_type})
    return result


def validate_pdm_status(value) -> dict:
    if not isinstance(value, dict) or not isinstance(value.get("remote-list"), list):
        raise ValueError("Invalid PDM resources/status response")
    seen = set()
    for remote in value["remote-list"]:
        if not isinstance(remote, dict):
            raise ValueError("Invalid PDM remote status")
        remote_id = remote.get("name")
        remote_type = remote.get("ty")
        remote_status = remote.get("status")
        if (
            not isinstance(remote_id, str)
            or not remote_id
            or remote_id in seen
            or remote_type not in ("pve", "pbs")
            or not isinstance(remote_status, str)
            or not remote_status
        ):
            raise ValueError("Ambiguous PDM remote status")
        seen.add(remote_id)
    return value


def validate_pdm_subscriptions(value) -> list[dict]:
    if not isinstance(value, list):
        raise ValueError("Invalid PDM resources/subscription response")
    seen = set()
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("remote"), str):
            raise ValueError("Invalid PDM subscription item")
        if not item["remote"] or item["remote"] in seen:
            raise ValueError("Ambiguous PDM subscription response")
        seen.add(item["remote"])
    return value


def validate_pdm_updates_envelope(value) -> dict:
    if not isinstance(value, dict) or not isinstance(value.get("remotes"), dict):
        raise ValueError("Invalid PDM remotes/updates/summary response")
    for remote_id, remote in value["remotes"].items():
        if not isinstance(remote_id, str) or not remote_id or not isinstance(remote, dict):
            raise ValueError("Invalid PDM updates Remote entry")
    return value


def build_pdm_updates_snapshot(value, inventory: list[dict]) -> dict:
    value = validate_pdm_updates_envelope(value)
    inventory = validate_pdm_remote_inventory(inventory)
    expected = {item["id"]: item["type"] for item in inventory}
    remotes = value["remotes"]
    if set(remotes) != set(expected):
        raise ValueError("Incomplete PDM updates Remote inventory")

    normalized = {}
    timestamps = []
    total_updates = 0
    for remote_id, remote_type in expected.items():
        remote = remotes[remote_id]
        if remote.get("remote-type") != remote_type or remote.get("status") != "success":
            raise ValueError("Incomplete PDM updates Remote status")
        nodes = remote.get("nodes")
        if not isinstance(nodes, dict) or not nodes:
            raise ValueError("Incomplete PDM updates node inventory")
        normalized_nodes = {}
        for node_id, node in nodes.items():
            if not isinstance(node_id, str) or not node_id or not isinstance(node, dict):
                raise ValueError("Invalid PDM updates node entry")
            count = node.get("number-of-updates")
            last_refresh = node.get("last-refresh")
            query_status = node.get("status")
            repository_status = node.get("repository-status")
            versions = node.get("versions")
            if (
                isinstance(count, bool)
                or not isinstance(count, int)
                or count < 0
                or isinstance(last_refresh, bool)
                or not isinstance(last_refresh, int)
                or last_refresh <= 0
                or query_status != "success"
                or not isinstance(repository_status, str)
                or not repository_status
                or not isinstance(versions, list)
            ):
                raise ValueError("Incomplete PDM updates node status")
            normalized_versions = []
            for version in versions:
                if (
                    not isinstance(version, dict)
                    or not isinstance(version.get("package"), str)
                    or not version["package"]
                    or not isinstance(version.get("version"), str)
                    or not version["version"]
                ):
                    raise ValueError("Invalid PDM updates version entry")
                normalized_versions.append(
                    {"package": version["package"], "version": version["version"]}
                )
            normalized_nodes[node_id] = {
                "status": query_status,
                "repository_status": repository_status,
                "number_of_updates": count,
                "last_refresh": last_refresh,
                "versions": normalized_versions,
            }
            total_updates += count
            timestamps.append(last_refresh)
        normalized[remote_id] = {
            "remote_type": remote_type,
            "status": remote["status"],
            "nodes": normalized_nodes,
        }

    return {
        "total_updates": total_updates,
        "oldest_last_refresh": min(timestamps) if timestamps else None,
        "newest_last_refresh": max(timestamps) if timestamps else None,
        "remotes": normalized,
    }


def merge_pdm_updates(last_good, response, inventory, inventory_fresh):
    endpoint_fresh = not isinstance(response, Exception)
    if endpoint_fresh:
        try:
            validate_pdm_updates_envelope(response)
        except ValueError:
            endpoint_fresh = False

    snapshot_complete = False
    if endpoint_fresh and inventory_fresh:
        try:
            snapshot = build_pdm_updates_snapshot(response, inventory)
        except ValueError:
            pass
        else:
            last_good["updates"] = snapshot
            snapshot_complete = True
    return last_good.get("updates"), endpoint_fresh, snapshot_complete


def merge_pdm_sections(last_good: dict, keys, responses) -> tuple[dict, dict]:
    """Merge a poll without treating an API failure as valid absence."""
    sections = {}
    sections_ok = {}
    for key, response in zip(keys, responses):
        sections_ok[key] = not isinstance(response, Exception)
        if sections_ok[key]:
            last_good[key] = response
        sections[key] = last_good.get(key)
    return sections, sections_ok


def _number(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if isfinite(value) and value >= 0 else None


def _percentage(used, total) -> float | None:
    used = _number(used)
    total = _number(total)
    if used is None or total in (None, 0):
        return None
    return round(used / total * 100, 2)


def _remote_summary(resources: list[dict]) -> tuple[dict, dict]:
    types = {
        "pve-node": "nodes",
        "pbs-node": "nodes",
        "pve-qemu": "qemu",
        "pve-lxc": "lxc",
        "pve-storage": "storages",
        "pbs-datastore": "datastores",
        "pve-network": "networks",
        "pve-sdn-zone": "sdn_zones",
    }
    inventory = {
        "total_resources": len(resources),
        "nodes": 0,
        "qemu": 0,
        "lxc": 0,
        "storages": 0,
        "datastores": 0,
        "networks": 0,
        "sdn_zones": 0,
    }
    memory_used = memory_total = storage_used = storage_total = 0.0
    cpu_used = cpu_total = 0.0
    memory_seen = storage_seen = cpu_seen = False
    for resource in resources:
        resource_type = resource.get("type")
        if resource_type in types:
            inventory[types[resource_type]] += 1
        if resource_type in ("pve-node", "pbs-node"):
            used = _number(resource.get("mem"))
            total = _number(resource.get("maxmem"))
            if used is not None and total is not None:
                memory_used += used
                memory_total += total
                memory_seen = True
            cpu = _number(resource.get("cpu"))
            maxcpu = _number(resource.get("maxcpu"))
            if cpu is not None and maxcpu is not None:
                cpu_used += cpu * maxcpu
                cpu_total += maxcpu
                cpu_seen = True
        if resource_type in ("pve-storage", "pbs-datastore"):
            used = _number(resource.get("disk"))
            total = _number(resource.get("maxdisk"))
            if used is not None and total is not None:
                storage_used += used
                storage_total += total
                storage_seen = True
    capacity = {
        "cpu_usage_percent": _percentage(cpu_used, cpu_total) if cpu_seen else None,
        "cpu_cores": cpu_total if cpu_seen else None,
        "memory_used": int(memory_used) if memory_seen else None,
        "memory_total": int(memory_total) if memory_seen else None,
        "memory_usage_percent": _percentage(memory_used, memory_total) if memory_seen else None,
        "storage_used": int(storage_used) if storage_seen else None,
        "storage_total": int(storage_total) if storage_seen else None,
        "storage_usage_percent": _percentage(storage_used, storage_total) if storage_seen else None,
    }
    return inventory, capacity


def build_pdm_remotes(
    inventory: list[dict],
    status: dict,
    resource_groups: list[dict],
    subscriptions: list[dict],
) -> dict:
    inventory = validate_pdm_remote_inventory(inventory)
    status = validate_pdm_status(status)
    resource_groups = validate_pdm_resource_groups(resource_groups)
    subscriptions = validate_pdm_subscriptions(subscriptions)
    status_by_remote = {item["name"]: item for item in status["remote-list"]}
    resources_by_remote = {item["remote"]: item["resources"] for item in resource_groups}
    subscriptions_by_remote = {item["remote"]: item.get("state") for item in subscriptions}
    result = {}
    for item in inventory:
        remote_id = item["id"]
        remote_status = status_by_remote.get(remote_id, {})
        resources = resources_by_remote.get(remote_id, [])
        remote_inventory, capacity = _remote_summary(resources)
        result[remote_id] = {
            "remote_id": remote_id,
            "type": item["type"],
            "status": remote_status.get("status"),
            "subscription": subscriptions_by_remote.get(remote_id),
            "inventory": remote_inventory,
            "capacity": capacity,
        }
    return result
