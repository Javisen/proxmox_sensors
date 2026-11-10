"""Per-device Physical Disk type overrides."""

TYPE_KEY = "physical_disk_type_v2"
TYPE_OPTIONS = ("automatic", "hdd", "ssd", "nvme")
DETECTED_TYPES = frozenset(TYPE_OPTIONS[1:])


def selected_type(options, identifier):
    saved = options.get(TYPE_KEY)
    value = saved.get(identifier, "automatic") if isinstance(saved, dict) else "automatic"
    return value if value in TYPE_OPTIONS else "automatic"


def effective_type(disk, options, identifier):
    selected = selected_type(options, identifier)
    if selected != "automatic":
        return selected
    detected = str(disk.get("type") or "").lower()
    return detected if detected in DETECTED_TYPES else "disk"


def apply_inventory_types(disks, identities, options):
    return {
        path: {**disk, "type": effective_type(disk, options, identities[path])}
        if path in identities else disk
        for path, disk in disks.items()
    }


def with_type(options, identifier, value):
    if value not in TYPE_OPTIONS:
        raise ValueError("Invalid Physical Disk type")
    updated = dict(options)
    saved = updated.get(TYPE_KEY)
    types = dict(saved) if isinstance(saved, dict) else {}
    if value == "automatic":
        types.pop(identifier, None)
    else:
        types[identifier] = value
    if types:
        updated[TYPE_KEY] = types
    else:
        updated.pop(TYPE_KEY, None)
    return updated
