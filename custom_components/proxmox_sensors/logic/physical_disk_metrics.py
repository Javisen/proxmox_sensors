"""Availability and cleanup rules for optional Physical Disk metrics."""

import math
import re


def controller_health_source(disk):
    return (isinstance(disk, dict)
            and (disk.get("device_type") == "ssacli"
                 or disk.get("health_source") == "ssacli"))


def disk_monitoring_metrics(disk):
    """Select evidence-appropriate health metrics for one disk record."""
    if not isinstance(disk, dict):
        return []
    if controller_health_source(disk):
        return ["controller_health", "temperature_c", "power_on_hours"]
    kind = str(disk.get("type") or "").lower()
    metrics = ["smart_status", "temperature_c", "power_on_hours"]
    if kind == "nvme":
        return metrics + ["smart_poll_status", "available_spare", "media_errors"]
    if kind == "hdd":
        metrics += ["reallocated_sectors", "pending_sectors"]
        model = str(disk.get("model") or "").strip()
        vendor = str(disk.get("vendor") or "")
        if ("seagate" in vendor.casefold() or "seagate" in model.casefold()
                or re.match(r"^ST[0-9]{3,}", model, re.IGNORECASE)):
            metrics.append("seek_error_rate")
    elif kind == "ssd":
        metrics.append("reallocated_sectors")
    return metrics


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
