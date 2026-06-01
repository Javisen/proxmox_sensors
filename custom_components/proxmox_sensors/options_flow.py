# =========OPTIONS FLOW — PROXMOX EXTENDED SENSORS===========

from __future__ import annotations
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

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

_LOGGER = logging.getLogger(__name__)


class ProxmoxOptionsFlow(config_entries.OptionsFlow):

    async def async_step_init(self, user_input=None) -> FlowResult:

        conf = self.config_entry.data
        server_type = conf.get(CONF_PLATFORM_TYPE, "PVE")

        if server_type == "CLUSTER":
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

    # ===== PVE OPTIONS =======================================

    async def async_step_pve(self, user_input=None) -> FlowResult:

        conf = self.config_entry.data
        options = self.config_entry.options or {}
        wol_mac_map = options.get("wol_macs", {})

        # Get cluster nodes for WOL fields
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
            new_data = dict(conf)
            new_data.update(
                {
                    CONF_VERIFY_SSL: user_input.get(CONF_VERIFY_SSL, False),
                    "enable_lm_sensors": user_input.get("enable_lm_sensors", True),
                    "enable_physical_disks": user_input.get(
                        "enable_physical_disks", True
                    ),
                    "enable_smart_monitoring": user_input.get(
                        "enable_smart_monitoring", True
                    ),
                    "enable_node_controls": user_input.get(
                        "enable_node_controls", False
                    ),
                    "selected_vms": user_input.get("vms", []),
                    "selected_cts": user_input.get("cts", []),
                    "selected_storage": user_input.get("storage", []),
                }
            )
            wol_macs = {
                node: user_input.get(f"wol_mac_{node}")
                for node in self._cluster_nodes
                if user_input.get(f"wol_mac_{node}")
            }
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=new_data,
                options={"wol_macs": wol_macs},
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

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
            vms_data = await client.get_vms(self.hass, conf[CONF_NODE]) or []
            cts_data = await client.get_containers(self.hass, conf[CONF_NODE]) or []
            storage_data = await client.get_storages(self.hass, conf[CONF_NODE]) or []

            detected_macs = {}
            for node in cluster_nodes:
                try:
                    net_data = await client.get_node_network(self.hass, node) or []
                    for iface in net_data:
                        if iface.get("active") and iface.get("mac-address"):
                            detected_macs[node] = iface.get("mac-address")
                            break
                except Exception:
                    continue

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
                if storage_node and storage_node != conf[CONF_NODE]:
                    continue
                if storage_path.startswith("/mnt") or storage_path.startswith("/media"):
                    if total == 0 and used == 0:
                        continue
                st_options[st_name] = st_name

            selected_vms = [
                v
                for v in (conf.get("selected_vms") or list(vm_options.keys()))
                if v in vm_options
            ]
            selected_cts = [
                c
                for c in (conf.get("selected_cts") or list(ct_options.keys()))
                if c in ct_options
            ]
            selected_storage = [
                s
                for s in (conf.get("selected_storage") or list(st_options.keys()))
                if s in st_options
            ]

            wol_fields = {
                vol.Optional(
                    f"wol_mac_{node}",
                    default=wol_mac_map.get(node) or detected_macs.get(node, ""),
                ): str
                for node in cluster_nodes
            }

            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
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
                            CONF_VERIFY_SSL,
                            default=conf.get(CONF_VERIFY_SSL, False),
                        ): bool,
                        **wol_fields,
                    }
                ),
            )

        except Exception as err:
            _LOGGER.warning("PVE options fallback (API error): %s", err)
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
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
                            CONF_VERIFY_SSL,
                            default=conf.get(CONF_VERIFY_SSL, False),
                        ): bool,
                    }
                ),
            )
