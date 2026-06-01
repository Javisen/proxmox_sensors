"""CONFIG FLOW for Proxmox Extended Sensors."""

from __future__ import annotations
import logging
import asyncio
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .api import (
    AuthenticationError,
    CannotConnect,
    PermissionError as ProxmoxPermissionError,
    ProxmoxClient,
)
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

_LOGGER = logging.getLogger(__name__)

SERVER_TYPES = {
    "PVE": "Proxmox VE",
    "PBS": "Proxmox Backup Server",
    "CLUSTER": "Proxmox Cluster",
}

PVE_MIN_ENDPOINTS = ["nodes"]
PVE_EXTRA_ENDPOINTS = ["cluster/resources"]
PBS_MIN_ENDPOINTS = ["admin/datastore"]
PBS_EXTRA_ENDPOINTS = ["status/datastore", "admin/tasks"]


class ProxmoxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1

    def __init__(self):
        self._config = {}
        self._use_token = False

    # ===== STEP 1 — SERVER TYPE + HOST ======================

    async def async_step_user(self, user_input=None) -> FlowResult:

        if user_input is not None:
            self._config.update(user_input)
            return await self.async_step_auth_method()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PLATFORM_TYPE, default="PVE"): vol.In(
                        SERVER_TYPES
                    ),
                }
            ),
        )

    # ===== STEP 2 — AUTH METHOD ==============================

    async def async_step_auth_method(self, user_input=None) -> FlowResult:

        server_type = self._config.get(CONF_PLATFORM_TYPE)

        # 🔥 SALTO DIRECTO PARA PBS
        if server_type == "PBS":
            self._use_token = True
            return await self.async_step_credentials_pbs()

        if user_input is not None:
            self._use_token = user_input.get("use_token", False)

            if server_type == "PVE":
                return await self.async_step_credentials_pve()
            elif server_type == "CLUSTER":
                return await self.async_step_credentials_cluster()

        return self.async_show_form(
            step_id="auth_method",
            data_schema=vol.Schema({vol.Required("use_token", default=False): bool}),
        )

    # ===== STEP 3a — CREDENTIALS PVE =========================

    async def async_step_credentials_pve(self, user_input=None) -> FlowResult:

        errors = {}
        schema_dict = {vol.Required(CONF_USER): str}

        if self._use_token:
            schema_dict[vol.Required(CONF_TOKEN_ID)] = str
            schema_dict[vol.Required(CONF_TOKEN_SECRET)] = str
        else:
            schema_dict[vol.Required(CONF_PASSWORD)] = str

        schema_dict[vol.Optional("auto_detect_node", default=True)] = bool
        schema_dict[vol.Optional("enable_lm_sensors", default=True)] = bool
        schema_dict[vol.Optional(CONF_VERIFY_SSL, default=False)] = bool

        if user_input is not None:
            self._config.update(user_input)
            client = self._build_client("PVE")
            try:
                validation = await self._validate_connection(
                    client, PVE_MIN_ENDPOINTS, PVE_EXTRA_ENDPOINTS
                )
            except AuthenticationError as err:
                _LOGGER.debug(
                    "PVE credential validation failed with %s: %s",
                    type(err).__name__,
                    err,
                )
                errors["base"] = "invalid_auth"
            except ProxmoxPermissionError as err:
                _LOGGER.debug(
                    "PVE credential validation failed with %s: %s",
                    type(err).__name__,
                    err,
                )
                errors["base"] = "insufficient_permissions"
            except CannotConnect as err:
                _LOGGER.debug(
                    "PVE credential validation failed with %s: %s",
                    type(err).__name__,
                    err,
                )
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected PVE credential validation error: %s", err)
                errors["base"] = "unknown"
            else:
                if not validation["has_minimum"]:
                    errors["base"] = "insufficient_permissions"
                else:
                    self._config["limited_permissions"] = not validation["has_all"]
                    return await self.async_step_select_node()

        return self.async_show_form(
            step_id="credentials_pve",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    # ===== STEP 3b — CREDENTIALS PBS =========================

    async def async_step_credentials_pbs(self, user_input=None) -> FlowResult:

        errors = {}
        schema_dict = {
            vol.Required(CONF_USER): str,
            vol.Required(CONF_TOKEN_ID): str,
            vol.Required(CONF_TOKEN_SECRET): str,
        }

        schema_dict[vol.Optional(CONF_VERIFY_SSL, default=False)] = bool

        if user_input is not None:
            self._config.update(user_input)
            client = self._build_client("PBS")
            try:
                validation = await self._validate_connection(
                    client, PBS_MIN_ENDPOINTS, PBS_EXTRA_ENDPOINTS
                )
            except AuthenticationError as err:
                _LOGGER.debug(
                    "PBS credential validation failed with %s: %s",
                    type(err).__name__,
                    err,
                )
                errors["base"] = "invalid_auth"
            except ProxmoxPermissionError as err:
                _LOGGER.debug(
                    "PBS credential validation failed with %s: %s",
                    type(err).__name__,
                    err,
                )
                errors["base"] = "insufficient_permissions"
            except CannotConnect as err:
                _LOGGER.debug(
                    "PBS credential validation failed with %s: %s",
                    type(err).__name__,
                    err,
                )
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected PBS credential validation error: %s", err)
                errors["base"] = "unknown"
            else:
                if not validation["has_minimum"]:
                    errors["base"] = "insufficient_permissions"
                else:
                    self._config["limited_permissions"] = not validation["has_all"]
                    return await self._finish()

        return self.async_show_form(
            step_id="credentials_pbs",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    # ===== STEP 3c — CREDENTIALS CLUSTER =====================

    async def async_step_credentials_cluster(self, user_input=None) -> FlowResult:

        errors = {}
        schema_dict = {vol.Required(CONF_USER): str}

        if self._use_token:
            schema_dict[vol.Required(CONF_TOKEN_ID)] = str
            schema_dict[vol.Required(CONF_TOKEN_SECRET)] = str
        else:
            schema_dict[vol.Required(CONF_PASSWORD)] = str

        schema_dict[vol.Optional(CONF_VERIFY_SSL, default=False)] = bool

        if user_input is not None:
            self._config.update(user_input)
            client = self._build_client("PVE")
            try:
                validation = await self._validate_connection(
                    client, PVE_MIN_ENDPOINTS, PVE_EXTRA_ENDPOINTS
                )
            except AuthenticationError as err:
                _LOGGER.debug(
                    "Cluster credential validation failed with %s: %s",
                    type(err).__name__,
                    err,
                )
                errors["base"] = "invalid_auth"
            except ProxmoxPermissionError as err:
                _LOGGER.debug(
                    "Cluster credential validation failed with %s: %s",
                    type(err).__name__,
                    err,
                )
                errors["base"] = "insufficient_permissions"
            except CannotConnect as err:
                _LOGGER.debug(
                    "Cluster credential validation failed with %s: %s",
                    type(err).__name__,
                    err,
                )
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception(
                    "Unexpected Cluster credential validation error: %s", err
                )
                errors["base"] = "unknown"
            else:
                if not validation["has_minimum"]:
                    errors["base"] = "insufficient_permissions"
                else:
                    self._config["limited_permissions"] = not validation["has_all"]
                    return await self._finish()

        return self.async_show_form(
            step_id="credentials_cluster",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    def _build_client(self, server_type: str) -> ProxmoxClient:
        """Create a client from the current config flow credentials."""
        return ProxmoxClient(
            host=self._config[CONF_HOST],
            user=self._config[CONF_USER],
            password=self._config.get(CONF_PASSWORD),
            token_id=self._config.get(CONF_TOKEN_ID),
            token_secret=self._config.get(CONF_TOKEN_SECRET),
            server_type=server_type,
            verify_ssl=self._config.get(CONF_VERIFY_SSL, False),
        )

    async def _validate_connection(
        self,
        client: ProxmoxClient,
        endpoints_min: list[str],
        endpoints_extra: list[str],
    ) -> dict[str, bool]:
        """Validate credentials and separate minimum from full permissions."""
        has_minimum = True
        has_all = True

        for endpoint in endpoints_min:
            try:
                response = await client.get(self.hass, endpoint, raise_errors=True)
                if response is None:
                    _LOGGER.debug(
                        "Minimum validation endpoint returned None: %s", endpoint
                    )
                    has_minimum = False
                    has_all = False
            except ProxmoxPermissionError as err:
                _LOGGER.debug(
                    "Minimum validation endpoint failed with %s: %s",
                    type(err).__name__,
                    err,
                )
                has_minimum = False
                has_all = False

        if not has_minimum:
            return {"has_minimum": False, "has_all": False}

        for endpoint in endpoints_extra:
            try:
                response = await client.get(self.hass, endpoint, raise_errors=True)
                if response is None:
                    _LOGGER.debug(
                        "Extra validation endpoint returned None: %s", endpoint
                    )
                    has_all = False
            except ProxmoxPermissionError as err:
                _LOGGER.debug(
                    "Extra validation endpoint failed with %s: %s",
                    type(err).__name__,
                    err,
                )
                has_all = False

        return {"has_minimum": has_minimum, "has_all": has_all}

    # ===== STEP 4 — SELECT NODE (PVE only) ===================

    async def async_step_select_node(self, user_input=None) -> FlowResult:

        client = ProxmoxClient(
            host=self._config[CONF_HOST],
            user=self._config[CONF_USER],
            password=self._config.get(CONF_PASSWORD),
            token_id=self._config.get(CONF_TOKEN_ID),
            token_secret=self._config.get(CONF_TOKEN_SECRET),
            server_type="PVE",
            verify_ssl=self._config.get(CONF_VERIFY_SSL, False),
        )

        try:
            resources = await client.get_cluster_resources(self.hass)
            nodes = [
                r for r in resources if isinstance(r, dict) and r.get("type") == "node"
            ]

            auto = self._config.get("auto_detect_node", True)

            if auto and nodes:
                host_ip = self._config.get(CONF_HOST)
                for n in nodes:
                    node_name = n.get("node")
                    try:
                        ip = await client.get_node_ip(self.hass, node_name)
                        if ip == host_ip:
                            self._config[CONF_NODE] = node_name
                            return await self.async_step_select_resources()
                    except Exception:
                        continue

                # Fallback: first node
                self._config[CONF_NODE] = nodes[0]["node"]
                return await self.async_step_select_resources()

            # Manual mode
            node_options = {}
            for n in nodes:
                node_name = n.get("node")
                ip = None
                try:
                    async with asyncio.timeout(5):
                        net = await client.get_node_network(self.hass, node_name)
                    for iface in net or []:
                        if iface.get("type") != "bridge":
                            continue
                        addr = iface.get("address")
                        if addr and not addr.startswith("127.") and ":" not in addr:
                            ip = addr
                            break
                    if not ip:
                        for iface in net or []:
                            addr = iface.get("address")
                            if addr and not addr.startswith("127.") and ":" not in addr:
                                ip = addr
                                break
                except Exception:
                    pass
                node_options[node_name] = f"{node_name} ({ip})" if ip else node_name

            if len(node_options) == 1:
                self._config[CONF_NODE] = list(node_options.keys())[0]
                return await self.async_step_select_resources()

            if user_input is not None:
                self._config[CONF_NODE] = user_input[CONF_NODE]
                return await self.async_step_select_resources()

            return self.async_show_form(
                step_id="select_node",
                data_schema=vol.Schema({vol.Required(CONF_NODE): vol.In(node_options)}),
            )

        except Exception as e:
            _LOGGER.error("Error fetching nodes: %s", e)
            return await self.async_step_select_resources()

    # ===== STEP 5 — SELECT RESOURCES (PVE only) ==============

    async def async_step_select_resources(self, user_input=None) -> FlowResult:

        if user_input is not None:
            self._config["selected_vms"] = user_input.get("vms", [])
            self._config["selected_cts"] = user_input.get("cts", [])
            self._config["selected_storage"] = user_input.get("storage", [])
            self._config["enable_physical_disks"] = user_input.get(
                "enable_physical_disks", True
            )
            self._config["enable_node_controls"] = user_input.get(
                "enable_node_controls", False
            )
            return await self._finish()

        client = ProxmoxClient(
            host=self._config[CONF_HOST],
            user=self._config[CONF_USER],
            password=self._config.get(CONF_PASSWORD),
            token_id=self._config.get(CONF_TOKEN_ID),
            token_secret=self._config.get(CONF_TOKEN_SECRET),
            server_type="PVE",
            verify_ssl=self._config.get(CONF_VERIFY_SSL, False),
        )

        node = self._config[CONF_NODE]

        try:
            vms_data = await client.get_vms(self.hass, node) or []
            cts_data = await client.get_containers(self.hass, node) or []
            storage_data = await client.get_storages(self.hass, node) or []

            vm_options = {
                str(v["vmid"]): f"{v['vmid']} ({v.get('name', 'VM')})"
                for v in vms_data
                if "vmid" in v
            }

            ct_options = {
                str(c["vmid"]): f"{c['vmid']} ({c.get('name', 'CT')})"
                for c in cts_data
                if "vmid" in c
            }

            st_options = {}
            for s in storage_data or []:
                st_name = s.get("storage")
                if not st_name:
                    continue
                is_shared = s.get("shared", 0) == 1
                storage_node = s.get("node")
                storage_path = s.get("path", "")
                total = s.get("total", 0) or 0
                used = s.get("used", 0) or 0

                if is_shared:
                    st_options[st_name] = st_name
                    continue
                if storage_node and storage_node != node:
                    continue
                if storage_path.startswith("/mnt") or storage_path.startswith("/media"):
                    if total == 0 and used == 0:
                        continue
                st_options[st_name] = st_name

            return self.async_show_form(
                step_id="select_resources",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            "vms", default=list(vm_options.keys())
                        ): cv.multi_select(vm_options),
                        vol.Optional(
                            "cts", default=list(ct_options.keys())
                        ): cv.multi_select(ct_options),
                        vol.Optional(
                            "storage", default=list(st_options.keys())
                        ): cv.multi_select(st_options),
                        vol.Optional("enable_physical_disks", default=True): bool,
                        vol.Optional("enable_node_controls", default=False): bool,
                    }
                ),
            )

        except Exception as e:
            _LOGGER.error("Error fetching resources: %s", e)
            return await self._finish()

    # ===== FINAL STEP ==========

    async def _finish(self):

        server_type = self._config.get(CONF_PLATFORM_TYPE, "PVE")

        if CONF_NODE not in self._config:
            self._config[CONF_NODE] = "Proxmox"

        title_name = None

        # ============= PBS =================
        if server_type == "PBS":
            entries = self.hass.config_entries.async_entries(DOMAIN)
            pbs_entries = [
                e for e in entries if e.data.get(CONF_PLATFORM_TYPE) == "PBS"
            ]
            self._config["server_id"] = f"pbs_{len(pbs_entries) + 1}"

            try:
                client = ProxmoxClient(
                    host=self._config[CONF_HOST],
                    user=self._config[CONF_USER],
                    password=self._config.get(CONF_PASSWORD),
                    token_id=self._config.get(CONF_TOKEN_ID),
                    token_secret=self._config.get(CONF_TOKEN_SECRET),
                    server_type="PBS",
                    verify_ssl=self._config.get(CONF_VERIFY_SSL, False),
                )

                hostname = await client.get_pbs_hostname(self.hass)

                if hostname:
                    self._config[CONF_NODE] = hostname
                else:
                    self._config[CONF_NODE] = "Proxmox"

            except Exception:
                self._config[CONF_NODE] = "Proxmox"

            title_name = self._config.get(CONF_NODE)

        # ============ CLUSTER =================
        elif server_type == "CLUSTER":
            self._config["server_id"] = f"cluster_{self._config[CONF_HOST]}"

            try:
                client = ProxmoxClient(
                    host=self._config[CONF_HOST],
                    user=self._config[CONF_USER],
                    password=self._config.get(CONF_PASSWORD),
                    token_id=self._config.get(CONF_TOKEN_ID),
                    token_secret=self._config.get(CONF_TOKEN_SECRET),
                    server_type="PVE",
                    verify_ssl=self._config.get(CONF_VERIFY_SSL, False),
                )

                status = await client.get_cluster_status(self.hass)
                cluster_name = status.get("name")

                if cluster_name:
                    self._config["cluster_name"] = cluster_name
                    title_name = cluster_name

            except Exception:
                pass

            if not title_name:
                title_name = self._config.get(CONF_HOST)

        # ========== PVE =================
        else:
            self._config["server_id"] = self._config[CONF_NODE]
            title_name = self._config.get(CONF_NODE)

        # ======== FINAL =================
        title = f"{server_type}: {title_name}"
        return self.async_create_entry(title=title, data=self._config)

    # ===== OPTIONS FLOW ======================================

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        from .options_flow import ProxmoxOptionsFlow

        return ProxmoxOptionsFlow()
