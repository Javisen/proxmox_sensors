"""Regression tests for Guest Agent VM disk-usage selection.

``logic/guest_agent.py`` has no Home Assistant imports, so it is loaded
directly from its file path to keep these tests free of HA dependencies.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "proxmox_sensors"
    / "logic"
    / "guest_agent.py"
)
_SPEC = importlib.util.spec_from_file_location("guest_agent", _MODULE_PATH)
guest_agent = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(guest_agent)

build_vm_disk_usage = guest_agent.build_vm_disk_usage

GB = 1_000_000_000


def _scsi(unit=0, target=0):
    return {"bus-type": "scsi", "bus": 0, "target": target, "unit": unit}


def _fs(mountpoint, fs_type, used, total, disks=None, name="sda1"):
    filesystem = {"name": name, "mountpoint": mountpoint, "type": fs_type}
    if total is not None:
        filesystem["total-bytes"] = total
    if used is not None:
        filesystem["used-bytes"] = used
    if disks is not None:
        filesystem["disk"] = disks
    return filesystem


# Shapes taken from get-fsinfo on real guests (see issue #86).
HAOS_FSINFO = [
    _fs("/", "erofs", 218_000_000, 218_000_000, [_scsi()], "sda5"),
    _fs("/mnt/data", "ext4", 23_200_000_000, 52_000_000_000, [_scsi()], "sda8"),
    _fs("/mnt/overlay", "ext4", 1_000_000, 100_000_000, [_scsi()], "sda7"),
    _fs("/mnt/boot", "vfat", 10_000_000, 33_000_000, [_scsi()], "sda1"),
    _fs("/tmp", "ext4", 0, 2_000_000, [{"bus-type": "unknown"}], "zram2"),
]

WINDOWS_FSINFO = [
    _fs("C:\\", "NTFS", 30_200_000_000, 67_600_000_000, [_scsi()], "\\\\?\\Volume{c}\\"),
    _fs("System Reserved", "NTFS", None, None, [_scsi()], "\\\\?\\Volume{r1}\\"),
    _fs("System Reserved", "FAT32", None, None, [_scsi()], "\\\\?\\Volume{r2}\\"),
]


def _expected(used, total, fs_type, additional=()):
    return {
        "total": total,
        "used": used,
        "free": total - used,
        "usage": round(used / total * 100, 2),
        "filesystem_type": fs_type,
        "additional_filesystems": list(additional),
    }


# --- Existing behaviour for writable-root Linux guests ---------------------


def test_writable_root_is_reported_as_before():
    filesystems = [
        _fs("/", "ext4", 8 * GB, 32 * GB, [_scsi()]),
        _fs("/boot/efi", "vfat", 1_000_000, 500_000_000, [_scsi()]),
    ]

    assert build_vm_disk_usage(filesystems) == _expected(8 * GB, 32 * GB, "ext4")


def test_writable_root_keeps_additional_filesystems_on_other_disks():
    filesystems = [
        _fs("/", "xfs", 8 * GB, 32 * GB, [_scsi(unit=0)]),
        _fs("/srv", "ext4", 50 * GB, 200 * GB, [_scsi(unit=1)], "sdb1"),
    ]

    usage = build_vm_disk_usage(filesystems)

    assert usage == _expected(
        8 * GB,
        32 * GB,
        "xfs",
        [
            {
                "mountpoint": "/srv",
                "total": 200 * GB,
                "used": 50 * GB,
                "free": 150 * GB,
                "usage": 25.0,
                "filesystem_type": "ext4",
            }
        ],
    )


def test_writable_root_is_not_replaced_by_a_larger_filesystem():
    filesystems = [
        _fs("/", "ext4", 1 * GB, 10 * GB, [_scsi(unit=0)]),
        _fs("/data", "ext4", 100 * GB, 1000 * GB, [_scsi(unit=1)], "sdb1"),
    ]

    usage = build_vm_disk_usage(filesystems)

    assert usage["total"] == 10 * GB
    assert usage["filesystem_type"] == "ext4"


def test_writable_root_wins_even_when_c_drive_is_present():
    filesystems = [
        _fs("/", "ext4", 1 * GB, 10 * GB, [_scsi()]),
        _fs("C:\\", "NTFS", 30 * GB, 60 * GB, [_scsi(unit=1)]),
    ]

    assert build_vm_disk_usage(filesystems)["total"] == 10 * GB


@pytest.mark.parametrize("filesystems", [None, {}, "x", []])
def test_invalid_or_empty_input_returns_none(filesystems):
    assert build_vm_disk_usage(filesystems) is None


def test_duplicate_root_returns_none():
    filesystems = [
        _fs("/", "ext4", 1 * GB, 10 * GB),
        _fs("/", "ext4", 1 * GB, 10 * GB),
    ]

    assert build_vm_disk_usage(filesystems) is None


def test_writable_root_without_valid_size_returns_none():
    filesystems = [
        _fs("/", "ext4", None, None),
        _fs("/data", "ext4", 1 * GB, 10 * GB),
    ]

    assert build_vm_disk_usage(filesystems) is None


# --- Read-only image root (HAOS and similar) --------------------------------


def test_haos_read_only_root_uses_largest_writable_filesystem():
    assert build_vm_disk_usage(HAOS_FSINFO) == _expected(
        23_200_000_000, 52_000_000_000, "ext4"
    )


@pytest.mark.parametrize("fs_type", ["squashfs", "EROFS", " SquashFS "])
def test_read_only_image_types_match_case_insensitively(fs_type):
    filesystems = [
        _fs("/", fs_type, 1 * GB, 1 * GB, [_scsi()]),
        _fs("/data", "ext4", 2 * GB, 8 * GB, [_scsi()]),
    ]

    assert build_vm_disk_usage(filesystems)["total"] == 8 * GB


def test_read_only_root_ignores_writable_filesystems_without_valid_size():
    filesystems = [
        _fs("/", "erofs", 1 * GB, 1 * GB, [_scsi()]),
        _fs("/big", "ext4", None, 500 * GB, [_scsi()]),
        _fs("/data", "ext4", 2 * GB, 8 * GB, [_scsi()]),
    ]

    assert build_vm_disk_usage(filesystems)["total"] == 8 * GB


def test_read_only_root_ignores_other_read_only_images():
    filesystems = [
        _fs("/", "erofs", 1 * GB, 1 * GB, [_scsi()]),
        _fs("/snap/core", "squashfs", 100 * GB, 100 * GB, [_scsi()]),
        _fs("/data", "ext4", 2 * GB, 8 * GB, [_scsi()]),
    ]

    assert build_vm_disk_usage(filesystems)["total"] == 8 * GB


def test_read_only_root_without_writable_filesystem_falls_back_to_root():
    filesystems = [_fs("/", "erofs", 1 * GB, 1 * GB, [_scsi()])]

    assert build_vm_disk_usage(filesystems) == _expected(1 * GB, 1 * GB, "erofs")


def test_read_only_root_selection_reports_other_disks_as_additional():
    filesystems = [
        _fs("/", "erofs", 1 * GB, 1 * GB, [_scsi(unit=0)]),
        _fs("/mnt/data", "ext4", 20 * GB, 50 * GB, [_scsi(unit=0)]),
        _fs("/mnt/extra", "ext4", 1 * GB, 10 * GB, [_scsi(unit=1)], "sdb1"),
    ]

    usage = build_vm_disk_usage(filesystems)

    assert usage["total"] == 50 * GB
    assert [fs["mountpoint"] for fs in usage["additional_filesystems"]] == [
        "/mnt/extra"
    ]


# --- Guests with no / (Windows) ---------------------------------------------


def test_windows_guest_uses_c_drive():
    assert build_vm_disk_usage(WINDOWS_FSINFO) == _expected(
        30_200_000_000, 67_600_000_000, "NTFS"
    )


def test_windows_c_drive_matches_case_insensitively():
    filesystems = [_fs("c:\\", "NTFS", 1 * GB, 4 * GB, [_scsi()])]

    assert build_vm_disk_usage(filesystems)["total"] == 4 * GB


def test_windows_c_drive_reports_other_disks_as_additional():
    filesystems = WINDOWS_FSINFO + [
        _fs("D:\\", "NTFS", 10 * GB, 100 * GB, [_scsi(unit=1)], "\\\\?\\Volume{d}\\"),
    ]

    usage = build_vm_disk_usage(filesystems)

    assert usage["total"] == 67_600_000_000
    assert [fs["mountpoint"] for fs in usage["additional_filesystems"]] == ["D:\\"]


def test_no_root_and_no_c_drive_returns_none():
    filesystems = [_fs("D:\\", "NTFS", 1 * GB, 4 * GB, [_scsi()])]

    assert build_vm_disk_usage(filesystems) is None


def test_duplicate_c_drive_returns_none():
    filesystems = [
        _fs("C:\\", "NTFS", 1 * GB, 4 * GB),
        _fs("C:\\", "NTFS", 1 * GB, 4 * GB),
    ]

    assert build_vm_disk_usage(filesystems) is None


def test_c_drive_without_valid_size_returns_none():
    filesystems = [_fs("C:\\", "NTFS", None, None)]

    assert build_vm_disk_usage(filesystems) is None
