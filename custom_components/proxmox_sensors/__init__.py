"""INIT for Proxmox Extended Sensors."""

from __future__ import annotations
import logging
import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.const import Platform
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr
import homeassistant.helpers.config_validation as cv

from .services import register_services
from .dashboard.preview import async_register_preview
from .dashboard.websocket import async_register_dashboard_websocket
from .dashboard.frontend import async_setup_dashboard_frontend
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
from .coordinator import (
    create_proxmox_coordinator, create_cluster_coordinator, create_pdm_coordinator,
    is_pbs_configuration_error, is_pbs_temporary_unavailable,
)
from .pbs_identity import async_remember_pbs_identity
from .pbs_devices import known_pbs_inventory, reconcile_pbs_devices
from .logic.pve_local_identity import (
    PveLocalIdentityError,
    pve_local_identity_context,
)
from .logic.pve_devices import (
    resolve_node_device_context,
    reconcile_legacy_node_devices,
    can_remove_pve_device,
)
from .logic.pdm import PDMIdentityError, pdm_identity_scope

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

ENTRY_VERSION = 3

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BUTTON,
    Platform.BINARY_SENSOR,
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register global diagnostics, including while individual entries are unloaded."""
    async_register_preview(hass)
    async_register_dashboard_websocket(hass)
    try:
        await async_setup_dashboard_frontend(hass)
    except Exception:
        _LOGGER.exception("Could not serve dashboard strategy; integration monitoring remains available")
    return True


def _entry_platform_type(config_entry: ConfigEntry) -> str:
    return (
        config_entry.data.get(CONF_PLATFORM_TYPE)
        or config_entry.data.get("server_type")
        or ""
    ).upper()


def _next_pbs_server_id(hass: HomeAssistant) -> str:
    max_index = 0
    for entry in hass.config_entries.async_entries(DOMAIN):
        if _entry_platform_type(entry) != "PBS":
            continue
        server_id = str(entry.data.get("server_id", "")).lower()
        if not server_id.startswith("pbs_"):
            continue
        suffix = server_id.removeprefix("pbs_")
        if suffix.isdigit():
            max_index = max(max_index, int(suffix))
    return f"pbs_{max_index + 1}"


def _ensure_pbs_server_id(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    if _entry_platform_type(config_entry) != "PBS":
        return False

    if config_entry.data.get("server_id"):
        return False

    ent_reg = er.async_get(hass)
    entries = er.async_entries_for_config_entry(ent_reg, config_entry.entry_id)
    if any(
        (entity.unique_id or "").lower().startswith("pbs_default_")
        for entity in entries
    ):
        server_id = "default"
    else:
        server_id = _next_pbs_server_id(hass)

    hass.config_entries.async_update_entry(
        config_entry, data={**config_entry.data, "server_id": server_id}
    )
    _LOGGER.info(
        "Persisted stable PBS server_id %s for legacy entry %s",
        server_id,
        config_entry.entry_id,
    )
    return True


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

    _ensure_pbs_server_id(hass, config_entry)
    server_id = (config_entry.data.get("server_id") or "default").lower()
    server_type = _entry_platform_type(config_entry).lower()

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

    if server_type != "pve":
        for entity in entries:
            old_unique_id = entity.unique_id
            if not old_unique_id:
                continue
            if old_unique_id.startswith(f"{prefix}_{server_id}_"):
                continue
            new_unique_id = f"{prefix}_{server_id}_{old_unique_id}".lower()
            ent_reg.async_update_entity(entity.entity_id, new_unique_id=new_unique_id)
            _LOGGER.debug("Updated unique_id: %s -> %s", old_unique_id, new_unique_id)


    if server_type == "pve":
        await _migrate_guest_ids_to_cluster_scope(hass, config_entry)

    hass.config_entries.async_update_entry(config_entry, version=ENTRY_VERSION)
    _LOGGER.info("Migration completed for entry %s", config_entry.entry_id)
    return True


async def _migrate_guest_ids_to_cluster_scope(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    return


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:

    if entry.data.get(CONF_PLATFORM_TYPE) == "PDM":
        return await _async_setup_pdm_entry(hass, entry)

    #  CLUSTER entry (autocreated)
    if entry.data.get(CONF_PLATFORM_TYPE) == "CLUSTER":
        return await _async_setup_cluster_entry(hass, entry)

    local_identity_context = None
    if entry.data.get(CONF_PLATFORM_TYPE) == "PVE":
        try:
            local_identity_context = pve_local_identity_context(
                entry, hass.config_entries.async_entries(DOMAIN)
            )
            try:
                local_identity_context = resolve_node_device_context(
                    local_identity_context, entry, dr.async_get(hass)
                )
            except PveLocalIdentityError:
                # Resolve first; only an ambiguity that passes the dedicated
                # casing-only preflight may mutate Entity Registry ownership.
                local_identity_context = reconcile_legacy_node_devices(
                    local_identity_context,
                    entry,
                    dr.async_get(hass),
                    er.async_get(hass),
                )
        except PveLocalIdentityError as err:
            raise ConfigEntryError(f"Invalid PVE local identity: {err}") from err

    #  Normal PVE / PBS entry
    if entry.version < ENTRY_VERSION:
        migrated = await async_migrate_entry(hass, entry)
        if not migrated:
            return False

    _ensure_pbs_server_id(hass, entry)

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
    if local_identity_context is not None:
        coordinator.pve_local_identity_context = local_identity_context

    known_pbs = False
    if data.get(CONF_PLATFORM_TYPE) == "PBS":
        known_pbs, known_stores = known_pbs_inventory(hass, entry)
        known_pbs = known_pbs or bool(known_stores)
        if coordinator.data is None:
            coordinator.data = {
                "server_type": "PBS",
                "pbs_datastores": {store: {} for store in known_stores},
                "_cleanup_confirmed": {"pbs_datastores": False},
            }

    if entry.data.get(CONF_PLATFORM_TYPE) == "PBS":
        try:
            pbs_instance_id = await client.get_pbs_instance_id(hass)
            hostname = entry.data.get("hostname") or await client.get_pbs_hostname(hass)

            new_data = entry.data
            if (
                pbs_instance_id
                and entry.data.get("pbs_instance_id") != pbs_instance_id
            ):
                new_data = {**new_data, "pbs_instance_id": pbs_instance_id}

            await async_remember_pbs_identity(
                hass, pbs_instance_id, entry.data.get("server_id")
            )

            if hostname:
                new_title = f"PBS: {hostname}"

                if entry.data.get("hostname") != hostname:
                    new_data = {**new_data, "hostname": hostname}

                if entry.title != new_title or new_data is not entry.data:
                    hass.config_entries.async_update_entry(
                        entry,
                        data=new_data,
                        title=new_title,
                    )
            elif new_data is not entry.data:
                hass.config_entries.async_update_entry(entry, data=new_data)

        except Exception as e:
            _LOGGER.error("PBS title update failed: %s", e)
    try:
        async with asyncio.timeout(20):
            await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        if data.get(CONF_PLATFORM_TYPE) == "PBS" and known_pbs and is_pbs_temporary_unavailable(err):
            _LOGGER.info("Known PBS %s is temporarily unavailable; loading existing entities", data[CONF_HOST])
        elif data.get(CONF_PLATFORM_TYPE) == "PBS" and is_pbs_configuration_error(err):
            raise ConfigEntryError(f"PBS authentication or permission error for {data[CONF_HOST]}") from err
        else:
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

    if data.get(CONF_PLATFORM_TYPE) == "PBS" and coordinator.last_update_success:
        reconcile_pbs_devices(hass, entry, coordinator.data.get("pbs_datastores", {}))

    register_services(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    hass.data[DOMAIN][entry.entry_id]["services_ready"] = True

    return True


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    if config_entry.data.get(CONF_PLATFORM_TYPE) == "PDM":
        return True
    return can_remove_pve_device(hass, config_entry, device_entry)


async def _async_setup_pdm_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a PDM config entry."""
    data = entry.data
    try:
        pdm_identity_scope(entry, hass.config_entries.async_entries(DOMAIN))
    except PDMIdentityError as err:
        raise ConfigEntryError(f"Invalid PDM identity: {err}") from err
    client = ProxmoxClient(
        host=data[CONF_HOST],
        user=data[CONF_USER],
        token_id=data.get(CONF_TOKEN_ID),
        token_secret=data.get(CONF_TOKEN_SECRET),
        server_type="PDM",
        verify_ssl=data.get(CONF_VERIFY_SSL, False),
    )
    coordinator = await create_pdm_coordinator(hass, entry, client)
    try:
        async with asyncio.timeout(30):
            await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        if is_pbs_configuration_error(err):
            raise ConfigEntryError(
                f"PDM authentication or permission error for {data[CONF_HOST]}"
            ) from err
        raise ConfigEntryNotReady(
            f"Unable to connect to Proxmox Datacenter Manager {data[CONF_HOST]}"
        ) from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "node": data.get(CONF_NODE, "PDM"),
        "server_type": "PDM",
        "features": data.get("features", {}),
    }
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
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

    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:

    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if runtime is not None:
        runtime["unloading"] = True

    try:
        if entry.data.get(CONF_PLATFORM_TYPE) in ("CLUSTER", "PDM"):
            unload_ok = await hass.config_entries.async_unload_platforms(
                entry, [Platform.SENSOR]
            )
        else:
            unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    finally:
        if runtime is not None:
            runtime.pop("unloading", None)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok
