"""PDM-only aggregate resource binding for the dashboard."""

from .layout import get_dashboard_layout


_ROOT_BLOCKS = {
    "pdm_status": "datacenter_status",
    "pdm_capacity": "capacity",
    "pdm_inventory": "inventory",
    "pdm_updates": "updates",
}
_ATTRIBUTES = {
    "pdm_status": ("remotes", "pve_remotes", "pbs_remotes", "failed_remotes", "sections_fresh"),
    "pdm_capacity": (
        "pve_cpu_stats", "pve_memory_stats", "pve_storage_stats",
        "pbs_cpu_stats", "pbs_memory_stats", "pbs_storage_stats",
    ),
    "pdm_inventory": (
        "pve_nodes", "pbs_nodes", "qemu", "lxc", "storages", "pbs_datastores", "sdn_zones",
    ),
    "pdm_updates": (
        "remotes", "oldest_last_refresh", "newest_last_refresh", "oldest_refresh_age",
        "endpoint_fresh", "snapshot_complete",
    ),
    "pdm_remote_status": ("remote_type", "subscription", "status_fresh"),
    "pdm_remote_overview": ("inventory", "capacity", "resources_fresh"),
}


def build_pdm_dashboard_model(inventory, layout=None):
    """Bind only the existing PDM sensor types."""
    layout = get_dashboard_layout("pdm") if layout is None else layout
    if layout["type"] != "pdm":
        raise ValueError("PDM resource mapping requires a PDM layout")
    groups = []
    for entry in sorted(inventory["entries"], key=lambda item: item["entry_id"]):
        if entry["platform_type"] != "PDM" or not entry.get("pdm_identity_id"):
            continue
        blocks = {block["id"]: {} for block in layout["blocks"]}
        for resource in sorted(inventory["resources"], key=lambda item: item["resource_id"]):
            if resource["entry_id"] != entry["entry_id"]:
                continue
            for entity in sorted(resource["entities"], key=lambda item: item["entity_id"]):
                key = entity.get("translation_key")
                if entity["domain"] != "sensor":
                    continue
                block = _ROOT_BLOCKS.get(key)
                if resource["kind"] == "pdm_remote" and key in (
                    "pdm_remote_status", "pdm_remote_overview"
                ):
                    block = "remotes"
                if block is None:
                    continue
                item = blocks[block].setdefault(resource["resource_id"], {
                    "resource_id": resource["resource_id"],
                    "kind": resource["kind"],
                    "title": resource["title"],
                    "references": [],
                })
                metric = key.removeprefix("pdm_").removeprefix("remote_")
                item["references"].append({"entity_id": entity["entity_id"], "metric": metric})
                for attribute in _ATTRIBUTES[key]:
                    if attribute in entity.get("attributes", ()):
                        item["references"].append({
                            "entity_id": entity["entity_id"],
                            "metric": attribute,
                            "attribute": attribute,
                        })
        result = {}
        for block, resources in blocks.items():
            result[block] = sorted(
                resources.values(), key=lambda item: (item["title"].casefold(), item["resource_id"])
            )
            for resource in result[block]:
                resource["references"].sort(
                    key=lambda ref: (ref.get("attribute") is not None, ref["metric"], ref["entity_id"])
                )
        if any(result.values()):
            groups.append({
                "entry_id": entry["entry_id"],
                "pdm_identity_id": entry["pdm_identity_id"],
                "title": entry["title"],
                "blocks": result,
            })
    return {"schema_version": 1, "type": "pdm", "groups": groups}
