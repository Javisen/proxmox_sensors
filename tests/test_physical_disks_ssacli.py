import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
PHYSICAL_DISKS = (
    ROOT / "custom_components" / "proxmox_sensors" / "logic" / "physical_disks.py"
)


def load_physical_disks():
    module_name = "physical_disks_test"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, PHYSICAL_DISKS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MergeDiskInventoriesTests(unittest.TestCase):
    def test_hardware_value_rejects_punctuated_all_zero_identity(self):
        physical_disks = load_physical_disks()

        self.assertIsNone(physical_disks.hardware_value("0x00:00:00"))
        for placeholder in ("N / A", "!!UNKNOWN!!", "NOT-AVAILABLE", "SERIAL NUMBER"):
            self.assertIsNone(physical_disks.hardware_value(placeholder))
        with self.assertRaises(physical_disks.DiskIdentityError):
            physical_disks.plan_disks(
                "scope",
                {"/dev/ssacli-slot-1-pd-1i-1-1": {"wwn": "0x00:00:00"}},
                {},
            )

    def test_reconcile_disk_inventories_preserves_last_good_on_source_failure(self):
        physical_disks = load_physical_disks()
        previous = [{
            "devpath": "/dev/ssacli-slot-1-pd-1i-1-1",
            "serial": "DRIVE-SERIAL-1",
        }]

        for pve, sidecar in ((RuntimeError("pve"), []), ([], RuntimeError("sidecar"))):
            disks, cleanup_confirmed = physical_disks.reconcile_disk_inventories(
                pve, sidecar, previous
            )
            self.assertEqual(disks, previous)
            self.assertFalse(cleanup_confirmed)

    def test_reconcile_disk_inventories_confirms_old_sidecar_404_sentinel(self):
        physical_disks = load_physical_disks()
        pve = [{"devpath": "/dev/sda", "serial": "LOGICAL-SERIAL-1"}]

        disks, cleanup_confirmed = physical_disks.reconcile_disk_inventories(
            pve, None, []
        )

        self.assertEqual(disks, pve)
        self.assertTrue(cleanup_confirmed)

    def test_matching_hardware_identity_supports_wwn_only_responses(self):
        physical_disks = load_physical_disks()

        self.assertFalse(physical_disks.matching_hardware_identity(
            {"wwn": "WWN-1"}, "not-a-record"
        ))
        self.assertTrue(physical_disks.matching_hardware_identity(
            {"serial": "SERIAL-1", "wwn": "WWN-1"},
            {"wwn": "wwn-1"},
        ))
        self.assertFalse(physical_disks.matching_hardware_identity(
            {"serial": "SERIAL-1", "wwn": "WWN-1"},
            {"serial": "SERIAL-2", "wwn": "WWN-1"},
        ))
        self.assertFalse(physical_disks.matching_hardware_identity(
            {"serial": "SERIAL-1"},
            {"wwn": "WWN-1"},
        ))

    def test_plan_disks_preserves_identity_across_wwn_formatting(self):
        physical_disks = load_physical_disks()
        identifiers, bindings = physical_disks.plan_disks(
            "scope",
            {"/dev/ssacli-slot-1-pd-1i-1-1": {"wwn": "aabbcc"}},
            {"existing-id": {"wwn": "0xAA:BB:CC", "serial": None}},
        )

        self.assertEqual(
            identifiers,
            {"/dev/ssacli-slot-1-pd-1i-1-1": "existing-id"},
        )
        self.assertEqual(bindings["existing-id"]["wwn"], "aabbcc")

    def test_merge_disk_inventories_combines_pve_and_sidecar_disks(self):
        physical_disks = load_physical_disks()
        pve = [{
            "devpath": "/dev/sda",
            "serial": "LOGICAL-SERIAL-1",
            "size": 1_000_000_000_000,
        }]
        sidecar = [{
            "devpath": "/dev/ssacli-slot-1-pd-1i-1-1",
            "serial": "PHYSICAL-SERIAL-1",
            "wwn": "PHYSICAL-WWN-1",
            "size": 1_000_000_000_000,
        }]

        merged = physical_disks.merge_disk_inventories(pve, sidecar)

        self.assertEqual(merged, [*pve, *sidecar])

    def test_merge_disk_inventories_preserves_controller_logical_volumes(self):
        physical_disks = load_physical_disks()
        logical = [{
            "devpath": "/dev/sda",
            "model": "LOGICAL_VOLUME",
            "serial": "LOGICAL-SERIAL-1",
            "size": 1_000_000_000_000,
        }]
        physical = [{
            "devpath": "/dev/ssacli-slot-1-pd-1i-1-1",
            "model": "HP MB1000FCWDE",
            "serial": "PHYSICAL-SERIAL-1",
            "wwn": "PHYSICAL-WWN-1",
            "size": 1_000_000_000_000,
        }]

        self.assertEqual(
            physical_disks.merge_disk_inventories(logical, physical),
            [*logical, *physical],
        )

    def test_merge_disk_inventories_rejects_duplicate_path_or_identity(self):
        physical_disks = load_physical_disks()
        first = {
            "devpath": "/dev/ssacli-slot-1-pd-1i-1-1",
            "serial": "PHYSICAL-SERIAL-1",
        }
        duplicate_path = {
            "devpath": "/dev/ssacli-slot-1-pd-1i-1-1",
            "serial": "PHYSICAL-SERIAL-2",
        }
        duplicate_identity = {
            "devpath": "/dev/ssacli-slot-1-pd-1i-1-2",
            "serial": "PHYSICAL-SERIAL-1",
        }

        with self.assertRaises(physical_disks.DiskIdentityError):
            physical_disks.merge_disk_inventories([first], [duplicate_path])
        with self.assertRaises(physical_disks.DiskIdentityError):
            physical_disks.merge_disk_inventories([first], [duplicate_identity])
        with self.assertRaises(physical_disks.DiskIdentityError):
            physical_disks.merge_disk_inventories(
                [{"devpath": "/dev/sdb", "wwn": "0xAA:BB:CC"}],
                [{"devpath": "/dev/ssacli-slot-1-pd-2i-1-1", "wwn": "aabbcc"}],
            )


if __name__ == "__main__":
    unittest.main()
