"""Helpers for computing Proxmox node sensor values and attributes"""

from __future__ import annotations


def format_node_sensor_value(sensor_id, value):
    """Format a raw node sensor value without changing its exposed semantics."""
    if sensor_id == "pveversion" and isinstance(value, str):
        parts = value.split("/")
        if len(parts) >= 2:
            return parts[1]

    if sensor_id in ["cpu", "wait"] and isinstance(value, (int, float)):
        return round(value * 100, 2)

    if sensor_id == "uptime" and isinstance(value, (int, float)):
        days = int(value // 86400)
        hours = int((value % 86400) // 3600)
        minutes = int((value % 3600) // 60)
        return f"{days}d {hours}h {minutes}m"

    if isinstance(value, dict):
        return value.get("release") or value.get("version", "").split("\n")[0] or None

    if isinstance(value, str):
        return value.split("\n")[0]

    return value


def build_cpu_sensor_attributes(node_data):
    """Build extra attributes for the CPU usage sensor."""
    cpu = node_data.get("cpu")
    cpuinfo = node_data.get("cpuinfo", {})
    cores = cpuinfo.get("cores")

    attrs = {}

    if cores:
        attrs["cpu_cores"] = cores

        if cpu is not None:
            try:
                attrs["cpu_average_per_core"] = round((cpu * 100) / cores, 2)
            except (ValueError, TypeError, ZeroDivisionError):
                pass

    return attrs


def build_cluster_task_attributes(task, tasks_list):
    """Build exposed task attributes while keeping output compatibility."""
    errors = [
        f"{t.get('type')}: {t.get('status')}"
        for t in tasks_list
        if t.get("status") and "OK" not in t.get("status")
    ]

    return {
        "user": task.get("user"),
        "status_raw": task.get("status"),
        "recent_errors": errors[:5] if errors else 0,
    }


def calculate_percentage_usage(used, total, zero_total_value=0, fallback_total=1):
    """Calculate a percentage with the same rounding used by node sensors."""
    if total == 0:
        return zero_total_value
    return round((used / (total or fallback_total)) * 100, 2)


def bytes_to_gb(bytes_size):
    """Convert bytes to gigabytes rounded to two decimals."""
    if not bytes_size:
        return 0
    return round(bytes_size / (1024**3), 2)


def format_bytes_size(bytes_size):
    """Format a byte value using compact binary units for display."""
    if bytes_size == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    index = 0
    size = float(bytes_size)

    while size >= 1024 and index < len(size_names) - 1:
        size /= 1024
        index += 1

    if index >= 3:
        return f"{size:.2f} {size_names[index]}"
    if index >= 1:
        return f"{size:.1f} {size_names[index]}"
    return f"{size:.0f} {size_names[index]}"


def parse_load_average(load, position=0, default=0):
    """Safely parse a load-average entry from a load list."""
    try:
        return float(load[position]) if len(load) > position else default
    except (ValueError, TypeError):
        return default


def calculate_node_score(node_data):
    """Calculate the node performance score where lower values are better."""
    cpu = node_data.get("cpu", 0)
    memory = node_data.get("memory", {})
    wait = node_data.get("wait", 0)
    load = node_data.get("loadavg", [])
    cores = node_data.get("cpuinfo", {}).get("cores", 1)

    cpu_p = cpu * 100 if isinstance(cpu, (int, float)) else 0
    ram_p = (
        (memory.get("used", 0) / memory.get("total", 1)) * 100
        if memory.get("total")
        else 0
    )
    io = wait * 100 if isinstance(wait, (int, float)) else 0
    load1 = parse_load_average(load)
    load_ratio = load1 / cores if cores else 0

    score = cpu_p * 0.4 + ram_p * 0.3 + (load_ratio * 100) * 0.2 + io * 0.1
    return round(score, 2)


def classify_node_score(score):
    """Map a numeric node score to its exposed health label."""
    if score < 20:
        return "Excellent"
    if score < 40:
        return "Good"
    if score < 60:
        return "Moderate"
    if score < 80:
        return "High"
    return "Critical"


def build_node_load_attributes(node_data):
    """Build 1m/5m/15m load average attributes and the derived status."""
    load = node_data.get("loadavg", [])
    cpuinfo = node_data.get("cpuinfo", {})
    cores = cpuinfo.get("cores")

    load1 = parse_load_average(load, 0)
    load5 = parse_load_average(load, 1)
    load15 = parse_load_average(load, 2)

    status = "OK"
    if cores:
        if load1 > cores:
            status = "Overloaded"
        elif load1 > cores * 0.7:
            status = "High"

    return {
        "load_1m": load1,
        "load_5m": load5,
        "load_15m": load15,
        "cores": cores,
        "status": status,
    }


def classify_iowait_level(percent):
    """Classify IO wait pressure based on the exposed thresholds."""
    if percent < 2:
        return "Low"
    if percent < 5:
        return "Moderate"
    if percent < 10:
        return "High"
    return "Critical"


def build_iowait_attributes(value):
    """Build IO wait sensor attributes from the raw wait value."""
    percent = round(value * 100, 2) if isinstance(value, (int, float)) else 0
    return {
        "raw": value,
        "level": classify_iowait_level(percent),
    }


def build_storage_details(storage_data):
    """Build per-storage usage details for node overview sensors."""
    storage_details = []

    for storage_name, storage_info in storage_data.items():
        if not isinstance(storage_info, dict):
            continue

        total_bytes = storage_info.get("total", 0) or 0
        used_bytes = storage_info.get("used", 0) or 0

        if total_bytes == 0 and used_bytes == 0:
            continue

        free_bytes = max(total_bytes - used_bytes, 0)
        percentage = (
            round(min((used_bytes / total_bytes) * 100, 100), 1)
            if total_bytes > 0
            else 0
        )

        storage_details.append(
            {
                "name": storage_name,
                "type": storage_info.get("type", "unknown"),
                "total_gb": bytes_to_gb(total_bytes),
                "used_gb": bytes_to_gb(used_bytes),
                "free_gb": bytes_to_gb(free_bytes),
                "percentage": percentage,
            }
        )

    return storage_details


def count_node_guests(items, node_name):
    """Count VM or CT items assigned to a node."""
    count = 0
    for item_info in items.values():
        if isinstance(item_info, dict) and item_info.get("node") == node_name:
            count += 1
    return count


def count_active_node_tasks(tasks, node_name):
    """Count non-finished tasks belonging to a node."""
    count = 0
    for task in tasks:
        if isinstance(task, dict) and task.get("node") == node_name:
            if task.get("status") not in ["OK", "stopped"]:
                count += 1
    return count


def build_node_overview_attributes(data, node_name):
    """Build the attribute payload exposed by the node overview entity."""
    node_data = data.get("node", {})
    storage_details = build_storage_details(data.get("storage", {}))
    node_status = data.get("node_status_map", {}).get(node_name, "unknown")

    cpu_usage = node_data.get("cpu", 0)
    if isinstance(cpu_usage, (int, float)):
        cpu_usage = round(cpu_usage * 100, 2)

    memory_data = node_data.get("memory", {})
    memory_used = memory_data.get("used", 0)
    memory_total = memory_data.get("total", 1)
    memory_percentage = (
        round((memory_used / memory_total) * 100, 2) if memory_total > 0 else 0
    )

    cpu_per_core = None
    if cpu_usage and node_data.get("cpuinfo", {}).get("cores"):
        cores = node_data.get("cpuinfo", {}).get("cores")
        cpu_per_core = round(cpu_usage / cores, 2)

    return {
        "node_name": node_name,
        "status": node_status,
        "cpu_average_per_core": cpu_per_core,
        "memory_usage_percent": memory_percentage,
        "vm_count": count_node_guests(data.get("vms", {}), node_name),
        "ct_count": count_node_guests(data.get("cts", {}), node_name),
        "storage_count": len(storage_details),
        "active_tasks": count_active_node_tasks(data.get("tasks", []), node_name),
        "storage_details": storage_details,
        "last_update": data.get("last_update", "unknown"),
        "pve_version": node_data.get("pveversion", "unknown"),
        "kernel_version": node_data.get("kversion", "unknown"),
        "uptime_seconds": node_data.get("uptime", 0),
    }


def build_storage_summary_attributes(storage_data, node_name, last_update):
    """Build the storage summary attributes exposed by the node storage sensor."""
    if not storage_data:
        return {
            "node": node_name,
            "storages": [],
            "count": 0,
            "message": "No storage data available",
        }

    storages_list = []
    total_capacity_bytes = 0
    total_used_bytes = 0
    type_accumulators = {}

    for storage_name, storage_info in storage_data.items():
        if not isinstance(storage_info, dict):
            continue

        total_bytes = storage_info.get("total", 0) or 0
        used_bytes = storage_info.get("used", 0) or 0
        avail_bytes = storage_info.get("avail", 0) or 0

        if avail_bytes == 0 and total_bytes > 0:
            avail_bytes = max(total_bytes - used_bytes, 0)

        percentage = (
            round((used_bytes / total_bytes * 100), 1) if total_bytes > 0 else 0
        )
        storage_type = storage_info.get("type", "unknown")

        if storage_type not in type_accumulators:
            type_accumulators[storage_type] = {"count": 0, "total_bytes": 0}
        type_accumulators[storage_type]["count"] += 1
        type_accumulators[storage_type]["total_bytes"] += total_bytes

        storages_list.append(
            {
                "name": storage_name,
                "type": storage_type,
                "path": storage_info.get("path", ""),
                "content": storage_info.get("content", ""),
                "total": format_bytes_size(total_bytes),
                "used": format_bytes_size(used_bytes),
                "free": format_bytes_size(avail_bytes),
                "total_gb": bytes_to_gb(total_bytes),
                "used_gb": bytes_to_gb(used_bytes),
                "free_gb": bytes_to_gb(avail_bytes),
                "percentage": percentage,
                "active": storage_info.get("active", 1) == 1,
                "enabled": storage_info.get("enabled", 1) == 1,
            }
        )

        total_capacity_bytes += total_bytes
        total_used_bytes += used_bytes

    total_free_bytes = max(total_capacity_bytes - total_used_bytes, 0)
    total_percentage = (
        round((total_used_bytes / total_capacity_bytes * 100), 1)
        if total_capacity_bytes > 0
        else 0
    )

    by_type = {}
    for storage_type, accumulator in type_accumulators.items():
        total_bytes_for_type = accumulator["total_bytes"]
        by_type[storage_type] = {
            "count": accumulator["count"],
            "total_capacity": format_bytes_size(total_bytes_for_type),
            "total_capacity_gb": bytes_to_gb(total_bytes_for_type),
        }

    return {
        "node": node_name,
        "storages": [storage["name"] for storage in storages_list],
        "count": len(storages_list),
        "storage_details": storages_list,
        "total_capacity": format_bytes_size(total_capacity_bytes),
        "total_used": format_bytes_size(total_used_bytes),
        "total_free": format_bytes_size(total_free_bytes),
        "total_capacity_gb": bytes_to_gb(total_capacity_bytes),
        "total_used_gb": bytes_to_gb(total_used_bytes),
        "total_free_gb": bytes_to_gb(total_free_bytes),
        "total_percentage": total_percentage,
        "by_type": by_type,
        "last_update": last_update,
        "summary": (
            f"{len(storages_list)} storages, "
            f"{format_bytes_size(total_capacity_bytes)} total, "
            f"{total_percentage}% used"
        ),
    }
