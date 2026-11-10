"""Availability and cleanup rules for optional Physical Disk metrics."""

import math


def percentage_used_available(kind, snapshot):
    if kind != "nvme" or not isinstance(snapshot, dict):
        return False
    data = snapshot.get("data")
    if not isinstance(data, dict) or "nvme" not in str(data.get("device_type") or "").lower():
        return False
    value = data.get("percentage_used")
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value) and value >= 0)


def percentage_used_obsolete(kind, snapshot):
    if kind != "nvme":
        return True
    return (isinstance(snapshot, dict) and snapshot.get("status") == "ok"
            and not percentage_used_available(kind, snapshot))


def owned_percentage_row(row, entry_id, identifier, device_id, domain):
    return (row.config_entry_id == entry_id and row.domain == "sensor"
            and row.platform == domain
            and row.unique_id == f"{identifier}_percentage_used"
            and row.device_id in (None, device_id))
