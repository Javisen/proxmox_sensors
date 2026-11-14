import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "custom_components" / "proxmox_sensors" / "api.py"


def load_api():
    module_name = "proxmox_sensors_api_test"
    sys.modules.pop(module_name, None)
    proxmoxer = types.ModuleType("proxmoxer")
    setattr(proxmoxer, "ProxmoxAPI", Mock)
    requests = types.ModuleType("requests")
    setattr(requests, "get", Mock())
    spec = importlib.util.spec_from_file_location(module_name, API)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"proxmoxer": proxmoxer, "requests": requests}):
        spec.loader.exec_module(module)
    return module


class FakeHass:
    async def async_add_executor_job(self, function, *args):
        return function(*args)


class SidecarDiskApiTests(unittest.TestCase):
    def test_get_smart_disk_http_rejects_non_mapping_ok_data(self):
        api = load_api()
        client = api.ProxmoxClient("pve.example", "monitor@pve")
        response = Mock()
        response.json.return_value = {"status": "ok", "data": "not-a-record"}

        with patch.object(api.requests, "get", return_value=response):
            with self.assertRaisesRegex(ValueError, "Invalid per-disk SMART response"):
                asyncio.run(
                    client.get_smart_disk_http(
                        FakeHass(), "pve2", "/dev/ssacli-slot-1-pd-1i-1-1", False, True
                    )
                )

    def test_get_sidecar_disks_http_returns_inventory(self):
        api = load_api()
        client = api.ProxmoxClient("pve.example", "monitor@pve")
        inventory = [{
            "devpath": "/dev/ssacli-slot-1-pd-1i-1-1",
            "serial": "DRIVE-SERIAL-1",
            "wwn": "DRIVE-WWN-1",
            "model": "HP MB1000FCWDE",
            "size": 1_000_000_000_000,
            "device_type": "ssacli",
            "health_source": "ssacli",
            "status": "OK",
            "controller_health_passed": True,
            "exposed_to_os": False,
        }]
        response = Mock()
        response.json.return_value = inventory

        with patch.object(api.requests, "get", return_value=response) as get:
            result = asyncio.run(
                client.get_sidecar_disks_http(FakeHass(), "pve2", raise_errors=True)
            )

        self.assertEqual(result, inventory)
        get.assert_called_once_with("http://pve.example:9000/disks", timeout=9)
        response.raise_for_status.assert_called_once_with()

    def test_get_sidecar_disks_http_treats_404_as_unsupported(self):
        api = load_api()
        client = api.ProxmoxClient("pve.example", "monitor@pve")
        response = Mock(status_code=404)

        with patch.object(api.requests, "get", return_value=response):
            result = asyncio.run(
                client.get_sidecar_disks_http(
                    FakeHass(), "pve2", raise_errors=True
                )
            )

        self.assertIsNone(result)
        response.raise_for_status.assert_not_called()

    def test_get_sidecar_disks_http_rejects_empty_selector_components(self):
        api = load_api()
        client = api.ProxmoxClient("pve.example", "monitor@pve")
        response = Mock()
        response.json.return_value = [{
            "devpath": "/dev/ssacli-slot--pd-",
            "serial": "DRIVE-SERIAL-1",
            "size": 1_000_000_000_000,
            "device_type": "ssacli",
            "health_source": "ssacli",
            "status": "OK",
            "controller_health_passed": True,
            "exposed_to_os": False,
        }]

        with patch.object(api.requests, "get", return_value=response):
            with self.assertRaisesRegex(ValueError, "sidecar disk inventory is malformed"):
                asyncio.run(
                    client.get_sidecar_disks_http(
                        FakeHass(), "pve2", raise_errors=True
                    )
                )

    def test_get_sidecar_disks_http_rejects_punctuated_zero_identity(self):
        api = load_api()
        client = api.ProxmoxClient("pve.example", "monitor@pve")
        response = Mock()
        response.json.return_value = [{
            "devpath": "/dev/ssacli-slot-1-pd-1i-1-1",
            "serial": "00:00:00",
            "size": 1_000_000_000_000,
            "device_type": "ssacli",
            "health_source": "ssacli",
            "status": "OK",
            "controller_health_passed": True,
            "exposed_to_os": False,
        }]

        with patch.object(api.requests, "get", return_value=response):
            with self.assertRaisesRegex(ValueError, "sidecar disk inventory is malformed"):
                asyncio.run(
                    client.get_sidecar_disks_http(
                        FakeHass(), "pve2", raise_errors=True
                    )
                )

    def test_get_sidecar_disks_http_rejects_placeholder_identities(self):
        api = load_api()
        client = api.ProxmoxClient("pve.example", "monitor@pve")
        response = Mock()

        for placeholder in (
            "not available", "na", "null", "not specified",
            "to be filled by o.e.m.", "123456789", "serialnumber",
            "N / A", "!!UNKNOWN!!", "NOT-AVAILABLE", "SERIAL NUMBER",
        ):
            response.json.return_value = [{
                "devpath": "/dev/ssacli-slot-1-pd-1i-1-1",
                "serial": placeholder,
                "size": 1_000_000_000_000,
                "device_type": "ssacli",
                "health_source": "ssacli",
                "status": "OK",
                "controller_health_passed": True,
                "exposed_to_os": False,
            }]
            with patch.object(api.requests, "get", return_value=response):
                with self.assertRaisesRegex(ValueError, "sidecar disk inventory is malformed"):
                    asyncio.run(
                        client.get_sidecar_disks_http(
                            FakeHass(), "pve2", raise_errors=True
                        )
                    )

    def test_get_sidecar_disks_http_rejects_malformed_inventory(self):
        api = load_api()
        client = api.ProxmoxClient("pve.example", "monitor@pve")
        response = Mock()
        response.json.return_value = [{
            "devpath": "/dev/ssacli-../bad",
            "serial": "DRIVE-SERIAL-1",
            "size": True,
            "device_type": "ssacli",
            "health_source": "ssacli",
            "status": "OK",
            "controller_health_passed": True,
            "exposed_to_os": False,
        }]

        with patch.object(api.requests, "get", return_value=response):
            with self.assertRaisesRegex(ValueError, "sidecar disk inventory is malformed"):
                asyncio.run(
                    client.get_sidecar_disks_http(
                        FakeHass(), "pve2", raise_errors=True
                    )
                )

    def test_get_sidecar_disks_http_rejects_duplicate_secondary_identity(self):
        api = load_api()
        client = api.ProxmoxClient("pve.example", "monitor@pve")
        response = Mock()
        response.json.return_value = [
            {
                "devpath": f"/dev/ssacli-slot-1-pd-1i-1-{index}",
                "serial": "DUPLICATE-SERIAL",
                "wwn": f"WWN-{index}",
                "size": 1_000_000_000_000,
                "device_type": "ssacli",
                "health_source": "ssacli",
                "status": "OK",
                "controller_health_passed": True,
                "exposed_to_os": False,
            }
            for index in (1, 2)
        ]

        with patch.object(api.requests, "get", return_value=response):
            with self.assertRaisesRegex(ValueError, "sidecar disk inventory is malformed"):
                asyncio.run(
                    client.get_sidecar_disks_http(
                        FakeHass(), "pve2", raise_errors=True
                    )
                )


if __name__ == "__main__":
    unittest.main()
