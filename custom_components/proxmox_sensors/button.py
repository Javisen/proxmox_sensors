"""Button entities for Proxmox Extended Sensors."""

import asyncio
import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers import device_registry as dr
from homeassistant.components import persistent_notification

from .pbs_actions import run_gc, run_prune, run_verify, run_sync
from .const import DOMAIN, CONF_NODE, CONF_PLATFORM_TYPE
from .logic.guest_keys import make_guest_key, matches_selected_guest

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up button entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    if data.get("server_type") == "PVE":
        client = getattr(coordinator, "client", data.get("client"))
    else:
        client = data.get("client")

    selected_vms = entry.options.get("selected_vms", entry.data.get("selected_vms", []))
    selected_cts = entry.options.get("selected_cts", entry.data.get("selected_cts", []))
    enable_node_controls = entry.options.get(
        "enable_node_controls", entry.data.get("enable_node_controls", True)
    )

    node = entry.data.get(CONF_NODE, "Proxmox")
    server_type = entry.data.get(CONF_PLATFORM_TYPE, "PVE")
    features = data.get("features", {})

    entities = []
    c_data = coordinator.data

    if not c_data:
        _LOGGER.warning("No data found in coordinator for %s", node)
        return

    # ========= PVE BUTTONS ===================
    if server_type == "PVE":

        device_registry = dr.async_get(hass)
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, f"proxmox_node_{node}")},
            manufacturer="Proxmox",
            model="Proxmox Node",
            name=f"1. Node: {node}",
        )

        entry = coordinator.config_entry
        wol_macs = entry.options.get("wol_macs", {})

        # -------- NODE CONTROL BUTTONS --------
        if enable_node_controls:
            entities.append(
                ProxmoxNodeButton(
                    coordinator, client, node, "Node", "reboot", "mdi:restart"
                )
            )
            entities.append(
                ProxmoxNodeButton(
                    coordinator, client, node, "Node", "shutdown", "mdi:power"
                )
            )

        # -------- WOL BUTTON --------
        if wol_macs.get(node):
            entities.append(
                ProxmoxNodeButton(
                    coordinator, client, node, "Node", "wake", "mdi:power-on"
                )
            )

        # LXC buttons
        if features.get("enable_cts", True):
            ct_map = c_data.get("cts", {})
            for ct_key, ct_data in ct_map.items():
                ct_id = ct_data.get("vmid", ct_key)
                ct_node = ct_data.get("node", node)
                if matches_selected_guest(selected_cts, ct_node, ct_id, ct_key):
                    label = ct_data.get("name", ct_id)

                    ct_commands = [
                        ("start", "mdi:play"),
                        ("shutdown", "mdi:power"),
                        ("stop", "mdi:stop"),
                        ("reboot", "mdi:restart"),
                    ]

                    for cmd, icon in ct_commands:
                        entities.append(
                            ProxmoxContainerButton(
                                coordinator,
                                client,
                                ct_id,
                                ct_node,
                                label,
                                cmd,
                                icon,
                                guest_key=ct_key,
                            )
                        )

        # VM buttons
        if features.get("enable_vms", True):
            vm_map = c_data.get("vms", {})
            for vm_key, vm_data in vm_map.items():
                vm_id = vm_data.get("vmid", vm_key)
                vm_node = vm_data.get("node", node)
                if matches_selected_guest(selected_vms, vm_node, vm_id, vm_key):
                    label = vm_data.get("name", vm_id)

                    vm_commands = [
                        ("start", "mdi:play"),
                        ("shutdown", "mdi:power"),
                        ("stop", "mdi:stop"),
                        ("reboot", "mdi:restart"),
                        ("reset", "mdi:restart-alert"),
                        ("pause", "mdi:pause"),
                        ("hibernate", "mdi:download"),
                        ("resume", "mdi:play-pause"),
                    ]

                    for cmd, icon in vm_commands:
                        entities.append(
                            ProxmoxVMButton(
                                coordinator,
                                client,
                                vm_id,
                                vm_node,
                                label,
                                cmd,
                                icon,
                                guest_key=vm_key,
                            )
                        )

    # ========PBS BUTTONS====================
    elif server_type == "PBS":
        server_id = entry.data.get("server_id", "pbs_main")
        datastores = c_data.get("pbs_datastores", {})

        for datastore_name in datastores.keys():
            entities.append(PBSGCButton(coordinator, client, datastore_name))
            entities.append(PBSPruneButton(coordinator, client, datastore_name))
            entities.append(PBSVerifyButton(coordinator, client, datastore_name))
            entities.append(PBSSyncButton(coordinator, client, datastore_name))

        # -------- WOL BUTTON --------
        mac = entry.data.get("wol_mac")

        if mac:
            entities.append(PBSWakeButton(coordinator, client, server_id))

        # -------- NODE CONTROL BUTTONS --------
        enable_pbs_node_controls = entry.options.get(
            "enable_pbs_node_controls",
            entry.data.get("enable_pbs_node_controls", True),
        )

        if enable_pbs_node_controls:
            entities.append(PBSShutdownButton(coordinator, client, server_id))
            entities.append(PBSRebootButton(coordinator, client, server_id))

    _LOGGER.info("Total button entities created: %d", len(entities))
    async_add_entities(entities)


# =======PBS BUTTON CLASSES=============


class PBSBaseButton(CoordinatorEntity, ButtonEntity):
    """Base class for PBS maintenance buttons."""

    def __init__(self, coordinator, client, datastore, command_name, command_display):
        super().__init__(coordinator)

        clean_datastore = (
            datastore.lower()
            .replace("-", "_")
            .replace(" ", "_")
        )

        self._client = client
        self._datastore = datastore

        # ONLY for HA entity_id safety
        self._sensor_entity_id = f"sensor.{clean_datastore}_last_action"

        self._command_name = command_name
        self._command_display = command_display

        self._attr_unique_id = f"{datastore.lower()}_{command_name}"
        self._attr_name = command_display

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"maintenance_{datastore}")},
            "name": f"Maintenance: {datastore}",
            "manufacturer": "Proxmox",
            "model": "Proxmox Backup Server",
        }

    @property
    def available(self):
        return self.coordinator.last_update_success

    def _update_last_action(self, message: str):
        self.hass.states.async_set(self._sensor_entity_id, message)


class PBSGCButton(PBSBaseButton):
    """Garbage Collection button for PBS datastore."""

    def __init__(self, coordinator, client, datastore):
        super().__init__(coordinator, client, datastore, "gc", "Garbage Collect")
        self._attr_icon = "mdi:recycle"

    async def async_press(self):
        await run_gc(self._client, self.hass, self._datastore)
        self._update_last_action("GC OK")
        await self.coordinator.async_request_refresh()


class PBSPruneButton(PBSBaseButton):
    """Prune button for PBS datastore."""

    def __init__(self, coordinator, client, datastore):
        super().__init__(coordinator, client, datastore, "prune", "Prune")
        self._attr_icon = "mdi:delete-sweep"

    async def async_press(self):
        await run_prune(self._client, self.hass, self._datastore)
        self._update_last_action("Prune OK")
        await self.coordinator.async_request_refresh()


class PBSVerifyButton(PBSBaseButton):
    """Verify button for PBS datastore."""

    def __init__(self, coordinator, client, datastore):
        super().__init__(coordinator, client, datastore, "verify", "Verify")
        self._attr_icon = "mdi:check-decagram"

    async def async_press(self):
        await run_verify(self._client, self.hass, self._datastore)
        self._update_last_action("Verify OK")
        await self.coordinator.async_request_refresh()


class PBSSyncButton(PBSBaseButton):
    """Sync button for PBS datastore."""

    def __init__(self, coordinator, client, datastore):
        super().__init__(coordinator, client, datastore, "sync", "Sync")
        self._attr_icon = "mdi:sync"

    async def async_press(self):
        await run_sync(self._client, self.hass, self._datastore)
        self._update_last_action("Sync OK")
        await self.coordinator.async_request_refresh()


# =======PBS NODE BUTTON CLASSES=============


class PBSNodeBaseButton(CoordinatorEntity, ButtonEntity):
    """Base class for PBS node control buttons (shutdown/reboot)."""

    def __init__(
        self, coordinator, client, server_id, command_name, command_display, icon
    ):
        super().__init__(coordinator)
        self._client = client
        self._server_id = server_id
        self._command_name = command_name
        self._command_display = command_display

        self._attr_unique_id = f"pbs_{server_id}_node_{command_name}"
        self._attr_name = f"PBS Node – {command_display}"
        self._attr_icon = icon

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"pbs_server_{server_id}")},
            "name": f"PBS Server: {server_id}",
            "manufacturer": "Proxmox",
            "model": "Proxmox Backup Server",
        }

    @property
    def available(self):
        return self.coordinator.last_update_success

    async def async_press(self):
        """Execute node command on PBS."""
        try:
            # For PBS, the node is always "localhost" as it's a single node system
            node = "localhost"

            # Execute the command using the client
            result = await self._client.execute_pbs_node_command(
                self.hass, node, self._command_name
            )

            if result:
                await asyncio.sleep(3)
                await self.coordinator.async_request_refresh()
                self.async_write_ha_state()
                _LOGGER.info(
                    "PBS node command %s executed successfully on %s",
                    self._command_name,
                    self._server_id,
                )
            else:
                _LOGGER.error(
                    "PBS node command %s failed on %s",
                    self._command_name,
                    self._server_id,
                )

        except Exception as e:
            _LOGGER.error(
                "Error executing PBS node command %s on %s: %s",
                self._command_name,
                self._server_id,
                e,
            )


class PBSShutdownButton(PBSNodeBaseButton):
    """Shutdown button for PBS node."""

    def __init__(self, coordinator, client, server_id):
        super().__init__(
            coordinator, client, server_id, "shutdown", "Shutdown", "mdi:power"
        )


class PBSRebootButton(PBSNodeBaseButton):
    """Reboot button for PBS node."""

    def __init__(self, coordinator, client, server_id):
        super().__init__(
            coordinator, client, server_id, "reboot", "Reboot", "mdi:restart"
        )


class PBSWakeButton(PBSNodeBaseButton):
    """Wake (WOL) button for PBS node."""

    def __init__(self, coordinator, client, server_id):
        super().__init__(
            coordinator,
            client,
            server_id,
            "wake",
            "Wake",
            "mdi:power-on",
        )

    async def async_press(self):
        """Send WOL packet."""
        try:
            entry = self.coordinator.config_entry
            mac = entry.data.get("wol_mac")

            if not mac:
                _LOGGER.error("No MAC configured for PBS %s", self._server_id)
                return

            _LOGGER.info("Sending WOL to PBS %s (%s)", self._server_id, mac)

            await self.hass.services.async_call(
                "wake_on_lan",
                "send_magic_packet",
                {"mac": mac},
                blocking=True,
            )

            persistent_notification.create(
                self.hass,
                f"WOL sent to PBS {self._server_id} ({mac})",
                "Proxmox PBS Wake",
            )

        except Exception as e:
            _LOGGER.error("Error sending WOL to PBS %s: %s", self._server_id, e)

            persistent_notification.create(
                self.hass,
                f"Error sending WOL to PBS {self._server_id}: {e}",
                "Proxmox PBS Wake ERROR",
            )


# =======PVE BUTTON CLASSES=========


class ProxmoxBaseButton(CoordinatorEntity, ButtonEntity):
    def __init__(
        self,
        coordinator,
        client,
        vmid,
        node,
        label,
        command,
        icon,
        guest_type=None,
        guest_key=None,
    ):
        super().__init__(coordinator)
        self._client = client
        self._vmid = vmid
        self._node = node
        self._label = label
        self._command = command
        self._guest_type = guest_type
        self._guest_key = guest_key or make_guest_key(node, vmid)

        self._attr_unique_id = f"proxmox_{node}_{vmid}_{command}"
        self._attr_name = f"{command.capitalize()} {label}"
        self._attr_icon = icon

    async def async_press(self):
        try:
            data = self.coordinator.data
            guest_type = self._guest_type

            if guest_type is None:
                vm_map = data.get("vms", {})
                ct_map = data.get("cts", {})
                if (
                    self._guest_key in vm_map
                    or str(self._vmid) in vm_map
                    or self._vmid in vm_map
                ):
                    guest_type = "vm"
                elif (
                    self._guest_key in ct_map
                    or str(self._vmid) in ct_map
                    or self._vmid in ct_map
                ):
                    guest_type = "ct"
                else:
                    _LOGGER.error(
                        "Guest %s (%s) not found in coordinator data",
                        self._vmid,
                        self._guest_key,
                    )
                    return

            result = False
            if guest_type == "vm":
                result = await self._client.execute_vm_command(
                    self.hass, self._node, self._vmid, self._command
                )
            else:
                result = await self._client.execute_ct_command(
                    self.hass, self._node, self._vmid, self._command
                )

            if result:
                await asyncio.sleep(2)
                await self.coordinator.async_request_refresh()
                self.async_write_ha_state()
                _LOGGER.info("Command %s completed for %s", self._command, self._vmid)
            else:
                _LOGGER.error("Command %s failed for %s", self._command, self._vmid)

        except Exception as e:
            _LOGGER.error("Error executing command on %s: %s", self._vmid, e)


class ProxmoxVMButton(ProxmoxBaseButton):
    def __init__(
        self, coordinator, client, vmid, node, label, command, icon, guest_key=None
    ):
        super().__init__(
            coordinator,
            client,
            vmid,
            node,
            label,
            command,
            icon,
            guest_type="vm",
            guest_key=guest_key,
        )

    @property
    def device_info(self):
        node_id = self._node.lower()
        vmid = str(self._vmid)

        return {
            "identifiers": {(DOMAIN, f"proxmox_vm_{node_id}_{vmid}_v1")},
            "manufacturer": "Proxmox",
            "model": "Virtual Machine",
            "name": f"4. VM: {self._label}-({self._vmid})",
            "via_device": (DOMAIN, f"proxmox_node_{node_id}"),
        }


class ProxmoxContainerButton(ProxmoxBaseButton):
    def __init__(
        self, coordinator, client, vmid, node, label, command, icon, guest_key=None
    ):
        super().__init__(
            coordinator,
            client,
            vmid,
            node,
            label,
            command,
            icon,
            guest_type="ct",
            guest_key=guest_key,
        )

    @property
    def device_info(self):
        node_id = self._node.lower()
        vmid = str(self._vmid)

        return {
            "identifiers": {(DOMAIN, f"proxmox_ct_{node_id}_{vmid}_v1")},
            "manufacturer": "Proxmox",
            "model": "Container",
            "name": f"3. CT: {self._label}-({self._vmid})",
            "via_device": (DOMAIN, f"proxmox_node_{node_id}"),
        }


class ProxmoxNodeButton(CoordinatorEntity, ButtonEntity):
    def __init__(self, coordinator, client, node, label, command, icon):
        super().__init__(coordinator)
        self._client = client
        self._node = node
        self._command = command
        self._attr_icon = icon

        server_id = coordinator.config_entry.data.get("server_id", "default").lower()
        node_id = node.lower()

        self._attr_unique_id = f"pve_{server_id}_node_{node_id}_{command}"
        self._attr_name = f"{label} – {command.capitalize()}"

    @property
    def device_info(self):
        node_id = self._node.lower()

        return {
            "identifiers": {(DOMAIN, f"proxmox_node_{node_id}")},
            "manufacturer": "Proxmox",
            "model": "Proxmox Node",
            "name": f"1. Node: {self._node.capitalize()}",
        }

    async def async_press(self):
        try:
            if hasattr(self._client, "execute_node_command"):
                result = await self._client.execute_node_command(
                    self.hass, self._node, self._command
                )
            else:
                path = f"nodes/{self._node}/status"
                data = {"command": self._command}
                result = await self._client.post(self.hass, path, data)

            if result:
                await asyncio.sleep(3)
                await self.coordinator.async_request_refresh()
                self.async_write_ha_state()
                _LOGGER.info("Node command %s executed successfully", self._command)
            else:
                _LOGGER.error("Node command %s failed", self._command)

        except Exception as e:
            _LOGGER.error(
                "Error executing %s on node %s: %s", self._command, self._node, e
            )
