"""Public, authenticated HA WebSocket command for read-only dashboard models."""

from .discovery import discover_inventory
from .selection import available_dashboard_types
from .layout import get_dashboard_layout
from .pve_resources import build_pve_dashboard_model
from .pbs_resources import build_pbs_dashboard_model
from .cluster_resources import build_cluster_dashboard_model
from .pdm_resources import build_pdm_dashboard_model

COMMAND = "proxmox_sensors/dashboard_models"
_REGISTERED = "proxmox_sensors.dashboard_websocket_registered"
_MAPPERS = {"pdm": build_pdm_dashboard_model,
            "pve": build_pve_dashboard_model, "pbs": build_pbs_dashboard_model,
            "cluster": build_cluster_dashboard_model}


def build_dashboard_response(hass):
    """Fresh snapshot per request, with no inventory or state payload exported."""
    inventory = discover_inventory(hass)
    available = available_dashboard_types(inventory)
    layouts = {kind: get_dashboard_layout(kind) for kind in available}
    return {"schema_version": 1, "available_dashboard_types": available,
            "layouts": layouts,
            "models": {kind: _MAPPERS[kind](inventory, layouts[kind]) for kind in available}}


def async_register_dashboard_websocket(hass):
    """Register globally; HA authenticates connections before dispatching commands."""
    from homeassistant.components import websocket_api
    from homeassistant.core import callback
    import voluptuous as vol

    if hass.data.get(_REGISTERED):
        return

    @websocket_api.websocket_command({vol.Required("type"): COMMAND})
    @callback
    def handle_models(hass, connection, msg):
        # No admin guard: authenticated non-admin dashboard users may read models.
        connection.send_result(msg["id"], build_dashboard_response(hass))

    websocket_api.async_register_command(hass, handle_models)
    hass.data[_REGISTERED] = True
