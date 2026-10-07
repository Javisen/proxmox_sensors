"""Declarative logical layouts; no resource binding or Lovelace generation."""

from copy import deepcopy


_STYLE = {
    "name": "proxmox",
    "accent_color": "#ef7d00",
    "requires_card_mod": True,
    "normal_card": {
        "css": "ha-card {\n"
        "  --card-mod-icon-color: #ef7d00;\n"
        "  background: #0000 !important;\n"
        "  border: 1px solid #333333 !important;\n"
        "  border-left: 5px solid #ef7d00 !important;\n"
        "  color: white !important;\n"
        "}",
    },
    "header_card": {
        "css": "ha-card {\n"
        "  --card-mod-icon-color: white;\n"
        "  background: #ef7d00 !important;\n"
        "  border: 1px solid #ef7d00 !important;\n"
        "  color: white !important;\n"
        "}",
    },
}

# IDs and order are a logical contract, not frontend view/section identifiers.
_BLOCKS = {
    "pdm": (
        ("header", "Proxmox Datacenter Manager", "mdi:view-dashboard", "header"),
        ("datacenter_status", "Datacenter Status", "mdi:heart-pulse", "summary"),
        ("capacity", "Datacenter Capacity", "mdi:database", "summary"),
        ("inventory", "Datacenter Inventory", "mdi:server-network", "summary"),
        ("updates", "Datacenter Updates", "mdi:package-up", "activity"),
        ("remotes", "PVE / PBS Remotes", "mdi:lan-connect", "resource_group"),
    ),
    "pve": (
        ("header", "Proxmox VE", "mdi:server", "header"),
        ("node_health", "Node health", "mdi:heart-pulse", "summary"),
        ("temperatures", "Temperatures", "mdi:thermometer", "metrics"),
        ("storage", "Storage", "mdi:database", "resource_group"),
        ("guests", "VM / LXC", "mdi:desktop-tower", "resource_group"),
        ("replication", "Replication", "mdi:content-copy", "resource_group"),
        ("tasks", "Tasks", "mdi:format-list-checks", "activity"),
        ("node_info", "Node Info", "mdi:information-outline", "summary"),
        ("diagnostics", "Diagnostics", "mdi:stethoscope", "diagnostics"),
    ),
    "pbs": (
        ("header", "Proxmox Backup Server", "mdi:backup-restore", "header"),
        ("server_health", "Server health", "mdi:heart-pulse", "summary"),
        ("datastores", "Datastores", "mdi:database", "resource_group"),
        ("backups", "Backups", "mdi:backup-restore", "resource_group"),
        ("maintenance", "Maintenance", "mdi:tools", "resource_group"),
        ("tasks", "Tasks", "mdi:format-list-checks", "activity"),
        ("diagnostics", "Diagnostics", "mdi:stethoscope", "diagnostics"),
    ),
    "cluster": (
        ("header", "Proxmox Cluster", "mdi:server-network", "header"),
        ("cluster_health", "Cluster health", "mdi:heart-pulse", "summary"),
        ("nodes", "Nodes", "mdi:server", "resource_group"),
        ("guests", "VM / LXC", "mdi:desktop-tower", "resource_group"),
        ("storage", "Aggregate storage", "mdi:database", "summary"),
        ("replication", "Replication", "mdi:content-copy", "resource_group"),
        ("backup_health", "Backup health", "mdi:backup-restore", "summary"),
        ("ha", "High availability", "mdi:shield-check", "summary"),
        ("tasks", "Tasks / errors", "mdi:format-list-checks", "activity"),
        ("diagnostics", "Diagnostics", "mdi:stethoscope", "diagnostics"),
    ),
}

_GROUPING = {
    "pdm": {"scope": "datacenter", "keys": ["entry_id", "pdm_identity_id"]},
    "pve": {"scope": "node", "keys": ["entry_id"]},
    "pbs": {"scope": "server", "keys": ["entry_id", "server_id"]},
    "cluster": {"scope": "cluster", "keys": ["entry_id", "cluster_id"]},
}


def get_dashboard_layout(dashboard_type):
    """Return an independent JSON-compatible specification for a known family.

    Position is ascending and one-based. Content blocks permit multiple resources
    within each declared scope, and must be omitted if future binding finds none.
    The header is dashboard-wide. The specification itself never asserts that
    data exists, chooses entities, or determines frontend views versus sections.
    """
    if not isinstance(dashboard_type, str) or dashboard_type not in _BLOCKS:
        raise ValueError(f"Unknown dashboard type: {dashboard_type!r}")
    blocks = []
    for position, (block_id, title, icon, block_type) in enumerate(_BLOCKS[dashboard_type], 1):
        header = block_type == "header"
        block = {
            "id": block_id, "title": title, "icon": icon,
            "block_type": block_type, "position": position,
            "multiple_resources": not header, "omit_if_empty": not header,
            "style": "header_card" if header else "normal_card",
            "scope": "dashboard" if header else "resource_group",
        }
        if dashboard_type == "pbs" and block_id == "maintenance":
            block["operations"] = ["gc", "prune", "verify", "sync"]
        blocks.append(block)
    return {
        "schema_version": 1,
        "type": dashboard_type,
        "title": _BLOCKS[dashboard_type][0][1],
        "grouping": deepcopy(_GROUPING[dashboard_type]),
        "style": deepcopy(_STYLE),
        "blocks": blocks,
    }
