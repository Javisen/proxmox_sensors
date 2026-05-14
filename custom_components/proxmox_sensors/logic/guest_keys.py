"""Utilities for stable guest keys across cluster nodes"""

from __future__ import annotations


def make_guest_key(node, vmid):
    """Build a node-aware guest key using the ``node:vmid`` format."""
    return f"{str(node).lower()}:{str(vmid)}"


def matches_selected_guest(selected_values, node, vmid, guest_key=None):
    """Return ``True`` when a selected value matches a guest.

    Supports legacy selections by raw VMID and newer selections by guest key.
    """
    if not selected_values:
        return True

    normalized = {str(value) for value in selected_values}
    vmid_str = str(vmid)
    canonical_key = make_guest_key(node, vmid)
    explicit_key = str(guest_key) if guest_key is not None else canonical_key
    raw_node_key = f"{node}:{vmid_str}"

    return any(
        candidate in normalized
        for candidate in (vmid_str, explicit_key, canonical_key, raw_node_key)
    )
