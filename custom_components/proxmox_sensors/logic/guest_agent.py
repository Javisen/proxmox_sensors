"""Pure helpers for QEMU Guest Agent filesystem metrics."""

from __future__ import annotations

import asyncio
from math import isfinite


def _byte_value(value):
    """Return a non-negative finite byte count, or ``None``."""
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not isfinite(number) or number < 0 or not number.is_integer():
        return None
    return int(number)


def _disk_identity(disk):
    """Return a structured QGA disk identity without using guest device names."""
    if not isinstance(disk, dict):
        return None

    bus_type = disk.get("bus-type")
    address = (disk.get("bus"), disk.get("target"), disk.get("unit"))
    if (
        isinstance(bus_type, str)
        and bus_type.strip()
        and all(isinstance(value, int) and not isinstance(value, bool) for value in address)
    ):
        return ("address", bus_type.strip(), *address)

    serial = disk.get("serial")
    if isinstance(serial, str) and serial.strip():
        return ("serial", serial.strip())
    return None


def _disk_identities(filesystem):
    disks = filesystem.get("disk") if isinstance(filesystem, dict) else None
    if not isinstance(disks, list) or not disks:
        return None
    identities = {_disk_identity(disk) for disk in disks}
    if None in identities or not identities:
        return None
    return identities


def _filesystem_metrics(filesystem):
    if not isinstance(filesystem, dict):
        return None
    total = _byte_value(filesystem.get("total-bytes"))
    used = _byte_value(filesystem.get("used-bytes"))
    if total is None or used is None or total <= 0 or used > total:
        return None
    free = total - used
    return {
        "mountpoint": filesystem.get("mountpoint"),
        "total": total,
        "used": used,
        "free": free,
        "usage": round(used / total * 100, 2),
        "filesystem_type": filesystem.get("type"),
    }


def build_vm_disk_usage(filesystems):
    """Build conservative Linux disk-usage data from ``get-fsinfo``.

    The root filesystem is authoritative for the entity state. Other
    filesystems are included only when QGA supplies a complete structured disk
    identity and at least one of their backing disks differs from root's.
    """
    if not isinstance(filesystems, list):
        return None

    roots = [
        filesystem
        for filesystem in filesystems
        if isinstance(filesystem, dict) and filesystem.get("mountpoint") == "/"
    ]
    if len(roots) != 1:
        return None

    root = roots[0]
    root_metrics = _filesystem_metrics(root)
    root_disks = _disk_identities(root)
    if root_metrics is None:
        return None

    additional = []
    if root_disks is not None:
        for filesystem in filesystems:
            if filesystem is root or not isinstance(filesystem, dict):
                continue
            disks = _disk_identities(filesystem)
            metrics = _filesystem_metrics(filesystem)
            if (
                disks is None
                or metrics is None
                or {identity[0] for identity in disks}
                != {identity[0] for identity in root_disks}
                or not (disks - root_disks)
            ):
                continue
            additional.append(metrics)

    root_metrics.pop("mountpoint", None)
    root_metrics["additional_filesystems"] = additional
    return root_metrics


async def collect_vm_disk_usage(
    raw_vms,
    *,
    guest_key_for,
    is_selected,
    fetch_fsinfo,
    last_good,
):
    """Collect per-VM metrics without letting one Guest Agent fail the cycle."""
    current_keys = set()
    statuses = {}

    async def _fetch_one(vm, guest_key):
        try:
            filesystems = await fetch_fsinfo(vm["vmid"])
        except Exception:
            statuses[guest_key] = "error"
            return

        statuses[guest_key] = "ok"
        usage = build_vm_disk_usage(filesystems)
        if usage is None:
            last_good.pop(guest_key, None)
        else:
            last_good[guest_key] = usage

    tasks = []
    for vm in raw_vms or []:
        if not isinstance(vm, dict) or vm.get("vmid") is None:
            continue
        guest_key = guest_key_for(vm["vmid"])
        if not is_selected(vm, guest_key):
            continue
        current_keys.add(guest_key)
        if str(vm.get("status", "")).lower() != "running":
            statuses[guest_key] = "stopped"
            continue
        tasks.append(_fetch_one(vm, guest_key))

    if tasks:
        await asyncio.gather(*tasks)

    for guest_key in set(last_good) - current_keys:
        last_good.pop(guest_key, None)

    return (
        {
            guest_key: last_good[guest_key]
            for guest_key in current_keys
            if guest_key in last_good
        },
        statuses,
    )
