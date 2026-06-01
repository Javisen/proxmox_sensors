"""Helpers for parsing and resolving Proxmox cluster notification settings.

This module keeps notification parsing logic independent from Home Assistant
entity classes so sensors and binary sensors can expose normalized values
without duplicating string handling.
"""

from __future__ import annotations


DISABLED_NOTIFICATION_VALUES = {"", "0", "false", "off", "none", "disabled", "never"}


def _normalize_notify_key(key):
    """Normalize notify keys from Proxmox into snake_case."""
    return str(key).strip().lower().replace("-", "_")


def parse_notify_string(notify_value):
    """Parse a Proxmox ``notify`` string into a normalized dictionary.

    Proxmox exposes notification settings as a compact string with key/value
    pairs such as ``"package-updates=always,target-package-updates=gotify1"``.
    This helper accepts either the raw string or an already parsed mapping and
    returns a dictionary with snake_case keys.
    """
    if not notify_value:
        return {}

    if isinstance(notify_value, dict):
        return {
            _normalize_notify_key(key): value for key, value in notify_value.items()
        }

    if not isinstance(notify_value, str):
        return {}

    parsed = {}
    normalized = notify_value.replace(";", ",")

    for chunk in normalized.split(","):
        item = chunk.strip()
        if not item:
            continue

        if "=" in item:
            key, value = item.split("=", 1)
            parsed[_normalize_notify_key(key)] = value.strip()
            continue

        parsed[_normalize_notify_key(item)] = True

    return parsed


def build_cluster_notifications_data(cluster_options, gotify_endpoints):
    """Build normalized cluster notification data from API responses."""

    notify_value = (
        cluster_options.get("notify") if isinstance(cluster_options, dict) else None
    )

    # 🔥 CASO: no hay configuración de notificaciones
    if not notify_value:
        return {
            "notify_raw": None,
            "notify": {},
            "gotify_endpoints": (
                gotify_endpoints if isinstance(gotify_endpoints, list) else []
            ),
            "package_updates": "not_configured",
            "replication": "not_configured",
            "fencing": "not_configured",
            "target_package_updates": None,
            "target_package_updates_type": None,
            "target_package_updates_server": None,
            "target_package_updates_origin": None,
            "notifications_configured": False,
        }

    # 🔁 Parsing normal
    notify_raw = parse_notify_string(notify_value)

    target_package_updates = notify_raw.get("target_package_updates")
    target_resolution = resolve_notification_target(
        target_package_updates, gotify_endpoints
    )

    return {
        "notify_raw": notify_value,
        "notify": notify_raw,
        "gotify_endpoints": (
            gotify_endpoints if isinstance(gotify_endpoints, list) else []
        ),
        "package_updates": notify_raw.get("package_updates"),
        "replication": notify_raw.get("replication"),
        "fencing": notify_raw.get("fencing"),
        "target_package_updates": target_resolution["target"],
        "target_package_updates_type": target_resolution["type"],
        "target_package_updates_server": target_resolution["server"],
        "target_package_updates_origin": target_resolution["origin"],
        "notifications_configured": True,
    }


def build_gotify_endpoint_map(endpoints):
    """Build a lookup table for Gotify endpoints by configured name."""
    endpoint_map = {}

    for endpoint in endpoints or []:
        if not isinstance(endpoint, dict):
            continue

        name = endpoint.get("name")
        if not name:
            continue

        endpoint_map[str(name)] = endpoint

    return endpoint_map


def resolve_notification_target(target_name, gotify_endpoints):
    """Resolve a notification target name against Gotify endpoints.

    Returns a dictionary with the original target name plus normalized metadata
    for ``type``, ``server`` and ``origin`` when the endpoint exists.
    """
    resolved = {
        "target": target_name,
        "type": None,
        "server": None,
        "origin": None,
    }

    if not target_name:
        return resolved

    endpoint = build_gotify_endpoint_map(gotify_endpoints).get(str(target_name))
    if not endpoint:
        return resolved

    resolved["type"] = endpoint.get("type") or "gotify"
    resolved["server"] = endpoint.get("server")
    resolved["origin"] = endpoint.get("origin")
    return resolved


def build_cluster_notifications_data(cluster_options, gotify_endpoints):
    """Build normalized cluster notification data from API responses."""
    notify_raw = {}
    if isinstance(cluster_options, dict):
        notify_raw = parse_notify_string(cluster_options.get("notify"))

    target_package_updates = notify_raw.get("target_package_updates")
    target_resolution = resolve_notification_target(
        target_package_updates, gotify_endpoints
    )

    return {
        "notify_raw": (
            cluster_options.get("notify") if isinstance(cluster_options, dict) else None
        ),
        "notify": notify_raw,
        "gotify_endpoints": (
            gotify_endpoints if isinstance(gotify_endpoints, list) else []
        ),
        "package_updates": notify_raw.get("package_updates"),
        "replication": notify_raw.get("replication"),
        "fencing": notify_raw.get("fencing"),
        "target_package_updates": target_resolution["target"],
        "target_package_updates_type": target_resolution["type"],
        "target_package_updates_server": target_resolution["server"],
        "target_package_updates_origin": target_resolution["origin"],
    }


def is_notification_enabled(value):
    """Return ``True`` when a notification mode should be treated as enabled."""
    if value is None:
        return False

    normalized = str(value).strip().lower()
    return normalized not in DISABLED_NOTIFICATION_VALUES
