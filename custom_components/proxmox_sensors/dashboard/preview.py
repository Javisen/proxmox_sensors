"""Manual, read-only dashboard diagnostics using public HA service responses."""

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
import voluptuous as vol

from ..const import DOMAIN
from .discovery import discover_inventory
from .generator import generate_dashboard
from .layout import get_dashboard_layout
from .pve_resources import build_pve_dashboard_model
from .pbs_resources import build_pbs_dashboard_model
from .cluster_resources import build_cluster_dashboard_model
from .pdm_resources import build_pdm_dashboard_model
from .selection import available_dashboard_types

SERVICE_DASHBOARD_PREVIEW = "dashboard_preview"


def async_register_preview(hass: HomeAssistant) -> None:
    """Register once for the integration lifetime, independently of entry unloads."""
    if hass.services.has_service(DOMAIN, SERVICE_DASHBOARD_PREVIEW):
        return

    async def async_preview(call: ServiceCall) -> ServiceResponse:
        """Build a fresh snapshot without I/O, listeners, caches or registry writes."""
        inventory = discover_inventory(hass)
        available = available_dashboard_types(inventory)
        response = {
            **generate_dashboard(inventory),
            "available_dashboard_types": available,
            "dashboard_layouts": {kind: get_dashboard_layout(kind) for kind in available},
            "excluded": inventory["excluded"],
            "inventory": inventory,
        }
        if "pdm" in available:
            response["pdm_dashboard_model"] = build_pdm_dashboard_model(
                inventory, response["dashboard_layouts"]["pdm"])
        if "pve" in available:
            response["pve_dashboard_model"] = build_pve_dashboard_model(
                inventory, response["dashboard_layouts"]["pve"])
        if "pbs" in available:
            response["pbs_dashboard_model"] = build_pbs_dashboard_model(
                inventory, response["dashboard_layouts"]["pbs"])
        if "cluster" in available:
            response["cluster_dashboard_model"] = build_cluster_dashboard_model(
                inventory, response["dashboard_layouts"]["cluster"])
        return response

    hass.services.async_register(
        DOMAIN,
        SERVICE_DASHBOARD_PREVIEW,
        async_preview,
        schema=vol.Schema({}),
        supports_response=SupportsResponse.ONLY,
    )
