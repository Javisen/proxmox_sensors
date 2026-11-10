"""Pure PVE resource binding to logical blocks, using references only."""

import re

from .layout import get_dashboard_layout

_HEALTH = {
    "proxmox_node": "health", "node_status": "status", "node_cpu": "cpu",
    "node_memory_usage": "memory", "node_swap_usage": "swap",
    "node_rootfs_usage": "rootfs",
    "node_load_1m": "load", "node_iowait": "iowait",
    "node_ksm_shared": "ksm", "node_score": "score",
}
_GUEST = ("status", "cpu_usage", "memory_usage", "memory_used", "memory_total",
          "disk_usage", "disk_used", "disk_total", "uptime")
_STORAGE = {"storage_usage": "usage", "storage_total": "total",
            "storage_used": "used", "storage_free": "free", "storage_status": "status"}
_HEADER = ("status", "node_name", "pve_version", "kernel_version", "uptime_seconds",
           "vm_count", "ct_count", "storage_count")
_ORDER = ("health", "status", "cpu", "memory", "swap", "rootfs", "load", "iowait",
          "ksm", "score", "cpu_usage", "memory_usage", "memory_used", "memory_total",
          "disk_usage", "disk_used", "disk_total", "uptime", "usage", "total", "used", "free",
          "replication_jobs", "replication_status", "duration", "last_sync", "next_sync")
_DIAGNOSTICS = ("sidecar", "smart", "zfs", "disks", "mounted_disks", "hardware", "system")


def _metric_order(reference):
    metric = reference["metric"]
    if "job_id" in reference:
        guest, _, job = reference["job_id"].partition("-")
        return (100, int(guest), (0, int(job)) if job.isdigit() else (1, job),
                _ORDER.index(metric), reference["entity_id"])
    return (_ORDER.index(metric) if metric in _ORDER else len(_ORDER),
            reference.get("job_id", ""), reference["entity_id"], reference.get("attribute", ""))


def build_pve_dashboard_model(inventory, layout=None):
    """Bind admitted PVE display resources; never infer ownership or query HA.

    Replication remains with its normalized guest even when entity-owned by
    CLUSTER. Whole CLUSTER/PBS resources are not mapped. Empty groups are omitted.
    """
    layout = get_dashboard_layout("pve") if layout is None else layout
    if layout["type"] != "pve":
        raise ValueError("PVE resource mapping requires a PVE layout")
    groups = []
    for entry in sorted(inventory["entries"], key=lambda item: item["entry_id"]):
        if entry["platform_type"] != "PVE":
            continue
        blocks = {block["id"]: {} for block in layout["blocks"]}
        resources = [r for r in inventory["resources"] if r["entry_id"] == entry["entry_id"]]

        def add(block, resource, entity, metric, attribute=None, job_id=None):
            item = blocks[block].setdefault(resource["resource_id"], {
                "resource_id": resource["resource_id"], "kind": resource["kind"],
                "title": resource["title"], "references": [],
            })
            if resource.get("guest_id") is not None:
                item["guest_id"] = resource["guest_id"]
            ref = {"entity_id": entity["entity_id"], "metric": metric}
            if block == "temperatures" or (block == "diagnostics" and metric == "hardware"):
                # Preserve per-sensor display metadata, not technical device titles.
                for field in ("translation_key", "name", "original_name", "device_class", "unit"):
                    if isinstance(entity.get(field), str) and entity[field]:
                        ref[field] = entity[field]
            if attribute is not None:
                ref["attribute"] = attribute
            if job_id is not None:
                ref["job_id"] = job_id
            if ref not in item["references"]:
                item["references"].append(ref)

        for resource in resources:
            kind = resource["kind"]
            for entity in resource["entities"]:
                if entity["domain"] == "button" and kind in ("vm", "ct"):
                    for command in ("start", "shutdown", "stop", "reboot"):
                        if entity.get("translation_key") == f"{kind}_{command}":
                            add("guests", resource, entity, command)
                    continue
                if entity["domain"] not in ("sensor", "binary_sensor"):
                    continue
                key = entity.get("translation_key")
                if key in ("node_updates", "node_network_rx", "node_network_tx") and kind == "node":
                    add("node_info", resource, entity, key)
                if key == "proxmox_storages" and kind == "node":
                    add("node_info", resource, entity, "storage_count")
                if key == "node_ksm_status" and kind == "node":
                    add("node_info", resource, entity, "ksm_status")
                    add("node_health", resource, entity, "ksm_status")
                if key == "node_kernel_version":
                    add("header", resource, entity, "kernel_version")
                uid = entity.get("unique_id") or ""
                family = entity["family"]
                attributes = entity.get("attributes", [])
                # Exact integration-owned sidecar identity, not a name search.
                node = re.escape((entry.get("node") or "").lower())
                sidecar = re.fullmatch(r"pve_.+_proxmox_node_" + node + "_sidecar_status", uid)
                if family == "replication":
                    cluster = re.escape(resource.get("cluster_id") or "")
                    job = re.fullmatch(r"pve_cluster_" + cluster + r"_replication_([0-9]+-.+)_(duration|last_sync|next_sync)", uid)
                    if job:
                        add("replication", resource, entity, job[2], job_id=job[1])
                    continue
                if kind in ("vm", "ct"):
                    for attr in ("replication_jobs", "replication_status"):
                        if attr in attributes:
                            add("replication", resource, entity, attr, attribute=attr)
                    if key in {f"{kind}_{metric}" for metric in _GUEST}:
                        add("guests", resource, entity, key[len(kind) + 1:])
                    continue
                if kind in ("storage", "storages"):
                    if key in _STORAGE:
                        add("storage", resource, entity, _STORAGE[key])
                    continue
                if entity.get("device_class") == "temperature":
                    add("temperatures", resource, entity, "temperature")
                    continue
                if key == "proxmox_node":
                    add("header", resource, entity, "health")
                    for attr in _HEADER:
                        if attr in attributes:
                            add("header", resource, entity, attr, attribute=attr)
                if key in _HEALTH and kind == "node":
                    add("node_health", resource, entity, _HEALTH[key])
                elif key in ("node_pve_version", "node_uptime") and kind == "node":
                    # Dedicated sensors are only a fallback for absent header attrs.
                    attr = "pve_version" if key == "node_pve_version" else "uptime_seconds"
                    has_attribute = any(e.get("translation_key") == "proxmox_node" and attr in e.get("attributes", [])
                                        for r in resources for e in r["entities"])
                    if not has_attribute:
                        add("header", resource, entity, attr)
                elif key in ("node_last_task", "node_failed_tasks") and kind == "node":
                    add("tasks", resource, entity, key)
                elif sidecar and family == "sidecar":
                    add("diagnostics", resource, entity, "sidecar")
                elif kind == "disks":
                    if (key == "disk_size" or uid.endswith("_capacity")
                            or ("_proxmox_disk_" in uid and uid.endswith("_v1"))):
                        add("diagnostics", resource, entity, "disks")
                elif kind in ("smart", "zfs"):
                    add("diagnostics", resource, entity, kind)
                elif key == "node_mounted_disks":
                    add("diagnostics", resource, entity, "mounted_disks")
                elif kind == "hardware":
                    add("diagnostics", resource, entity, "hardware")
                elif key in ("node_cpu_info", "node_kernel_version"):
                    add("diagnostics", resource, entity, "system")

        result = {}
        for block, items in blocks.items():
            def order(item):
                guest = str(item.get("guest_id", ""))
                if block == "node_health":
                    return (min(_metric_order(ref) for ref in item["references"]), item["resource_id"])
                if block in ("guests", "replication"):
                    return (int(guest) if guest.isdigit() else float("inf"), item["resource_id"])
                if block == "diagnostics":
                    rank = min(_DIAGNOSTICS.index(ref["metric"]) for ref in item["references"])
                    return (rank, item["title"].casefold(), item["resource_id"])
                return (item["title"].casefold(), item["resource_id"])
            result[block] = sorted(items.values(), key=order)
            for item in result[block]:
                item["references"].sort(key=_metric_order)
        if any(result.values()):
            groups.append({"entry_id": entry["entry_id"], "node": entry.get("node"), "blocks": result})
    return {"schema_version": 1, "type": "pve", "groups": groups}
