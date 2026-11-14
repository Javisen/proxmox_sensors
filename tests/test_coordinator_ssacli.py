import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "proxmox_sensors"
COORDINATOR = COMPONENT / "coordinator.py"
PHYSICAL_DISKS = COMPONENT / "logic" / "physical_disks.py"


def module(name, **values):
    value = types.ModuleType(name)
    for key, item in values.items():
        setattr(value, key, item)
    return value


class FakeDataUpdateCoordinator:
    def __init__(self, hass, logger, *, name, update_method, update_interval):
        self.hass = hass
        self.name = name
        self.update_method = update_method
        self.update_interval = update_interval
        self.data = None


class UpdateFailed(Exception):
    pass


class FakeSmartCache:
    def __init__(self, interval):
        self.value = {}

    def should_refresh(self, enabled, now):
        return enabled

    def accept(self, value, now):
        self.value = value

    def snapshot(self, node):
        return {node: self.value}


class FakeDiskSmartSchedule:
    def __init__(self):
        self.generation = {}
        self.last_attempt = {}
        self.values = {}

    def due(self, identifier, now, minutes, enabled):
        return enabled

    def accept_if_current(self, identifier, response, now, wall_now, generation, attempted):
        self.values[identifier] = response

    def snapshot(self, identifier, wall_now, enabled):
        response = self.values.get(identifier, {"status": "disabled" if not enabled else "pending"})
        return {
            "status": response.get("status"),
            "data": response.get("data"),
            "last_read": None,
            "age_seconds": None,
        }

    def invalidate(self, identifier):
        self.values.pop(identifier, None)


class FakeEntry:
    def __init__(self, physical=True, smart=True, memory=True):
        self.entry_id = "entry-1"
        self.data = {
            "platform_type": "PVE",
            "node": "pve",
            "cluster_id": "cluster",
            "enable_lm_sensors": False,
            "enable_smart_monitoring": smart,
            "enable_memory_monitoring": memory,
            "selected_vms": [],
            "selected_cts": [],
            "selected_storage": [],
        }
        self.options = {
            "enable_physical_disks": physical,
            "enable_smart_monitoring": smart,
            "enable_memory_monitoring": memory,
            "enable_guest_agent_metrics": False,
        }


class FakeConfigEntries:
    def async_update_entry(self, entry, *, data=None, options=None):
        if data is not None:
            entry.data = data
        if options is not None:
            entry.options = options


class FakeHass:
    def __init__(self):
        self.config_entries = FakeConfigEntries()
        self.data = {}


class FakeClient:
    def __init__(self):
        self.fail_sidecar_inventory = False
        self.smart_disk_calls = []

    async def get_cluster_resources(self, *args):
        return [{"type": "node", "node": "pve", "status": "online"}]

    async def get_cluster_status(self, *args):
        return {"type": "cluster", "name": "cluster"}

    async def get_cluster_ha_status(self, *args):
        return {}

    async def get_cluster_firewall_options(self, *args):
        return {}

    async def get_node_status(self, *args):
        return {"data": {"status": "online"}}

    async def get_node_updates(self, *args):
        return []

    async def get_node_network(self, *args):
        return []

    async def get_cluster_tasks(self, *args):
        return []

    async def get_vms(self, *args):
        return []

    async def get_containers(self, *args):
        return []

    async def get_storages(self, *args):
        return []

    async def get_zfs_pools(self, *args):
        return []

    async def get_disks(self, *args):
        return [{
            "devpath": "/dev/sda",
            "serial": "LOGICAL-SERIAL-1",
            "model": "LOGICAL_VOLUME",
            "size": 1_000_000_000_000,
            "type": "hdd",
        }]

    async def get_sidecar_disks_http(self, *args):
        if self.fail_sidecar_inventory:
            raise RuntimeError("sidecar unavailable")
        return [{
            "devpath": "/dev/ssacli-slot-1-pd-1i-1-1",
            "serial": "PHYSICAL-SERIAL-1",
            "wwn": "PHYSICAL-WWN-1",
            "model": "HP DISK",
            "size": 1_000_000_000_000,
            "type": "hdd",
            "device_type": "ssacli",
            "health_source": "ssacli",
            "controller_health_passed": True,
            "smart_available": False,
            "status": "OK",
            "exposed_to_os": False,
        }]

    async def get_mounts(self, *args):
        return {"marker": "mounts"}

    async def get_memory_http(self, *args):
        return {"modules": [], "total_modules": 0, "total_gb": 0, "timestamp": None}

    async def get_ksm_http(self, *args):
        return {"available": True, "marker": "ksm"}

    async def get_lm_sensors_http(self, *args):
        return {}

    async def get_smart_data_http(self, *args):
        return {"global": {"marker": "smart"}}

    async def get_smart_disk_http(self, hass, node, path, protect, raise_errors):
        self.smart_disk_calls.append((path, protect))
        if path.startswith("/dev/ssacli-"):
            data = (await self.get_sidecar_disks_http())[0]
        else:
            data = {
                "devpath": path,
                "serial": "LOGICAL-SERIAL-1",
                "smart_available": True,
                "smart_passed": True,
            }
        return {"status": "ok", "data": data}


def load_coordinator():
    package = module("custom_components")
    package.__path__ = []
    component = module("custom_components.proxmox_sensors")
    component.__path__ = [str(COMPONENT)]
    logic = module("custom_components.proxmox_sensors.logic")
    logic.__path__ = [str(COMPONENT / "logic")]

    physical_spec = importlib.util.spec_from_file_location(
        "custom_components.proxmox_sensors.logic.physical_disks", PHYSICAL_DISKS
    )
    assert physical_spec is not None and physical_spec.loader is not None
    physical = importlib.util.module_from_spec(physical_spec)
    physical_spec.loader.exec_module(physical)

    class AuthenticationError(Exception):
        pass

    class CannotConnect(Exception):
        pass

    class PermissionError(Exception):
        pass

    class RequestTimeout(Exception):
        pass

    class RequestConnectionError(Exception):
        pass

    class RequestSSLError(Exception):
        pass

    stubs = {
        "custom_components": package,
        "custom_components.proxmox_sensors": component,
        "custom_components.proxmox_sensors.logic": logic,
        "homeassistant": module("homeassistant"),
        "homeassistant.helpers": module("homeassistant.helpers"),
        "homeassistant.helpers.update_coordinator": module(
            "homeassistant.helpers.update_coordinator",
            DataUpdateCoordinator=FakeDataUpdateCoordinator,
            UpdateFailed=UpdateFailed,
        ),
        "requests": module(
            "requests",
            exceptions=types.SimpleNamespace(
                Timeout=RequestTimeout,
                ConnectionError=RequestConnectionError,
                SSLError=RequestSSLError,
            ),
        ),
        "custom_components.proxmox_sensors.const": module(
            "custom_components.proxmox_sensors.const",
            DOMAIN="proxmox_sensors", CONF_NODE="node", CONF_PLATFORM_TYPE="platform_type",
        ),
        "custom_components.proxmox_sensors.api": module(
            "custom_components.proxmox_sensors.api",
            AuthenticationError=AuthenticationError,
            CannotConnect=CannotConnect,
            PermissionError=PermissionError,
        ),
        "custom_components.proxmox_sensors.logic.guest_keys": module(
            "guest_keys",
            find_guest_node_in_resources=lambda *args: None,
            make_guest_key=lambda node, vmid: f"{node}:{vmid}",
            matches_selected_guest=lambda *args: False,
        ),
        "custom_components.proxmox_sensors.logic.guest_agent": module(
            "guest_agent", collect_vm_disk_usage=lambda *args, **kwargs: ({}, {})
        ),
        "custom_components.proxmox_sensors.logic.guest_selection": module(
            "guest_selection",
            get_effective_guest_selections=lambda hass, entry, cluster, vms, cts: (vms, cts),
            get_entry_guest_selection=lambda entry, key, default=None: entry.options.get(
                key, entry.data.get(key, default)
            ),
            set_effective_guest_selections=lambda result, vms, cts: result.update({
                "_effective_selected_vms": vms, "_effective_selected_cts": cts,
            }),
        ),
        "custom_components.proxmox_sensors.logic.pdm": module(
            "pdm",
            build_pdm_remotes=lambda *args: {},
            merge_pdm_sections=lambda *args: {},
            merge_pdm_updates=lambda *args: {},
        ),
        "custom_components.proxmox_sensors.logic.smart_cache": module(
            "smart_cache", SmartCache=FakeSmartCache
        ),
        "custom_components.proxmox_sensors.logic.disk_smart": module(
            "disk_smart",
            DiskSmartSchedule=FakeDiskSmartSchedule,
            preferences=lambda options, identifier, minutes, enabled=True: {
                "minutes": minutes, "enabled": enabled, "protect_standby": False,
            },
        ),
        "custom_components.proxmox_sensors.logic.physical_disks": physical,
        "custom_components.proxmox_sensors.logic.physical_disk_type": module(
            "physical_disk_type", apply_inventory_types=lambda disks, identities, options: disks
        ),
    }

    with patch.dict(sys.modules, stubs):
        spec = importlib.util.spec_from_file_location(
            "custom_components.proxmox_sensors.coordinator", COORDINATOR
        )
        assert spec is not None and spec.loader is not None
        loaded = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded)
    return loaded


class CoordinatorSsacliTests(unittest.TestCase):
    def test_physical_inventory_refresh_routing_and_failure_preservation(self):
        coordinator_module = load_coordinator()
        hass = FakeHass()
        entry = FakeEntry(physical=True, smart=True, memory=True)
        client = FakeClient()

        coordinator = asyncio.run(
            coordinator_module.create_proxmox_coordinator(hass, entry, client)
        )
        first = asyncio.run(coordinator.update_method())

        self.assertTrue(first["_cleanup_confirmed"]["node_disks"])
        self.assertEqual(len(first["node_disks"]), 2)
        self.assertEqual(first["mounts"], {"marker": "mounts"})
        self.assertEqual(first["ksm_status"]["marker"], "ksm")
        self.assertIn("pve", first["memory"])
        self.assertTrue(any(path.startswith("/dev/ssacli-") for path, _ in client.smart_disk_calls))

        call_count = len(client.smart_disk_calls)
        client.fail_sidecar_inventory = True
        second = asyncio.run(coordinator.update_method())

        self.assertFalse(second["_cleanup_confirmed"]["node_disks"])
        self.assertEqual(second["node_disks"], first["node_disks"])
        self.assertEqual(len(client.smart_disk_calls), call_count)
        self.assertEqual(second["mounts"], {"marker": "mounts"})
        self.assertEqual(second["ksm_status"]["marker"], "ksm")

    def test_global_smart_and_indexing_when_physical_disks_disabled(self):
        coordinator_module = load_coordinator()
        hass = FakeHass()
        entry = FakeEntry(physical=False, smart=True, memory=False)
        client = FakeClient()

        coordinator = asyncio.run(
            coordinator_module.create_proxmox_coordinator(hass, entry, client)
        )
        result = asyncio.run(coordinator.update_method())

        self.assertTrue(result["_cleanup_confirmed"]["node_disks"])
        self.assertEqual(result["node_disks"], [])
        self.assertEqual(result["mounts"], {"marker": "mounts"})
        self.assertEqual(result["ksm_status"]["marker"], "ksm")
        self.assertEqual(result["smart"]["pve"], {"global": {"marker": "smart"}})


if __name__ == "__main__":
    unittest.main()
