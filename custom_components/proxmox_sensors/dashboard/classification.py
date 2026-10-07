"""Pure classification of the integration's existing registry identities."""

import json
import re

from ..pbs_devices import pbs_device_datastore


def resource_id(*parts):
    """Collision-free, stable resource key, independent of entity/device IDs."""
    return json.dumps(parts, ensure_ascii=False, separators=(",", ":"))


def guest_identity(unique_id, identifiers, entry):
    """Return kind/scope/VMID; names and entity IDs are never identity inputs."""
    for identifier in sorted(identifiers):
        match = re.fullmatch(r"proxmox_(vm|ct)_cluster_(.+)_([0-9]+)_v1", identifier)
        if match:
            return match[1], match[2], match[3]
        node = re.escape((entry.get("node") or "").lower())
        match = re.fullmatch(r"proxmox_(vm|ct)_" + node + r"_([0-9]+)_v1", identifier)
        if match:
            return match[1], None, match[2]
    match = re.fullmatch(r"pve_cluster_(.+)_proxmox_(vm|ct)_(.+)_([0-9]+)_.+_v1", unique_id)
    if match and match[1] == match[3]:
        return match[2], match[1], match[4]
    match = re.fullmatch(r"proxmox_(vm|ct)_cluster_(.+)_([0-9]+)_[a-z]+", unique_id)
    if match:
        return match[1], match[2], match[3]
    node = re.escape((entry.get("node") or "").lower())
    match = re.fullmatch(r"pve_.+_proxmox_(vm|ct)_" + node + r"_([0-9]+)_.+_v1", unique_id)
    if match:
        return match[1], None, match[2]
    return None


def classify_entity(row, entry, identifiers):
    """Return family plus resource type/key/label and optional guest identity."""
    uid = row.unique_id or ""
    key = getattr(row, "translation_key", None) or ""
    if entry["platform_type"] == "PDM":
        scope = entry.get("pdm_identity_id")
        root = f"pdm_server_{scope}" if scope else None
        if root and (root in identifiers or uid.startswith(f"pdm_{scope}_")
                     and "_remote_" not in uid):
            return {"family": "pdm", "kind": "pdm", "label": "Datacenter",
                    "key": resource_id(entry["entry_id"], "pdm")}
        prefix = f"pdm_remote_{scope}_" if scope else None
        matches = sorted(identifier for identifier in identifiers
                         if prefix and identifier.startswith(prefix))
        if len(matches) == 1 and re.fullmatch(re.escape(prefix) + r"[0-9a-f]{64}", matches[0]):
            return {"family": "pdm_remote", "kind": "pdm_remote", "label": "PDM Remote",
                    "key": resource_id(entry["entry_id"], "pdm_remote", matches[0][len(prefix):])}
        return {"family": "pdm", "kind": "pdm_unknown", "label": "PDM",
                "key": resource_id(entry["entry_id"], "pdm_unknown", uid)}
    guest = guest_identity(uid, identifiers, entry)
    if guest is None and key.startswith(("vm_", "ct_")):
        match = re.fullmatch(r"proxmox_" + re.escape((entry.get("node") or "").lower())
                             + r"_([0-9]+)_[a-z]+", uid)
        if match:
            guest = key.split("_", 1)[0], None, match[1]
    if guest:
        kind, cluster, vmid = guest
        return {"family": "replication" if "_replication_" in uid else kind,
                "kind": kind, "key": resource_id("guest", "cluster" if cluster else "entry",
                                                  cluster or entry["entry_id"], kind, vmid),
                "label": f"{'VM' if kind == 'vm' else 'LXC'} {vmid}", "guest": guest}

    family = "pbs" if entry["platform_type"] == "PBS" else "cluster" if entry["platform_type"] == "CLUSTER" else "node"
    if "_replication_" in uid:
        family = "replication"
        cluster = entry.get("cluster_id")
        match = re.fullmatch(r"pve_cluster_" + re.escape(cluster or "")
                             + r"_replication_([0-9]+)-.+_(last_sync|next_sync|duration)", uid)
        if match and cluster:
            return {"family": family, "kind": family, "label": "Replication",
                    "key": resource_id(entry["entry_id"], family),
                    "guest_reference": (cluster, match[1])}
    elif "sidecar" in uid or "sidecar" in key:
        family = "sidecar"
    elif "backup" in key or "backup" in uid or "vzdump" in uid:
        family = "backups"
    elif key.startswith("zfs_") or "_proxmox_zfs_" in uid:
        family = "zfs"
    elif key == "disk_size" or "_proxmox_disk_" in uid:
        family = "disks"
    elif "smart" in key or "smart" in uid:
        family = "smart"
    elif key == "hw_nvme_temperature" or "_proxmox_nvme_" in uid:
        family = "smart"
    elif key.startswith("storage_"):
        family = "storages"
    elif key.startswith(("hardware_", "cpu_temperature", "dimm_")) or "_proxmox_hw_" in uid:
        family = "hardware"
    elif getattr(row, "entity_category", None) == "diagnostic":
        family = "diagnostic"

    # PBS datastore and maintenance devices share a resource, scoped by entry
    # AND persisted server ID. Equal datastore names on two servers never merge.
    if entry["platform_type"] == "PBS":
        stores = {store for identifier in identifiers
                  if (store := pbs_device_datastore(identifier, entry.get("server_id"))) is not None}
        if len(stores) == 1:
            store = next(iter(stores))
            return {"family": family, "kind": "datastore", "label": store,
                    "key": resource_id(entry["entry_id"], entry.get("server_id"), "datastore", store)}

    node = (entry.get("node") or "").lower()
    prefixes = [f"proxmox_storage_{node}_"]
    if entry.get("pve_identity_id"):
        prefixes.insert(0, f"proxmox_storage_{entry['pve_identity_id']}_{node}_")
    stores = {
        identifier[len(prefix):]
        for identifier in identifiers
        for prefix in prefixes
        if identifier.startswith(prefix) and identifier != prefix
    }
    if len(stores) == 1:
        store = next(iter(stores))
        return {"family": "storages", "kind": "storage", "label": store,
                "key": resource_id(entry["entry_id"], "storage", store)}

    # Some hardware resources share the node device. Extract only known prefixes;
    # unknown variants remain separate instead of accidentally merging resources.
    token = None
    for marker in (f"_proxmox_zfs_{node}_", f"_proxmox_disk_{node}_"):
        if marker in uid:
            token = uid.split(marker, 1)[1]
            if family == "disks":
                token = token.removesuffix("_v1")
    if family in ("zfs", "disks", "smart", "hardware"):
        token = token or uid
        return {"family": family, "kind": family, "label": token,
                "key": resource_id(entry["entry_id"], family, token)}
    return {"family": family, "kind": family, "label": family.replace("_", " ").title(),
            "key": resource_id(entry["entry_id"], family)}
