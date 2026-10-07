"""Pure availability of dashboard families from the complete normalized inventory."""

DASHBOARD_TYPES = ("pdm", "pve", "pbs", "cluster")


def representable_entities(resource, *, include_controls=False):
    """Use the static generator's entity policy, independently of live state."""
    return [entity for entity in resource["entities"]
            if include_controls or entity["domain"] != "button"]


def available_dashboard_types(inventory):
    """Return families with default-plan content, in a stable public order.

    Resource entry_id is the normalized display owner, unlike entity ownership.
    VM/CT resources (including guest Replication) are PVE even with cluster scope.
    Other resources use their display entry's normalized platform_type. No names,
    unique IDs, device ownership or cluster membership are reclassified here.
    """
    platforms = {entry["entry_id"]: entry["platform_type"].lower()
                 for entry in inventory["entries"]}
    available = set()
    for resource in inventory["resources"]:
        platform = platforms.get(resource["entry_id"])
        if platform not in DASHBOARD_TYPES or not representable_entities(resource):
            continue
        available.add("pve" if resource["kind"] in ("vm", "ct") else platform)
    return [kind for kind in DASHBOARD_TYPES if kind in available]
