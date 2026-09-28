"""Shared diagnostics for ambiguous legacy guest identities."""

from __future__ import annotations

import logging


_LOGGER = logging.getLogger(__name__)
_WARNING_KEYS = "ambiguous_guest_identity_warnings"


def warn_ambiguous_guest(runtime, entry_id, kind, vmid, node) -> None:
    """Log once when a config entry omits a guest with conflicting identities."""
    normalized_kind = str(kind).lower()
    key = (str(entry_id), normalized_kind, str(vmid))
    warned = runtime.setdefault(_WARNING_KEYS, set())
    if key in warned:
        return
    warned.add(key)
    _LOGGER.warning(
        "Skipping selected %s %s on node %s for config entry %s because "
        "incompatible legacy identities were found; the guest was omitted for safety",
        normalized_kind.upper(),
        vmid,
        node,
        entry_id,
    )
