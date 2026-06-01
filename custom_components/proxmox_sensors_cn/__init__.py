"""INIT for Proxmox Extended Sensors."""

from __future__ import annotations
import logging
import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.const import Platform
from homeassistant.helpers import entity_registry as er

from .services import register_services
from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_USER,
    CONF_PASSWORD,
    CONF_TOKEN_ID,
    CONF_TOKEN_SECRET,
    CONF_NODE,
    CONF_PLATFORM_TYPE,
    CONF_VERIFY_SSL,
)

from .api import ProxmoxClient
from .coordinator import create_proxmox_coordinator, create_cluster_coordinator

_LOGGER = logging.getLogger(__name__)

ENTRY_VERSION = 2

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BUTTON,
    Platform.BINARY_SENSOR,
]


async def async_migrate_entry(hass, config_entry):
    """Migrate Proxmox entry to prefixed unique_id format."""

    if config_entry.version >= ENTRY_VERSION:
        return True

    _LOGGER.info(
        "Migrating Proxmox entry %s from version %s to %s",
        config_entry.entry_id,
        config_entry.version,
        ENTRY_VERSION,
    )

    ent_reg = er.async_get(hass)
    entries = er.async_entries_for_config_entry(ent_reg, config_entry.entry_id)

    server_id = (config_entry.data.get("server_id") or "default").lower()
    server_type = (config_entry.data.get("server_type") or "").lower()

    _LOGGER.debug("Migration server_type raw value: %s", server_type)

    if server_type == "pbs":
        prefix = "pbs"
    elif server_type == "pve":
        prefix = "pve"
    else:
        if any("datastore" in (e.unique_id or "") for e in entries):
            prefix = "pbs"
            _LOGGER.info("Legacy entry detected as PBS")
        else:
            prefix = "pve"
            _LOGGER.info("Legacy entry detected as PVE")

    for entity in entries:
        old_unique_id = entity.unique_id
        if not old_unique_id:
            continue
        if old_unique_id.startswith(f"{prefix}_{server_id}_"):
            continue
        new_unique_id = f"{prefix}_{server_id}_{old_unique_id}".lower()
        ent_reg.async_update_entity(entity.entity_id, new_unique_id=new_unique_id)
        _LOGGER.debug("Updated unique_id: %s -> %s", old_unique_id, new_unique_id)

    hass.config_entries.async_update_entry(config_entry, version=ENTRY_VERSION)
    _LOGGER.info("Migration completed for entry %s", config_entry.entry_id)
    return True


async def _async_manage_cluster_entry(
    hass: HomeAssistant,
    pve_entry: ConfigEntry,
    cluster_name: str,
    enable_cluster: bool,
):
    """Create or remove the CLUSTER config entry based on enable_cluster flag."""

    # Find existing cluster entries for this cluster name
    existing = [
        e
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.data.get(CONF_PLATFORM_TYPE) == "CLUSTER"
        and e.data.get("cluster_name") == cluster_name
    ]

    if not enable_cluster:
        # Remove cluster entry if it exists and was created by this PVE entry
        for e in existing:
            if e.data.get("parent_entry_id") == pve_entry.entry_id:
                _LOGGER.info("Removing CLUSTER entry for %s", cluster_name)
                await hass.config_entries.async_remove(e.entry_id)
        return

    # Already exists (created by any PVE entry for this cluster) → nothing to do
    if existing:
        _LOGGER.debug("CLUSTER entry for %s already exists, skipping", cluster_name)
        return

    # Create new CLUSTER entry reusing PVE credentials
    _LOGGER.info("Auto-creating CLUSTER entry for %s", cluster_name)

    data = pve_entry.data
    cluster_data = {
        CONF_HOST: data[CONF_HOST],
        CONF_USER: data[CONF_USER],
        CONF_PASSWORD: data.get(CONF_PASSWORD),
        CONF_TOKEN_ID: data.get(CONF_TOKEN_ID),
        CONF_TOKEN_SECRET: data.get(CONF_TOKEN_SECRET),
        CONF_VERIFY_SSL: data.get(CONF_VERIFY_SSL, False),
        CONF_PLATFORM_TYPE: "CLUSTER",
        CONF_NODE: data.get(CONF_NODE, ""),
        "cluster_name": cluster_name,
        "parent_entry_id": pve_entry.entry_id,
        "server_id": f"cluster_{cluster_name.lower()}",
    }


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:

    #  CLUSTER entry (autocreated)
    if entry.data.get(CONF_PLATFORM_TYPE) == "CLUSTER":
        return await _async_setup_cluster_entry(hass, entry)

    #  Normal PVE / PBS entry
    if entry.version < ENTRY_VERSION:
        migrated = await async_migrate_entry(hass, entry)
        if not migrated:
            return False

    data = entry.data

    client = ProxmoxClient(
        host=data[CONF_HOST],
        user=data[CONF_USER],
        password=data.get(CONF_PASSWORD),
        token_id=data.get(CONF_TOKEN_ID),
        token_secret=data.get(CONF_TOKEN_SECRET),
        server_type=data[CONF_PLATFORM_TYPE],
        verify_ssl=data.get(CONF_VERIFY_SSL, False),
    )

    coordinator = await create_proxmox_coordinator(hass, entry, client)

    if entry.data.get(CONF_PLATFORM_TYPE) == "PBS":
        try:
            hostname = entry.data.get("hostname") or await client.get_pbs_hostname(hass)

            if hostname:
                new_title = f"PBS: {hostname}"

                new_data = entry.data

                if entry.data.get("hostname") != hostname:
                    new_data = {**entry.data, "hostname": hostname}

                if entry.title != new_title or new_data is not entry.data:
                    hass.config_entries.async_update_entry(
                        entry,
                        data=new_data,
                        title=new_title,
                    )

        except Exception as e:
            _LOGGER.error("PBS title update failed: %s", e)
    try:
        async with asyncio.timeout(20):
            await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        raise ConfigEntryNotReady(
            f"Unable to connect to Proxmox {data[CONF_HOST]}"
        ) from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "node": data[CONF_NODE],
        "server_type": client._server_type,
        "features": data.get("features", {}),
    }

    register_services(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    #  Auto-manage CLUSTER entry after PVE loads
    if data.get(CONF_PLATFORM_TYPE) == "PVE":
        enable_cluster = entry.options.get(
            "enable_cluster", data.get("enable_cluster", True)
        )

        async def _safe_manage_cluster():
            """Create cluster entry without risking the PVE entry setup."""
            try:
                # Small delay to ensure PVE entry is fully registered first
                await asyncio.sleep(2)

                c_data = coordinator.data or {}
                cluster_info = c_data.get("cluster_status", {})
                cluster_name = cluster_info.get("name") if cluster_info else None

                if not cluster_name:
                    if enable_cluster:
                        _LOGGER.warning(
                            "enable_cluster=True but no cluster name in data for %s",
                            data.get(CONF_NODE),
                        )
                    return

                await _async_manage_cluster_entry(
                    hass, entry, cluster_name, enable_cluster
                )

            except Exception as err:
                # NEVER let cluster management fail the PVE entry
                _LOGGER.error(
                    "Error managing CLUSTER entry (PVE entry unaffected): %s", err
                )

        hass.async_create_task(_safe_manage_cluster())

    return True


async def _async_setup_cluster_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a CLUSTER-type config entry."""

    data = entry.data

    client = ProxmoxClient(
        host=data[CONF_HOST],
        user=data[CONF_USER],
        password=data.get(CONF_PASSWORD),
        token_id=data.get(CONF_TOKEN_ID),
        token_secret=data.get(CONF_TOKEN_SECRET),
        server_type="PVE",  # uses PVE API
        verify_ssl=data.get(CONF_VERIFY_SSL, False),
    )

    coordinator = await create_cluster_coordinator(hass, entry, client)

    try:
        async with asyncio.timeout(20):
            await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        raise ConfigEntryNotReady(
            f"Unable to connect to Proxmox cluster {data[CONF_HOST]}"
        ) from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "node": data.get(CONF_NODE, ""),
        "server_type": "CLUSTER",
        "features": {},
    }

    # Only sensors for CLUSTER entries
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:

    if entry.data.get(CONF_PLATFORM_TYPE) == "CLUSTER":
        unload_ok = await hass.config_entries.async_unload_platforms(
            entry, [Platform.SENSOR]
        )
    else:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok
