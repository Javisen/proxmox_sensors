import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "custom_components" / "proxmox_sensors" / "logic" / "physical_disk_metrics.py"
DISK_SENSOR = ROOT / "custom_components" / "proxmox_sensors" / "sensor" / "disks.py"
SIDECAR = ROOT / "scripts" / "pve-sensors-api.py"
SELECT = ROOT / "custom_components" / "proxmox_sensors" / "select.py"
SWITCH = ROOT / "custom_components" / "proxmox_sensors" / "switch.py"


def load_metrics():
    spec = importlib.util.spec_from_file_location("physical_disk_metrics_test", METRICS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SsacliSensorContractTests(unittest.TestCase):
    def test_ssacli_uses_controller_health_not_smart_health(self):
        metrics = load_metrics().disk_monitoring_metrics({
            "device_type": "ssacli",
            "health_source": "ssacli",
            "type": "hdd",
        })

        self.assertIn("controller_health", metrics)
        self.assertNotIn("smart_status", metrics)
        self.assertNotIn("reallocated_sectors", metrics)
        self.assertNotIn("pending_sectors", metrics)

        sensor_source = DISK_SENSOR.read_text()
        self.assertIn('"controller_health": ("Controller health", None, None)', sensor_source)
        self.assertIn('data.get("controller_health_passed")', sensor_source)
        self.assertIn("self._controller_reported", sensor_source)
        self.assertIn('attributes["Health Source"] = "HPE Smart Array (ssacli)"', sensor_source)
        self.assertNotIn('"smart_passed": controller_health_passed', SIDECAR.read_text())
        self.assertTrue(load_metrics().controller_health_source({"device_type": "ssacli"}))
        self.assertIn("Controller polling interval", SELECT.read_text())
        switch_source = SWITCH.read_text()
        self.assertIn("Controller health polling", switch_source)
        self.assertIn("if not controller_reported and kind not in", switch_source)

    def test_ata_hdd_retains_smart_metrics(self):
        metrics = load_metrics().disk_monitoring_metrics({"type": "hdd"})

        self.assertIn("smart_status", metrics)
        self.assertIn("reallocated_sectors", metrics)
        self.assertIn("pending_sectors", metrics)
        self.assertNotIn("controller_health", metrics)


if __name__ == "__main__":
    unittest.main()
