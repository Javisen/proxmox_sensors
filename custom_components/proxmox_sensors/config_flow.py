"""CONFIG FLOW for Proxmox Extended Sensors."""

from __future__ import annotations
import ipaddress
import logging
import asyncio
import re
from .logic.cluster_scope import (
    ACTIVE_SCOPE, CLUSTER_SCOPE_ID, CLUSTER_SCOPE_STATE, new_cluster_scope_id,
    cluster_entry_scope_status, entry_cluster_scope_id, recoverable_pve_scopes,
    recovery_registry_conflict,
)
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers import entity_registry as er, device_registry as dr

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
    PDM_IDENTITY_ID,
)
from .pbs_identity import (
    async_remember_pbs_identity,
    async_reserved_pbs_server_ids,
    async_server_id_for_pbs_identity,
    pbs_server_id_available_for_identity,
)
from .logic.pve_local_identity import (
    LOCAL_IDENTITY_VERSION,
    new_pve_identity_id,
)
from .const import PVE_IDENTITY_ID, PVE_LOCAL_IDENTITY_VERSION
from .logic.pdm import PDM_IDENTITY_VERSION, new_pdm_identity_id

_LOGGER = logging.getLogger(__name__)

SERVER_TYPES = {
    "PVE": "PVE",
    "PBS": "PBS",
    "CLUSTER": "CLUSTER",
    "PDM": "PDM",
}

PVE_MIN_ENDPOINTS = ["nodes"]
PVE_EXTRA_ENDPOINTS = ["cluster/resources"]
PBS_MIN_ENDPOINTS = ["admin/datastore"]
PBS_EXTRA_ENDPOINTS = ["version", "nodes/localhost/tasks"]
PDM_MIN_ENDPOINTS = ["resources/status", "remotes/remote"]
PDM_EXTRA_ENDPOINTS = [
    "version",
    "resources/list",
    "resources/subscription",
    "remotes/updates/summary",
]

_HOST_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?")


def _pbs_server_id_index(server_id: str | None) -> int | None:
    server_id = str(server_id or "").lower()
    if not server_id.startswith("pbs_"):
        return None
    suffix = server_id.removeprefix("pbs_")
    if suffix.isdigit():
        return int(suffix)
    return None


def _next_pbs_server_id(entries, reserved_server_ids=()):
    max_index = 0
    for entry in entries:
        platform_type = (
            entry.data.get(CONF_PLATFORM_TYPE) or entry.data.get("server_type") or ""
        ).upper()
        if platform_type != "PBS":
            continue
        index = _pbs_server_id_index(entry.data.get("server_id"))
        if index is not None:
            max_index = max(max_index, index)
    for server_id in reserved_server_ids:
        index = _pbs_server_id_index(server_id)
        if index is not None:
            max_index = max(max_index, index)
    return f"pbs_{max_index + 1}"


def _normalized_config_host(value) -> str:
    return str(value or "").strip().rstrip(".").lower()


def _config_host_error(value, platform) -> str | None:
    """Validate a new config-entry host against the clients' real support."""
    host = str(value or "").strip()
    platform = str(platform or "").upper()
    if not host or any(char.isspace() for char in host):
        return "invalid_host"
    if "://" in host or any(char in host for char in "/?#@"):
        return "invalid_host"

    address = host
    if host.startswith("["):
        if not host.endswith("]"):
            return "invalid_host"
        address = host[1:-1]
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError:
            return "invalid_host"
        if parsed.version != 6:
            return "invalid_host"
    else:
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError:
            parsed = None

    if parsed is not None:
        if parsed.version == 6 and platform not in ("PVE", "CLUSTER"):
            return "ipv6_not_supported"
        return None

    if ":" in host or set(host) <= set("0123456789."):
        return "invalid_host"

    hostname = host.rstrip(".")
    if not hostname or len(hostname) > 253:
        return "invalid_host"
    try:
        labels = [label.encode("idna").decode("ascii") for label in hostname.split(".")]
    except UnicodeError:
        return "invalid_host"
    if not all(_HOST_LABEL.fullmatch(label) for label in labels):
        return "invalid_host"
    return None


def _config_entry_platform(data) -> str:
    return str(data.get(CONF_PLATFORM_TYPE) or data.get("server_type") or "").upper()


def _config_entry_unique_id(data) -> str | None:
    platform = _config_entry_platform(data)
    host = _normalized_config_host(data.get(CONF_HOST))
    if not host:
        return None
    if platform == "PVE":
        node = str(data.get(CONF_NODE) or "").strip().lower()
        return f"pve:{host}:{node}" if node else None
    if platform == "PBS":
        instance_id = str(data.get("pbs_instance_id") or "").strip()
        return f"pbs:instance:{instance_id}" if instance_id else f"pbs:endpoint:{host}"
    if platform == "CLUSTER":
        return f"cluster:endpoint:{host}"
    if platform == "PDM":
        identity_id = str(data.get(PDM_IDENTITY_ID) or "").strip()
        return f"pdm:instance:{identity_id}" if identity_id else None
    return None


def _equivalent_config_entry(data, entries) -> bool:
    platform = _config_entry_platform(data)
    host = _normalized_config_host(data.get(CONF_HOST))
    node = str(data.get(CONF_NODE) or "").strip().lower()
    instance_id = str(data.get("pbs_instance_id") or "").strip()
    for entry in entries:
        existing = getattr(entry, "data", {}) or {}
        if _config_entry_platform(existing) != platform:
            continue
        existing_host = _normalized_config_host(existing.get(CONF_HOST))
        if platform == "PVE":
            existing_node = str(existing.get(CONF_NODE) or "").strip().lower()
            if host and node and host == existing_host and node == existing_node:
                return True
        elif platform == "PBS":
            existing_instance = str(existing.get("pbs_instance_id") or "").strip()
            if instance_id and existing_instance:
                if instance_id == existing_instance:
                    return True
            elif host and host == existing_host:
                return True
        elif platform == "CLUSTER" and host and host == existing_host:
            return True
        elif platform == "PDM" and host and host == existing_host:
            return True
    return False


class ProxmoxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 3

    def __init__(self):
        self._config = {}
        self._use_token = False

    async def _check_config_entry_identity(self):
        unique_id = _config_entry_unique_id(self._config)
        if unique_id is None:
            return None
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()
        if _equivalent_config_entry(
            self._config, self.hass.config_entries.async_entries(DOMAIN)
        ):
            return self.async_abort(reason="already_configured")
        return None

    # ===== STEP 1 — SERVER TYPE + HOST ======================

    async def async_step_user(self, user_input=None) -> FlowResult:

        errors = {}
        if user_input is not None:
            error = _config_host_error(
                user_input.get(CONF_HOST), user_input.get(CONF_PLATFORM_TYPE)
            )
            if error is None:
                user_input = {**user_input, CONF_HOST: user_input[CONF_HOST].strip()}
                self._config.update(user_input)
                return await self.async_step_auth_method()
            errors[CONF_HOST] = error

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PLATFORM_TYPE, default="PVE"): vol.In(
                        await self._server_type_labels()
                    ),
                }
            ),
            errors=errors,
        )

    async def _server_type_labels(self):
        language = (getattr(self, "context", None) or {}).get("language") or getattr(
            getattr(self.hass, "config", None), "language", "en"
        )
        translations = await async_get_translations(
            self.hass, language, "component", {DOMAIN}
        )
        english = translations if language == "en" else await async_get_translations(
            self.hass, "en", "component", {DOMAIN}
        )
        return {
            value: translations.get(key) or english.get(key) or value
            for value in SERVER_TYPES
            for key in (f"component.{DOMAIN}.selector.platform_type.options.{value.lower()}",)
        }

    # ===== STEP 2 — AUTH METHOD ==============================

    async def async_step_auth_method(self, user_input=None) -> FlowResult:

        server_type = self._config.get(CONF_PLATFORM_TYPE)

        # 🔥 SALTO DIRECTO PARA PBS
        if server_type in ("PBS", "PDM"):
            self._use_token = True
            return (
                await self.async_step_credentials_pbs()
                if server_type == "PBS"
                else await self.async_step_credentials_pdm()
            )

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
                    try:
                        pbs_instance_id = await client.get_pbs_instance_id(
                            self.hass, raise_errors=True
                        )
                        if pbs_instance_id:
                            self._config["pbs_instance_id"] = pbs_instance_id
                    except Exception as err:
                        _LOGGER.debug(
                            "PBS instance identity unavailable during setup: %s",
                            err,
                        )
                    return await self._finish()

        return self.async_show_form(
            step_id="credentials_pbs",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    async def async_step_credentials_pdm(self, user_input=None) -> FlowResult:
        errors = {}
        schema_dict = {
            vol.Required(CONF_USER): str,
            vol.Required(CONF_TOKEN_ID): str,
            vol.Required(CONF_TOKEN_SECRET): str,
            vol.Optional(CONF_VERIFY_SSL, default=False): bool,
        }
        if user_input is not None:
            self._config.update(user_input)
            client = self._build_client("PDM")
            try:
                validation = await self._validate_connection(
                    client, PDM_MIN_ENDPOINTS, PDM_EXTRA_ENDPOINTS
                )
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except ProxmoxPermissionError:
                errors["base"] = "insufficient_permissions"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected PDM credential validation error")
                errors["base"] = "unknown"
            else:
                if not validation["has_minimum"]:
                    errors["base"] = "insufficient_permissions"
                else:
                    self._config["limited_permissions"] = not validation["has_all"]
                    self._config["pdm_identity_version"] = PDM_IDENTITY_VERSION
                    self._config[PDM_IDENTITY_ID] = new_pdm_identity_id(
                        self.hass.config_entries.async_entries(DOMAIN)
                    )
                    return await self._finish()
        return self.async_show_form(
            step_id="credentials_pdm",
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

                if response is None or (
                    endpoint == "nodes" and isinstance(response, list) and not response
                ):
                    _LOGGER.debug(
                        "Minimum validation endpoint returned no visible nodes: %s",
                        endpoint,
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
                        "Extra validation endpoint returned None: %s",
                        endpoint,
                    )
                    has_all = False

            except (ProxmoxPermissionError, CannotConnect) as err:
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

            if not nodes:
                return self.async_abort(reason="no_nodes_visible")

            auto = self._config.get("auto_detect_node", True)

            if auto:
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
            self._config["enable_lm_sensors"] = user_input.get(
                "enable_lm_sensors", True
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
                        vol.Optional("vms", default=[]): cv.multi_select(vm_options),
                        vol.Optional("cts", default=[]): cv.multi_select(ct_options),
                        vol.Optional("storage", default=[]): cv.multi_select(
                            st_options
                        ),
                        vol.Optional("enable_physical_disks", default=True): bool,
                        vol.Optional("enable_lm_sensors", default=True): bool,
                        vol.Optional("enable_node_controls", default=False): bool,
                    }
                ),
            )

        except Exception as e:
            _LOGGER.error("Error fetching resources: %s", e)
            return await self._finish()

    # ===== FINAL STEP ==========

    def _recovery_candidates(self):
        entries = tuple(self.hass.config_entries.async_entries(DOMAIN))
        groups = recoverable_pve_scopes(entries)
        if not groups:
            return {}
        try:
            rows = tuple(er.async_get(self.hass).entities.values())
            device_registry = dr.async_get(self.hass)
            devices = tuple(device_registry.devices)
        except Exception:
            _LOGGER.exception("Unable to inspect registries for CLUSTER recovery")
            return {}
        return {
            scope: members for scope, members in groups.items()
            if not recovery_registry_conflict(scope, members, rows, devices)
        }

    async def async_step_cluster_association(self, user_input=None):
        return self.async_show_menu(
            step_id="cluster_association",
            menu_options=["new_cluster_association", "recover_cluster_scope"],
        )

    async def async_step_new_cluster_association(self, user_input=None):
        self._cluster_association_choice = "new"
        return await self._finish()

    async def async_step_recover_cluster_scope(self, user_input=None):
        candidates = self._recovery_candidates()
        errors = {}
        if user_input is not None:
            scope = user_input.get("scope")
            offered = getattr(self, "_offered_recovery", {})
            if scope in candidates and candidates[scope] == offered.get(scope):
                self._selected_recovery = (scope, candidates[scope])
                return await self.async_step_confirm_cluster_recovery()
            errors["base"] = "recovery_unavailable"
        self._offered_recovery = dict(candidates)
        entries = {entry.entry_id: entry for entry in self.hass.config_entries.async_entries(DOMAIN)}
        choices = {
            scope: ", ".join(
                f"{entries[entry_id].title} ({entries[entry_id].data.get(CONF_HOST, '?')}; {entry_id})"
                for entry_id in members
            )
            for scope, members in candidates.items()
        }
        return self.async_show_form(
            step_id="recover_cluster_scope",
            data_schema=vol.Schema({vol.Required("scope"): vol.In(choices)}),
            errors=errors,
        )

    async def async_step_confirm_cluster_recovery(self, user_input=None):
        selection = getattr(self, "_selected_recovery", None)
        if selection is None:
            return await self.async_step_recover_cluster_scope()
        scope, members = selection
        if user_input is not None:
            if not user_input.get("confirm", False):
                self._selected_recovery = None
                return await self.async_step_cluster_association()
            if self._recovery_candidates().get(scope) != members:
                self._selected_recovery = None
                return await self.async_step_recover_cluster_scope({"scope": scope})
            self._cluster_association_choice = "recover"
            return await self._finish()
        entries = {entry.entry_id: entry for entry in self.hass.config_entries.async_entries(DOMAIN)}
        return self.async_show_form(
            step_id="confirm_cluster_recovery",
            data_schema=vol.Schema({vol.Required("confirm", default=False): bool}),
            description_placeholders={
                "pves": ", ".join(f"{entries[entry_id].title} ({entry_id})" for entry_id in members),
            },
        )

    def _eligible_clusters(self):
        clusters = [entry for entry in self.hass.config_entries.async_entries(DOMAIN)
                    if entry.data.get(CONF_PLATFORM_TYPE) == "CLUSTER"]
        return {
            entry.entry_id: entry for entry in clusters
            if cluster_entry_scope_status(entry) == ACTIVE_SCOPE
            and sum(entry_cluster_scope_id(other) == entry_cluster_scope_id(entry)
                    for other in clusters) == 1
        }

    async def async_step_pve_membership(self, user_input=None):
        return self.async_show_menu(
            step_id="pve_membership",
            menu_options=(["join_cluster", "independent"]
                          if self._eligible_clusters() else ["independent"]),
        )

    async def async_step_join_cluster(self, user_input=None):
        clusters = self._eligible_clusters()
        errors = {}
        if user_input is not None:
            target_id = user_input.get("cluster")
            target = clusters.get(target_id)
            expected = getattr(self, "_offered_clusters", {}).get(target_id)
            if target is not None and expected == entry_cluster_scope_id(target):
                self._membership_choice = target_id
                self._membership_scope = expected
                return await self._finish()
            errors["base"] = "cluster_unavailable"
        self._offered_clusters = {
            entry_id: entry_cluster_scope_id(entry) for entry_id, entry in clusters.items()
        }
        choices = {
            entry.entry_id: f"{index}. {entry.title} ({entry.data.get(CONF_HOST, '')})"
            for index, entry in enumerate(sorted(clusters.values(), key=lambda entry: entry.entry_id), 1)
        }
        return self.async_show_form(
            step_id="join_cluster",
            data_schema=vol.Schema({vol.Required("cluster"): vol.In(choices)}),
            errors=errors,
        )

    async def async_step_independent(self, user_input=None):
        self._membership_choice = "independent"
        return await self._finish()

    async def _finish(self):

        server_type = self._config.get(CONF_PLATFORM_TYPE, "PVE")

        if CONF_NODE not in self._config:
            self._config[CONF_NODE] = "Proxmox"

        duplicate = await self._check_config_entry_identity()
        if duplicate is not None:
            return duplicate

        title_name = None

        # ============= PBS =================
        if server_type == "PBS":
            entries = self.hass.config_entries.async_entries(DOMAIN)
            reserved_server_ids = await async_reserved_pbs_server_ids(self.hass)
            pbs_instance_id = self._config.get("pbs_instance_id")
            restored_server_id = await async_server_id_for_pbs_identity(
                self.hass, pbs_instance_id
            )
            if restored_server_id and pbs_server_id_available_for_identity(
                self.hass, restored_server_id, pbs_instance_id
            ):
                self._config["server_id"] = restored_server_id
            else:
                if restored_server_id:
                    _LOGGER.warning(
                        "PBS identity %s maps to active server_id %s; assigning a new id",
                        pbs_instance_id,
                        restored_server_id,
                    )
                self._config["server_id"] = _next_pbs_server_id(
                    entries, reserved_server_ids
                )

            await async_remember_pbs_identity(
                self.hass, pbs_instance_id, self._config["server_id"]
            )

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
            candidates = self._recovery_candidates()
            choice = getattr(self, "_cluster_association_choice", None)
            if candidates and choice is None:
                return await self.async_step_cluster_association()
            if choice == "recover":
                selection = getattr(self, "_selected_recovery", None)
                if selection is None or self._recovery_candidates().get(selection[0]) != selection[1]:
                    self._cluster_association_choice = None
                    self._selected_recovery = None
                    return await self.async_step_recover_cluster_scope({"scope": None})
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

        # ============ PDM =================
        elif server_type == "PDM":
            self._config[CONF_NODE] = "PDM"
            title_name = self._config.get(CONF_HOST)

        # ========== PVE =================
        else:
            choice = getattr(self, "_membership_choice", None)
            if choice is None:
                return await self.async_step_pve_membership()
            if choice == "independent":
                if CLUSTER_SCOPE_ID not in self._config:
                    self._config[CLUSTER_SCOPE_ID] = new_cluster_scope_id()
            else:
                target = self._eligible_clusters().get(choice)
                if target is None or entry_cluster_scope_id(target) != self._membership_scope:
                    return await self.async_step_join_cluster({"cluster": choice})
                self._config[CLUSTER_SCOPE_ID] = self._membership_scope
            self._config["server_id"] = self._config[CONF_NODE]
            self._config[CLUSTER_SCOPE_STATE] = ACTIVE_SCOPE
            if PVE_LOCAL_IDENTITY_VERSION not in self._config:
                self._config[PVE_LOCAL_IDENTITY_VERSION] = LOCAL_IDENTITY_VERSION
                self._config[PVE_IDENTITY_ID] = new_pve_identity_id(
                    self.hass.config_entries.async_entries(DOMAIN)
                )
            title_name = self._config.get(CONF_NODE)

        # ======== FINAL =================
        duplicate = await self._check_config_entry_identity()
        if duplicate is not None:
            return duplicate
        if server_type == "CLUSTER":
            if choice == "recover":
                selection = getattr(self, "_selected_recovery", None)
                if selection is None or self._recovery_candidates().get(selection[0]) != selection[1]:
                    self._cluster_association_choice = None
                    self._selected_recovery = None
                    return await self.async_step_recover_cluster_scope({"scope": None})
                self._config[CLUSTER_SCOPE_ID] = selection[0]
            elif CLUSTER_SCOPE_ID not in self._config:
                reserved = {
                    entry_cluster_scope_id(entry)
                    for entry in self.hass.config_entries.async_entries(DOMAIN)
                }
                for _ in range(16):
                    scope = new_cluster_scope_id()
                    if scope not in reserved:
                        self._config[CLUSTER_SCOPE_ID] = scope
                        break
                else:
                    return self.async_abort(reason="scope_unavailable")
            self._config[CLUSTER_SCOPE_STATE] = ACTIVE_SCOPE
        title = f"{server_type}: {title_name}"
        return self.async_create_entry(title=title, data=self._config)

    # ===== OPTIONS FLOW ======================================

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        from .options_flow import ProxmoxOptionsFlow

        return ProxmoxOptionsFlow()
