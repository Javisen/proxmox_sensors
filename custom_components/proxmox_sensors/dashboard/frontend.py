"""Serve the packaged strategy and logo through the public HTTP API."""

from pathlib import Path
import asyncio

RESOURCE_URL = "/proxmox_sensors/proxmox-dashboard.js"
LOGO_URL = "/proxmox_sensors/dashboard/logo_small.png"
LIGHT_LOGO_URL = "/proxmox_sensors/dashboard/logo_small2.png"
_REGISTERED = "proxmox_sensors.dashboard_static_registered"
_REGISTRATION_LOCK = "proxmox_sensors.dashboard_static_registration_lock"


async def async_setup_dashboard_frontend(hass):
    """Publish a static module, without registering or creating Lovelace storage."""
    from homeassistant.components.http import StaticPathConfig

    lock = hass.data.setdefault(_REGISTRATION_LOCK, asyncio.Lock())
    async with lock:
        if hass.data.get(_REGISTERED):
            return
        path = Path(__file__).resolve().parents[1] / "frontend" / "proxmox-dashboard.js"
        logo_path = Path(__file__).resolve().parent / "logo_small.png"
        light_logo_path = Path(__file__).resolve().parent / "logo_small2.png"
        await hass.http.async_register_static_paths([
            StaticPathConfig(RESOURCE_URL, str(path), False),
            StaticPathConfig(LOGO_URL, str(logo_path), False),
            StaticPathConfig(LIGHT_LOGO_URL, str(light_logo_path), False),
            # PBS's public URL aliases the same packaged logo used by PVE.
            StaticPathConfig("/proxmox_sensors/dashboard/logo_int.png", str(logo_path), False),
        ])
        hass.data[_REGISTERED] = True
