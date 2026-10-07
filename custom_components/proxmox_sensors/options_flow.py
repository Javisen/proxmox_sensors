# =========OPTIONS FLOW — PROXMOX EXTENDED SENSORS===========

from __future__ import annotations
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import selector
from homeassistant.helpers.translation import async_get_translations

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
from .logic.guest_selection import (
    _entry_cluster_id, get_entry_guest_selection, get_effective_guest_selections,
    guest_selection_entries, selection_guest_ids, plan_guest_selection,
)
from .logic.cluster_scope import (
    CLUSTER_SCOPE_ID, CLUSTER_SCOPE_STATE, PENDING_SCOPE, cluster_association_preflight,
    cluster_scope_status, entry_cluster_scope_id, new_cluster_scope_id,
)
from .logic.cluster_scope import associated_cluster_for_pve

_LOGGER = logging.getLogger(__name__)


class GuestSelectionError(ValueError):
    """An expected, user-actionable guest selection validation failure."""

    def __init__(self, translation_key: str):
        self.translation_key = translation_key
        super().__init__(translation_key)


class ProxmoxOptionsFlow(config_entries.OptionsFlow):

    async def _scope_labels(self):
        language = (getattr(self, "context", None) or {}).get("language") or getattr(
            getattr(self.hass, "config", None), "language", "en"
        )
        translations = await async_get_translations(
            self.hass, language, "selector", {DOMAIN}
        )
        english = translations if language == "en" else await async_get_translations(
            self.hass, "en", "selector", {DOMAIN}
        )
        prefix = f"component.{DOMAIN}.selector.cluster_scope_action.options."
        return {
            key: translations.get(prefix + key) or english.get(prefix + key) or key
            for key in ("keep", "independent")
        }


    def _scope_validator(self):
        return selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=list(self._scope_choices()),
                translation_key="cluster_scope_action",
            )
        )

    def _scope_choices(self):
        """Return the normal PVE Options Flow cluster actions."""
        entries = list(self.hass.config_entries.async_entries(DOMAIN))
        cluster = associated_cluster_for_pve(self.config_entry, entries)
        if cluster is None:
            return {"keep": self._localized_scope_labels["keep"]}
        return {
            "keep": self._localized_scope_labels["keep"],
            "independent": self._localized_scope_labels["independent"],
        }

    def _cluster_association_choices(self):
        entries = list(self.hass.config_entries.async_entries(DOMAIN))
        choices = {"keep": getattr(self, "_localized_scope_labels", {}).get("keep", "keep")}
        for candidate in entries:
            result = cluster_association_preflight(
                self.config_entry, candidate, entries
            )
            if not result.allowed:
                continue
            title = getattr(candidate, "title", candidate.entry_id)
            host = candidate.data.get(CONF_HOST, "?")
            cluster_name = candidate.data.get("cluster_name", "?")
            choices[f"associate:{candidate.entry_id}"] = (
                f"{title} — {host} ({cluster_name})"
            )
        return choices

    def _cluster_association_validator(self):
        return getattr(vol, "In", lambda choices: str)(
            self._cluster_association_choices()
        )

    def _cluster_association_target(self):
        target_id = getattr(self, "_pending_cluster_association_id", None)
        return next(
            (
                candidate
                for candidate in self.hass.config_entries.async_entries(DOMAIN)
                if candidate.entry_id == target_id
            ),
            None,
        )

    async def async_step_cluster_association_confirm(self, user_input=None):
        target = self._cluster_association_target()
        entries = list(self.hass.config_entries.async_entries(DOMAIN))
        result = (
            cluster_association_preflight(self.config_entry, target, entries)
            if target is not None
            else None
        )
        if user_input is not None:
            if not user_input.get("confirm", False):
                return self.async_create_entry(title="", data={})
            if result is None or not result.allowed:
                return self.async_show_form(
                    step_id="cluster_association_confirm",
                    data_schema=vol.Schema({vol.Required("confirm", default=False): bool}),
                    errors={"base": result.reason if result else "association_target_not_available"},
                )
            data = dict(target.data)
            data[CLUSTER_SCOPE_ID] = entry_cluster_scope_id(self.config_entry)
            data[CLUSTER_SCOPE_STATE] = cluster_scope_status(self.config_entry)
            self.hass.config_entries.async_update_entry(target, data=data)
            return self.async_create_entry(title="", data={})
        if result is None or not result.allowed:
            return self.async_show_form(
                step_id="cluster_association_confirm",
                data_schema=vol.Schema({vol.Required("confirm", default=False): bool}),
                errors={"base": result.reason if result else "association_target_not_available"},
            )
        source_title = getattr(self.config_entry, "title", self.config_entry.entry_id)
        target_title = getattr(target, "title", target.entry_id)
        scope = entry_cluster_scope_id(self.config_entry)
        return self.async_show_form(
            step_id="cluster_association_confirm",
            data_schema=vol.Schema({vol.Required("confirm", default=False): bool}),
            description_placeholders={
                "source": source_title,
                "target": target_title,
                "scope": f"{scope[:8]}…{scope[-4:]}",
            },
        )

    async def async_step_scope_confirm(self, user_input=None):
        """Persist an explicitly confirmed scope change and nothing else."""
        if user_input is not None:
            if not user_input.get("confirm", False):
                return self.async_create_entry(title="", data={})
            action = self._pending_scope_action
            data = dict(self.config_entry.data)
            if action == "independent":
                data[CLUSTER_SCOPE_ID] = new_cluster_scope_id()
            else:
                target_id = action.removeprefix("join:")
                target = self.hass.config_entries.async_get_entry(target_id)
                scope_of = globals().get("entry_cluster_scope_id", lambda value: None)
                scope = scope_of(target) if target else None
                if scope is None:
                    return self.async_create_entry(title="", data={})
                data[CLUSTER_SCOPE_ID] = scope
            # Existing entries require the later, opt-in assisted migration.
            data[CLUSTER_SCOPE_STATE] = PENDING_SCOPE
            self.hass.config_entries.async_update_entry(self.config_entry, data=data)
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})
        return self.async_show_form(
            step_id="scope_confirm",
            data_schema=vol.Schema({vol.Required("confirm", default=False): bool}),
        )

    async def async_step_init(self, user_input=None) -> FlowResult:

        conf = self.config_entry.data
        server_type = conf.get(CONF_PLATFORM_TYPE, "PVE")

        if server_type in ("CLUSTER", "PDM"):
            return await self.async_step_cluster(user_input)
        elif server_type == "PBS":
            return await self.async_step_pbs(user_input)
        else:
            return await self.async_step_pve(user_input)

    # ===== CLUSTER OPTIONS ===================================

    async def async_step_cluster(self, user_input=None) -> FlowResult:

        conf = self.config_entry.data

        if user_input is not None:
            new_data = dict(conf)
            new_data[CONF_VERIFY_SSL] = user_input.get(CONF_VERIFY_SSL, False)
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data, options={}
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_VERIFY_SSL, default=conf.get(CONF_VERIFY_SSL, False)
                    ): bool,
                }
            ),
        )

    # ===== PBS OPTIONS =======================================

    async def async_step_pbs(self, user_input=None) -> FlowResult:

        conf = self.config_entry.data

        if user_input is not None:
            new_data = dict(conf)
            new_data[CONF_VERIFY_SSL] = user_input.get(CONF_VERIFY_SSL, False)
            new_data["enable_pbs_node_controls"] = user_input.get(
                "enable_pbs_node_controls", True
            )
            new_data["wol_mac"] = user_input.get("wol_mac", "")
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=new_data, options={}
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_VERIFY_SSL, default=conf.get(CONF_VERIFY_SSL, False)
                    ): bool,
                    vol.Optional(
                        "enable_pbs_node_controls",
                        default=conf.get("enable_pbs_node_controls", True),
                    ): bool,
                    vol.Optional("wol_mac", default=conf.get("wol_mac", "")): str,
                }
            ),
        )

    async def _guest_inventory(self, client):
        """Validate cluster inventory against fresh lists from every visible node."""
        resources = await client.get(self.hass, "cluster/resources", raise_errors=True)
        if not isinstance(resources, list) or any(not isinstance(r, dict) for r in resources):
            raise GuestSelectionError("guest_inventory_changed")
        nodes = {r.get("node") for r in resources if r.get("type") == "node"}
        if not nodes or any(not isinstance(n, str) or not n for n in nodes):
            raise GuestSelectionError("guest_inventory_changed")
        entries = guest_selection_entries(self.hass, self.config_entry)
        expected = {e.data.get(CONF_NODE) for e in entries}
        runtime = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id, {})
        coordinator = runtime.get("coordinator")
        previous = getattr(coordinator, "data", None) or {}
        expected.update(previous.get("cluster_nodes", []))
        if not expected <= nodes:
            raise GuestSelectionError("guest_inventory_changed")
        if len(nodes) > 1 and not _entry_cluster_id(self.hass, self.config_entry):
            raise GuestSelectionError("guest_discovery_unavailable")
        # Do not silently omit a configured sibling with unresolved membership.
        for candidate in self.hass.config_entries.async_entries(DOMAIN):
            if (candidate.data.get(CONF_PLATFORM_TYPE) == "PVE"
                    and candidate.data.get(CONF_NODE) in nodes
                    and not _entry_cluster_id(self.hass, candidate)
                    and candidate.entry_id != self.config_entry.entry_id):
                raise GuestSelectionError("guest_discovery_unavailable")
        choices = {"vms": {}, "cts": {}}
        locations = {"vms": {}, "cts": {}}
        for node in sorted(nodes):
            for field, resource_type, endpoint in (("vms", "qemu", "qemu"), ("cts", "lxc", "lxc")):
                guests = await client.get(self.hass, f"nodes/{node}/{endpoint}", raise_errors=True)
                if not isinstance(guests, list) or any(
                    not isinstance(g, dict) or not str(g.get("vmid", "")).isdecimal() for g in guests
                ):
                    raise GuestSelectionError("guest_discovery_unavailable")
                ids = {str(g["vmid"]) for g in guests}
                inventory_ids = {str(r.get("vmid")) for r in resources
                                 if r.get("type") == resource_type and r.get("node") == node}
                if ids != inventory_ids or ids & choices[field].keys():
                    raise GuestSelectionError("guest_inventory_changed")
                choices[field].update({str(g["vmid"]): f"{g['vmid']} ({g.get('name', resource_type)}) — {node}"
                                       for g in guests})
                locations[field].update({vmid: node for vmid in ids})
        if any(r.get("type") in ("qemu", "lxc") and r.get("node") not in nodes for r in resources):
            raise GuestSelectionError("guest_inventory_changed")
        return {**choices, "locations": locations}

    def _guest_selection_snapshot(self):
        return {e.entry_id: (get_entry_guest_selection(e, "selected_vms", []),
                             get_entry_guest_selection(e, "selected_cts", []))
                for e in guest_selection_entries(self.hass, self.config_entry)}

    def _previous_guest_ids(self, field):
        ids = set()
        resource_type = "qemu" if field == "vms" else "lxc"
        for entry in guest_selection_entries(self.hass, self.config_entry):
            runtime = self.hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
            data = getattr(runtime.get("coordinator"), "data", None) or {}
            guests = list((data.get(field) or {}).values())
            guests.extend(r for r in data.get("cluster_resources", [])
                          if isinstance(r, dict) and r.get("type") == resource_type)
            ids.update(str(g["vmid"]) for g in guests
                       if isinstance(g, dict) and str(g.get("vmid", "")).isdecimal())
        return ids

    # ===== PVE OPTIONS =======================================

    async def async_step_pve(self, user_input=None) -> FlowResult:

        self._localized_scope_labels = await self._scope_labels()

        conf = self.config_entry.data
        options = self.config_entry.options or {}
        wol_mac_map = options.get("wol_macs", {})

        current_node = conf[CONF_NODE]

        # Get cluster nodes
        cluster_nodes = [conf.get(CONF_NODE, "")]
        try:
            entry_data = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
            if entry_data and entry_data.get("coordinator"):
                coordinator_data = entry_data["coordinator"].data or {}
                cluster_nodes = coordinator_data.get("cluster_nodes", cluster_nodes)
        except Exception:
            pass

        self._cluster_nodes = cluster_nodes

        if user_input is not None:
            action = user_input.get("cluster_scope_action", "keep")
            if action == "independent" and action in self._scope_choices():
                self._pending_scope_action = action
                return await self.async_step_scope_confirm()
            plans = {}
            changed_fields = [field for field in ("vms", "cts") if field in user_input
                              and set(user_input[field]) != set(getattr(self, "_guest_defaults", {}).get(field, []))]
            if changed_fields:
                try:
                    if not getattr(self, "_guest_choices", None):
                        raise GuestSelectionError("guest_discovery_unavailable")
                    if self._guest_snapshot != self._guest_selection_snapshot():
                        raise GuestSelectionError("guest_selection_changed")
                    fresh = await self._guest_inventory(self._guest_client)
                    if self._guest_snapshot != self._guest_selection_snapshot():
                        raise GuestSelectionError("guest_selection_changed")
                    if any(set(fresh[field]) != set(self._guest_choices[field]) for field in ("vms", "cts")):
                        raise GuestSelectionError("guest_inventory_changed")
                    if fresh["locations"] != self._guest_choices["locations"]:
                        raise GuestSelectionError("guest_inventory_changed")
                    entries = guest_selection_entries(self.hass, self.config_entry)
                    effective = get_effective_guest_selections(
                        self.hass, self.config_entry, _entry_cluster_id(self.hass, self.config_entry),
                        get_entry_guest_selection(self.config_entry, "selected_vms", []),
                        get_entry_guest_selection(self.config_entry, "selected_cts", []),
                    )
                    for field in changed_fields:
                        chosen = selection_guest_ids(user_input[field])
                        visible = set(self._guest_visible[field])
                        if chosen is None or not chosen <= visible:
                            raise GuestSelectionError("invalid_guest_selection")
                        selected = selection_guest_ids(effective[0 if field == "vms" else 1])
                        if selected is None:
                            selected = set(fresh[field])
                        # Apply the local form as a patch to the cluster selection.
                        cluster_chosen = ((selected & set(fresh[field])) - visible) | chosen
                        plans["selected_" + field] = plan_guest_selection(
                            entries, "selected_" + field, cluster_chosen, fresh[field], True,
                            self._guest_previous[field] | self._previous_guest_ids(field),
                        )
                except GuestSelectionError as err:
                    _LOGGER.warning("Guest selection not saved: %s", err.translation_key)
                    return self.async_show_form(step_id="init", data_schema=self._pve_schema,
                                                errors={"base": err.translation_key})
                except Exception:
                    _LOGGER.exception("Unexpected error while saving guest selections")
                    return self.async_show_form(step_id="init", data_schema=self._pve_schema,
                                                errors={"base": "guest_selection_failed"})

            # Discovery awaited above; preserve unrelated options changed meanwhile.
            new_data = dict(self.config_entry.data)
            options = self.config_entry.options or {}
            wol_mac_map = options.get("wol_macs", {})
            for key in (CONF_VERIFY_SSL, "enable_lm_sensors", "enable_physical_disks",
                        "enable_smart_monitoring", "enable_node_controls",
                        "enable_guest_agent_metrics"):
                if key in user_input:
                    new_data[key] = user_input[key]
            if "storage" in user_input:
                new_data["selected_storage"] = user_input["storage"]
            new_options = dict(options)
            wol_macs = dict(wol_mac_map)
            if "wol_mac" in user_input:
                value = user_input["wol_mac"]
                if value:
                    wol_macs[current_node] = value
                else:
                    wol_macs.pop(current_node, None)
            if wol_macs or "wol_macs" in options:
                new_options["wol_macs"] = wol_macs
            # No await between validation and the sibling writes.
            for target in guest_selection_entries(self.hass, self.config_entry):
                target_options = new_options if target.entry_id == self.config_entry.entry_id else dict(target.options)
                for key, plan in plans.items():
                    if target.entry_id in plan:
                        target_options[key] = list(plan[target.entry_id])
                if target.entry_id != self.config_entry.entry_id and target_options != dict(target.options):
                    self.hass.config_entries.async_update_entry(target, options=target_options)
            if new_data != dict(self.config_entry.data) or new_options != dict(options):
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=new_data, options=new_options,
                )
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data=new_options)

        # Load resources via API
        client = ProxmoxClient(
            host=conf[CONF_HOST],
            user=conf[CONF_USER],
            password=conf.get(CONF_PASSWORD),
            token_id=conf.get(CONF_TOKEN_ID),
            token_secret=conf.get(CONF_TOKEN_SECRET),
            server_type="PVE",
            verify_ssl=conf.get(CONF_VERIFY_SSL, False),
        )

        try:
            self._guest_client = client
            self._guest_choices = await self._guest_inventory(client)
            self._guest_visible = {
                field: {vmid: label for vmid, label in self._guest_choices[field].items()
                        if self._guest_choices["locations"][field][vmid] == conf[CONF_NODE]}
                for field in ("vms", "cts")
            }
            self._guest_snapshot = self._guest_selection_snapshot()
            self._guest_previous = {field: self._previous_guest_ids(field) for field in ("vms", "cts")}
            storage_data = await client.get_storages(self.hass, conf[CONF_NODE]) or []

            detected_macs = {}
            for node in (current_node,):
                try:
                    net_data = await client.get_node_network(self.hass, node) or []
                    for iface in net_data:
                        if iface.get("active") and iface.get("mac-address"):
                            detected_macs[node] = iface.get("mac-address")
                            break
                except Exception:
                    continue

            vm_options = self._guest_visible["vms"]
            ct_options = self._guest_visible["cts"]

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
                if storage_node and storage_node != conf[CONF_NODE]:
                    continue
                if storage_path.startswith("/mnt") or storage_path.startswith("/media"):
                    if total == 0 and used == 0:
                        continue
                st_options[st_name] = st_name

            effective = get_effective_guest_selections(
                self.hass, self.config_entry, _entry_cluster_id(self.hass, self.config_entry),
                get_entry_guest_selection(self.config_entry, "selected_vms", []),
                get_entry_guest_selection(self.config_entry, "selected_cts", []),
            )
            self._guest_defaults = {}
            for field, selection in zip(("vms", "cts"), effective):
                ids = selection_guest_ids(selection)
                self._guest_defaults[field] = sorted(self._guest_visible[field] if ids is None
                                                      else ids & self._guest_visible[field].keys())
            selected_vms = self._guest_defaults["vms"]
            selected_cts = self._guest_defaults["cts"]

            selected_storage = [
                s
                for s in conf.get("selected_storage", list(st_options.keys()))
                if s in st_options
            ]

            wol_fields = {
                vol.Optional(
                    "wol_mac",
                    default=wol_mac_map.get(current_node) or detected_macs.get(current_node, ""),
                ): str
            }

            schema_fields = {
                        vol.Optional("vms", default=selected_vms): cv.multi_select(
                            vm_options
                        ),
                        vol.Optional("cts", default=selected_cts): cv.multi_select(
                            ct_options
                        ),
                        vol.Optional(
                            "storage", default=selected_storage
                        ): cv.multi_select(st_options),
                        vol.Optional(
                            "enable_physical_disks",
                            default=conf.get("enable_physical_disks", True),
                        ): bool,
                        vol.Optional(
                            "enable_lm_sensors",
                            default=conf.get("enable_lm_sensors", True),
                        ): bool,
                        vol.Optional(
                            "enable_smart_monitoring",
                            default=conf.get("enable_smart_monitoring", True),
                        ): bool,
                        vol.Optional(
                            "enable_node_controls",
                            default=conf.get("enable_node_controls", False),
                        ): bool,
                        vol.Optional(
                            "enable_guest_agent_metrics",
                            default=conf.get("enable_guest_agent_metrics", False),
                        ): bool,
                        vol.Optional(
                            CONF_VERIFY_SSL,
                            default=conf.get(CONF_VERIFY_SSL, False),
                        ): bool,
                **wol_fields,
            }
            if len(self._scope_choices()) > 1:
                schema_fields[vol.Optional("cluster_scope_action", default="keep")] = (
                    self._scope_validator()
                )
            self._pve_schema = vol.Schema(schema_fields)
            return self.async_show_form(step_id="init", data_schema=self._pve_schema)

        except Exception:
            _LOGGER.exception("PVE options fallback: guest discovery is unavailable")
            self._guest_choices = None
            schema_fields = {
                        vol.Optional("wol_mac", default=wol_mac_map.get(current_node, "")): str,
                        vol.Optional(
                            "enable_physical_disks",
                            default=conf.get("enable_physical_disks", True),
                        ): bool,
                        vol.Optional(
                            "enable_lm_sensors",
                            default=conf.get("enable_lm_sensors", True),
                        ): bool,
                        vol.Optional(
                            "enable_smart_monitoring",
                            default=conf.get("enable_smart_monitoring", True),
                        ): bool,
                        vol.Optional(
                            "enable_node_controls",
                            default=conf.get("enable_node_controls", False),
                        ): bool,
                        vol.Optional(
                            "enable_guest_agent_metrics",
                            default=conf.get("enable_guest_agent_metrics", False),
                        ): bool,
                        vol.Optional(
                            CONF_VERIFY_SSL,
                            default=conf.get(CONF_VERIFY_SSL, False),
                        ): bool,
            }
            if len(self._scope_choices()) > 1:
                schema_fields[vol.Optional("cluster_scope_action", default="keep")] = (
                    self._scope_validator()
                )
            self._pve_schema = vol.Schema(schema_fields)
            return self.async_show_form(step_id="init", data_schema=self._pve_schema,
                                        errors={"base": "guest_discovery_unavailable"})
