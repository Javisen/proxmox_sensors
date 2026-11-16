import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from urllib.parse import urlencode
from unittest.mock import Mock, mock_open, patch


ROOT = Path(__file__).resolve().parents[1]
SIDECAR = ROOT / "scripts" / "pve-sensors-api.py"
FIXTURE = ROOT / "tests" / "fixtures" / "ssacli_p420.txt"


def load_sidecar():
    module_name = "pve_sensors_api_test"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, SIDECAR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    with patch("os.path.exists", return_value=True), patch(
        "builtins.open", mock_open(read_data="ALLOWED_IPS=127.0.0.1\n")
    ):
        spec.loader.exec_module(module)
    return module


class SsacliParserTests(unittest.TestCase):
    def test_parse_ssacli_records_creates_inventory_and_smart_fields(self):
        sidecar = load_sidecar()
        records = sidecar._parse_ssacli_records(FIXTURE.read_text())

        self.assertEqual(len(records), 2)
        first, second = records
        self.assertEqual(first["devpath"], "/dev/ssacli-slot-1-pd-1i-1-1")
        self.assertEqual(first["controller"], "Smart Array P420")
        self.assertEqual(first["controller_slot"], "1")
        self.assertEqual(first["location"], "1I:1:1")
        self.assertEqual(first["serial"], "DRIVE-SERIAL-1")
        self.assertEqual(first["wwn"], "DRIVE-WWN-1")
        self.assertEqual(first["model"], "HP MB1000FCWDE")
        self.assertEqual(first["firmware"], "HPD5")
        self.assertEqual(first["size"], 1_000_000_000_000)
        self.assertEqual(first["type"], "hdd")
        self.assertEqual(first["device_type"], "ssacli")
        self.assertFalse(first["exposed_to_os"])
        self.assertEqual(first["temperature_c"], 34)
        self.assertEqual(first["max_temperature_c"], 38)
        self.assertFalse(first["smart_available"])
        self.assertEqual(first["health_source"], "ssacli")
        self.assertTrue(first["controller_health_passed"])
        self.assertNotIn("smart_passed", first)
        self.assertEqual(second["status"], "Predictive Failure")
        self.assertFalse(second["controller_health_passed"])
        self.assertNotIn("smart_passed", second)

    def test_cached_ssacli_records_reuses_one_controller_query(self):
        sidecar = load_sidecar()
        parsed = sidecar._parse_ssacli_records(FIXTURE.read_text())

        with patch.object(sidecar, "_query_ssacli_records", return_value=parsed) as query, patch.object(
            sidecar.time, "monotonic", side_effect=[100.0, 100.0, 101.0]
        ):
            first = sidecar._cached_ssacli_records()
            second = sidecar._cached_ssacli_records()

        self.assertEqual(first, parsed)
        self.assertEqual(second, parsed)
        self.assertIsNot(first, second)
        query.assert_called_once_with()

    def test_cached_ssacli_records_backs_off_after_failed_refresh(self):
        sidecar = load_sidecar()
        old = sidecar._parse_ssacli_records(FIXTURE.read_text())
        setattr(sidecar, "_ssacli_records_cache", old)
        setattr(sidecar, "_ssacli_next_refresh", 0.0)
        setattr(sidecar, "_ssacli_last_error", None)

        with patch.object(
            sidecar,
            "_query_ssacli_records",
            side_effect=sidecar.SsacliSnapshotError("command failed"),
        ) as query, patch.object(sidecar.time, "monotonic", side_effect=[100.0, 108.0, 109.0]):
            with self.assertRaises(sidecar.SsacliSnapshotError):
                sidecar._cached_ssacli_records()
            with self.assertRaises(sidecar.SsacliSnapshotError):
                sidecar._cached_ssacli_records()

        query.assert_called_once_with()
        self.assertEqual(getattr(sidecar, "_ssacli_records_cache"), old)

    def test_ssacli_record_lookup_requires_an_exact_pseudo_path(self):
        sidecar = load_sidecar()
        parsed = sidecar._parse_ssacli_records(FIXTURE.read_text())

        with patch.object(sidecar, "_cached_ssacli_records", return_value=parsed):
            record = sidecar._ssacli_record_for_path(parsed[0]["devpath"])
            missing = sidecar._ssacli_record_for_path("/dev/ssacli-slot-1-pd-missing")
            ordinary = sidecar._ssacli_record_for_path("/dev/sda")

        self.assertEqual(record["serial"], "DRIVE-SERIAL-1")
        self.assertIsNone(missing)
        self.assertIsNone(ordinary)

    def test_trusted_ssacli_binary_rejects_group_writable_executable(self):
        sidecar = load_sidecar()
        executable = SimpleNamespace(
            st_mode=sidecar.stat.S_IFREG | 0o775,
            st_uid=0,
        )

        with patch.object(sidecar, "SSACLI_CANDIDATES", ("/unsafe/bin/ssacli",)), patch.object(
            sidecar.os.path, "lexists", return_value=True
        ), patch.object(sidecar.os.path, "realpath", side_effect=lambda value: value), patch.object(
            sidecar.os, "stat", return_value=executable
        ), patch.object(sidecar.os, "access", return_value=True), self.assertRaises(
            sidecar.SsacliSnapshotError
        ):
            sidecar._trusted_ssacli_binary()

    def test_trusted_ssacli_binary_rejects_writable_parent_directory(self):
        sidecar = load_sidecar()
        candidate = "/unsafe/bin/ssacli"

        def stat_result(path):
            if path == candidate:
                return SimpleNamespace(st_mode=sidecar.stat.S_IFREG | 0o755, st_uid=0)
            mode = 0o777 if path == "/unsafe/bin" else 0o755
            return SimpleNamespace(st_mode=sidecar.stat.S_IFDIR | mode, st_uid=0)

        with patch.object(sidecar, "SSACLI_CANDIDATES", (candidate,)), patch.object(
            sidecar.os.path, "lexists", return_value=True
        ), patch.object(sidecar.os.path, "realpath", return_value=candidate), patch.object(
            sidecar.os, "stat", side_effect=stat_result
        ), patch.object(sidecar.os, "access", return_value=True), self.assertRaises(
            sidecar.SsacliSnapshotError
        ):
            sidecar._trusted_ssacli_binary()

    def test_trusted_ssacli_binary_checks_allowlisted_symlink_parents(self):
        sidecar = load_sidecar()
        candidate = "/unsafe/bin/ssacli"
        resolved = "/safe/bin/ssacli"

        def stat_result(path):
            if path == resolved:
                return SimpleNamespace(st_mode=sidecar.stat.S_IFREG | 0o755, st_uid=0)
            mode = 0o777 if path == "/unsafe/bin" else 0o755
            return SimpleNamespace(st_mode=sidecar.stat.S_IFDIR | mode, st_uid=0)

        with patch.object(sidecar, "SSACLI_CANDIDATES", (candidate,)), patch.object(
            sidecar.os.path, "lexists", return_value=True
        ), patch.object(sidecar.os.path, "realpath", return_value=resolved), patch.object(
            sidecar.os, "stat", side_effect=stat_result
        ), patch.object(sidecar.os, "access", return_value=True), self.assertRaises(
            sidecar.SsacliSnapshotError
        ):
            sidecar._trusted_ssacli_binary()

    def test_query_ssacli_records_uses_fixed_read_only_command(self):
        sidecar = load_sidecar()
        completed = Mock(returncode=0, stdout=FIXTURE.read_text())

        with patch.object(sidecar, "_trusted_ssacli_binary", return_value="/usr/sbin/ssacli"), patch.object(
            sidecar.subprocess, "run", return_value=completed
        ) as run:
            records = sidecar._query_ssacli_records()

        self.assertEqual(len(records), 2)
        self.assertIn(
            "/opt/smartstorageadmin/ssacli/bin/ssacli",
            sidecar.SSACLI_CANDIDATES,
        )
        run.assert_called_once_with(
            ["/usr/sbin/ssacli", "ctrl", "all", "show", "config", "detail"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
            env={
                "LANG": "C",
                "LC_ALL": "C",
                "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
            },
        )

    def test_query_ssacli_records_raises_on_malformed_controller_snapshot(self):
        sidecar = load_sidecar()
        completed = Mock(
            returncode=0,
            stdout="Smart Array P420 in Slot 1\n   physicaldrive 1I:1:1\n      Status: OK\n",
        )

        with patch.object(sidecar, "_trusted_ssacli_binary", return_value="/usr/sbin/ssacli"), patch.object(
            sidecar.subprocess, "run", return_value=completed
        ):
            with self.assertRaises(sidecar.SsacliSnapshotError):
                sidecar._query_ssacli_records()

    def test_query_ssacli_records_rejects_empty_success_output(self):
        sidecar = load_sidecar()
        completed = Mock(returncode=0, stdout="")

        with patch.object(sidecar, "_trusted_ssacli_binary", return_value="/usr/sbin/ssacli"), patch.object(
            sidecar.subprocess, "run", return_value=completed
        ), self.assertRaises(sidecar.SsacliSnapshotError):
            sidecar._query_ssacli_records()

    def test_query_ssacli_records_rejects_controller_header_only(self):
        sidecar = load_sidecar()
        completed = Mock(returncode=0, stdout="Smart Array P420 in Slot 1\n")

        with patch.object(sidecar, "_trusted_ssacli_binary", return_value="/usr/sbin/ssacli"), patch.object(
            sidecar.subprocess, "run", return_value=completed
        ), self.assertRaises(sidecar.SsacliSnapshotError):
            sidecar._query_ssacli_records()

    def test_query_ssacli_records_rejects_truncated_second_controller(self):
        sidecar = load_sidecar()
        output = FIXTURE.read_text() + "\nSmart Array P420 in Slot 2\n"
        completed = Mock(returncode=0, stdout=output)

        self.assertEqual(sidecar._parse_ssacli_records(output), [])
        with patch.object(sidecar, "_trusted_ssacli_binary", return_value="/usr/sbin/ssacli"), patch.object(
            sidecar.subprocess, "run", return_value=completed
        ), self.assertRaises(sidecar.SsacliSnapshotError):
            sidecar._query_ssacli_records()

    def test_query_ssacli_records_raises_when_command_fails(self):
        sidecar = load_sidecar()
        completed = Mock(returncode=1, stdout=FIXTURE.read_text())

        with patch.object(sidecar, "_trusted_ssacli_binary", return_value="/usr/sbin/ssacli"), patch.object(
            sidecar.subprocess, "run", return_value=completed
        ):
            with self.assertRaises(sidecar.SsacliSnapshotError):
                sidecar._query_ssacli_records()

    def test_query_ssacli_records_raises_on_timeout(self):
        sidecar = load_sidecar()

        with patch.object(sidecar, "_trusted_ssacli_binary", return_value="/usr/sbin/ssacli"), patch.object(
            sidecar.subprocess, "run", side_effect=sidecar.subprocess.TimeoutExpired("ssacli", 8)
        ):
            with self.assertRaises(sidecar.SsacliSnapshotError):
                sidecar._query_ssacli_records()

    def test_query_ssacli_records_wraps_execution_error(self):
        sidecar = load_sidecar()

        with patch.object(sidecar, "_trusted_ssacli_binary", return_value="/usr/sbin/ssacli"), patch.object(
            sidecar.subprocess, "run", side_effect=OSError("cannot execute")
        ):
            with self.assertRaises(sidecar.SsacliSnapshotError):
                sidecar._query_ssacli_records()

    def test_query_ssacli_records_returns_empty_when_tool_is_missing(self):
        sidecar = load_sidecar()

        with patch.object(sidecar, "_trusted_ssacli_binary", return_value=None):
            self.assertEqual(sidecar._query_ssacli_records(), [])

    def test_parse_ssacli_records_requires_drive_exposure_state(self):
        sidecar = load_sidecar()
        fixture = FIXTURE.read_text().replace(
            "         Drive exposed to OS: False\n",
            "",
            1,
        )

        self.assertEqual(sidecar._parse_ssacli_records(fixture), [])

    def test_parse_ssacli_records_requires_authentication_state(self):
        sidecar = load_sidecar()
        fixture = FIXTURE.read_text().replace(
            "         Drive Authentication Status: OK\n",
            "",
            1,
        )

        self.assertEqual(sidecar._parse_ssacli_records(fixture), [])

    def test_parse_ssacli_records_accepts_not_applicable_authentication(self):
        sidecar = load_sidecar()
        fixture = FIXTURE.read_text().replace(
            "         Drive Authentication Status: OK\n",
            "         Drive Authentication Status: Not Applicable\n",
            1,
        )

        records = sidecar._parse_ssacli_records(fixture)

        self.assertTrue(records[0]["controller_health_passed"])
        self.assertNotIn("smart_passed", records[0])

    def test_parse_ssacli_records_does_not_guess_ssd_without_evidence(self):
        sidecar = load_sidecar()
        fixture = FIXTURE.read_text().replace(
            "         Rotational Speed: 7200\n",
            "",
            1,
        )

        records = sidecar._parse_ssacli_records(fixture)

        self.assertEqual(records[0]["type"], "unknown")
        self.assertEqual(records[1]["type"], "hdd")

    def test_parse_ssacli_records_supports_hpe_embedded_controller_header(self):
        sidecar = load_sidecar()
        fixture = FIXTURE.read_text().replace(
            "Smart Array P420 in Slot 1",
            "HPE Smart Array P420 in Slot 0 (Embedded)",
        )

        records = sidecar._parse_ssacli_records(fixture)

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["controller"], "HPE Smart Array P420")
        self.assertEqual(records[0]["controller_slot"], "0 (Embedded)")
        self.assertTrue(records[0]["devpath"].startswith(
            "/dev/ssacli-slot-0-embedded-pd-"
        ))

    def test_parse_ssacli_records_rejects_partial_snapshot(self):
        sidecar = load_sidecar()
        fixture = FIXTURE.read_text().replace(
            "         Serial Number: DRIVE-SERIAL-2\n",
            "",
        ).replace(
            "         WWID: DRIVE-WWN-2\n",
            "",
        )

        self.assertEqual(sidecar._parse_ssacli_records(fixture), [])

    def test_parse_ssacli_records_accepts_array_summary_drive_lines(self):
        sidecar = load_sidecar()
        fixture = FIXTURE.read_text().replace(
            "      physicaldrive 1I:1:1",
            "      physicaldrive 1I:1:1 (port 1I:box 1:bay 1, SAS HDD, 1 TB, OK)\n"
            "      physicaldrive 1I:1:1",
            1,
        )

        self.assertEqual(len(sidecar._parse_ssacli_records(fixture)), 2)

    def test_parse_ssacli_records_rejects_malformed_drive_header_after_valid_drive(self):
        sidecar = load_sidecar()
        fixture = FIXTURE.read_text().replace(
            "      physicaldrive 1I:1:2",
            "      physicaldrive 1I:1:2 unexpected",
            1,
        )

        self.assertEqual(sidecar._parse_ssacli_records(fixture), [])

    def test_parse_ssacli_records_rejects_duplicate_fields(self):
        sidecar = load_sidecar()
        fixture = FIXTURE.read_text().replace(
            "         Serial Number: DRIVE-SERIAL-1",
            "         Serial Number: DRIVE-SERIAL-1\n"
            "         Serial Number: CONFLICTING-SERIAL",
            1,
        )

        self.assertEqual(sidecar._parse_ssacli_records(fixture), [])

        fixture = FIXTURE.read_text().replace(
            "         Rotational Speed: 7200",
            "         Rotational Speed: N/A\n"
            "         Rotational Speed: 0",
            1,
        )
        self.assertEqual(sidecar._parse_ssacli_records(fixture), [])

    def test_parse_ssacli_records_rejects_complete_prefix_of_snapshot(self):
        sidecar = load_sidecar()
        fixture = FIXTURE.read_text().split("\n      physicaldrive 1I:1:2\n", 1)[0]

        self.assertEqual(sidecar._parse_ssacli_records(fixture), [])

    def test_parse_ssacli_records_rejects_empty_selector_components(self):
        sidecar = load_sidecar()

        for fixture in (
            FIXTURE.read_text().replace("Smart Array P420 in Slot 1", "Smart Array P420 in Slot ---"),
            FIXTURE.read_text().replace("1I:1:1", "---"),
        ):
            self.assertEqual(sidecar._parse_ssacli_records(fixture), [])

    def test_parse_ssacli_records_rejects_unbounded_capacity(self):
        sidecar = load_sidecar()
        fixture = FIXTURE.read_text().replace(
            "         Size: 1 TB",
            "         Size: 999999999999999999999999 EB",
            1,
        )

        self.assertEqual(sidecar._parse_ssacli_records(fixture), [])

    def test_parse_ssacli_records_rejects_duplicate_hardware_identity(self):
        sidecar = load_sidecar()
        fixture = FIXTURE.read_text().replace("DRIVE-WWN-2", "DRIVE-WWN-1")

        self.assertEqual(sidecar._parse_ssacli_records(fixture), [])

        fixture = FIXTURE.read_text().replace("DRIVE-SERIAL-2", "DRIVE-SERIAL-1")
        self.assertEqual(sidecar._parse_ssacli_records(fixture), [])

    def test_parse_ssacli_records_rejects_placeholder_identity(self):
        sidecar = load_sidecar()
        fixture = FIXTURE.read_text().replace("DRIVE-SERIAL-1", "N/A").replace(
            "DRIVE-WWN-1", "0x0000000000000000"
        )

        self.assertEqual(sidecar._parse_ssacli_records(fixture), [])

        for placeholder in (
            "null", "not specified", "to be filled by o.e.m.", "123456789",
            "not available", "na", "serialnumber", "N / A", "!!UNKNOWN!!",
            "NOT-AVAILABLE", "SERIAL NUMBER",
        ):
            fixture = FIXTURE.read_text().replace(
                "DRIVE-SERIAL-1", placeholder
            ).replace("DRIVE-WWN-1", placeholder)
            self.assertEqual(sidecar._parse_ssacli_records(fixture), [])


class SsacliHandlerTests(unittest.TestCase):
    def test_global_smart_returns_http_error_when_ssacli_refresh_fails(self):
        sidecar = load_sidecar()
        handler = object.__new__(sidecar.Handler)
        handler._send_json_response = Mock()
        handler._send_error_response = Mock()

        with patch.object(
            sidecar,
            "_cached_ssacli_records",
            side_effect=sidecar.SsacliSnapshotError("command failed"),
        ), patch.object(sidecar.subprocess, "run", return_value=Mock(returncode=0, stdout="")):
            handler._handle_smart()

        handler._send_error_response.assert_called_once()
        handler._send_json_response.assert_not_called()

    def test_get_disks_route_calls_inventory_handler(self):
        sidecar = load_sidecar()
        handler = object.__new__(sidecar.Handler)
        handler.client_address = ("127.0.0.1", 12345)
        handler.path = "/disks"
        handler._handle_disks = Mock()
        handler.send_response = Mock()
        handler.end_headers = Mock()

        handler.do_GET()

        handler._handle_disks.assert_called_once_with()
        handler.send_response.assert_not_called()

    def test_disks_endpoint_returns_ssacli_inventory(self):
        sidecar = load_sidecar()
        records = sidecar._parse_ssacli_records(FIXTURE.read_text())
        handler = object.__new__(sidecar.Handler)
        handler._send_json_response = Mock()

        with patch.object(sidecar, "_cached_ssacli_records", return_value=records):
            handler._handle_disks()

        payload = json.loads(handler._send_json_response.call_args.args[0])
        self.assertEqual([disk["devpath"] for disk in payload], [
            "/dev/ssacli-slot-1-pd-1i-1-1",
            "/dev/ssacli-slot-1-pd-1i-1-2",
        ])
        self.assertEqual(payload[0]["serial"], "DRIVE-SERIAL-1")

    def test_disks_endpoint_omits_drives_exposed_to_the_os(self):
        sidecar = load_sidecar()
        fixture = FIXTURE.read_text().replace(
            "         Drive exposed to OS: False\n",
            "         Drive exposed to OS: True\n",
            1,
        )
        records = sidecar._parse_ssacli_records(fixture)
        handler = object.__new__(sidecar.Handler)
        handler._send_json_response = Mock()

        with patch.object(sidecar, "_cached_ssacli_records", return_value=records):
            handler._handle_disks()

        payload = json.loads(handler._send_json_response.call_args.args[0])
        self.assertEqual(
            [disk["serial"] for disk in payload],
            ["DRIVE-SERIAL-2"],
        )

    def test_disks_endpoint_returns_http_error_when_snapshot_refresh_fails(self):
        sidecar = load_sidecar()
        handler = object.__new__(sidecar.Handler)
        handler._send_json_response = Mock()
        handler._send_error_response = Mock()

        with patch.object(
            sidecar,
            "_cached_ssacli_records",
            side_effect=sidecar.SsacliSnapshotError("command failed"),
        ):
            handler._handle_disks()

        handler._send_error_response.assert_called_once_with(
            "ssacli inventory unavailable"
        )
        handler._send_json_response.assert_not_called()

    def test_health_summary_counts_healthy_ssacli_controller_records(self):
        sidecar = load_sidecar()
        record = sidecar._parse_ssacli_records(FIXTURE.read_text())[0]
        handler = object.__new__(sidecar.Handler)

        with patch.object(
            handler,
            "_get_smart_data_fast",
            return_value={"ssacli-slot-1-pd-1i-1-1": record},
        ):
            summary = handler._get_disk_health_summary()

        self.assertEqual(summary, {"working": 1, "failed": 0, "total": 1})

    def test_global_smart_data_includes_ssacli_records_when_smartctl_scan_is_empty(self):
        sidecar = load_sidecar()
        records = sidecar._parse_ssacli_records(FIXTURE.read_text())
        handler = object.__new__(sidecar.Handler)
        completed = Mock(returncode=0, stdout="")

        with patch.object(sidecar.subprocess, "run", return_value=completed), patch.object(
            sidecar, "_cached_ssacli_records", return_value=records
        ), patch.object(handler, "_get_disk_info_safe", return_value=None):
            smart = handler._get_smart_data_fast()

        self.assertEqual(set(smart), {
            "ssacli-slot-1-pd-1i-1-1",
            "ssacli-slot-1-pd-1i-1-2",
        })
        self.assertEqual(smart["ssacli-slot-1-pd-1i-1-1"]["temperature_c"], 34)

    def test_global_smart_data_omits_drives_exposed_to_the_os(self):
        sidecar = load_sidecar()
        fixture = FIXTURE.read_text().replace(
            "         Drive exposed to OS: False\n",
            "         Drive exposed to OS: True\n",
            1,
        )
        records = sidecar._parse_ssacli_records(fixture)
        handler = object.__new__(sidecar.Handler)
        completed = Mock(returncode=0, stdout="")

        with patch.object(sidecar.subprocess, "run", return_value=completed), patch.object(
            sidecar, "_cached_ssacli_records", return_value=records
        ), patch.object(handler, "_get_disk_info_safe", return_value=None):
            smart = handler._get_smart_data_fast()

        self.assertEqual(set(smart), {"ssacli-slot-1-pd-1i-1-2"})

    def test_extended_smart_does_not_run_smartctl_for_ssacli_pseudo_paths(self):
        sidecar = load_sidecar()
        records = sidecar._parse_ssacli_records(FIXTURE.read_text())
        handler = object.__new__(sidecar.Handler)
        smart = {
            record["devpath"].removeprefix("/dev/"): record
            for record in records
        }

        with patch.object(handler, "_get_smart_data_fast", return_value=smart), patch.object(
            handler, "_get_detailed_smart_attributes"
        ) as detailed:
            result = handler._get_smart_data_extended()

        self.assertEqual(result, smart)
        detailed.assert_not_called()

    def test_smart_disk_returns_http_error_when_ssacli_refresh_fails(self):
        sidecar = load_sidecar()
        handler = object.__new__(sidecar.Handler)
        handler.path = "/smart-disk?" + urlencode(
            {"path": "/dev/ssacli-slot-1-pd-1i-1-1", "protect": 1}
        )
        handler._send_json_response = Mock()
        handler._send_error_response = Mock()

        with patch.object(
            sidecar,
            "_ssacli_record_for_path",
            side_effect=sidecar.SsacliSnapshotError("command failed"),
        ):
            handler._handle_smart_disk()

        handler._send_error_response.assert_called_once_with(
            "ssacli inventory unavailable"
        )
        handler._send_json_response.assert_not_called()

    def test_smart_disk_returns_cached_ssacli_record_for_pseudo_path(self):
        sidecar = load_sidecar()
        record = sidecar._parse_ssacli_records(FIXTURE.read_text())[0]
        handler = object.__new__(sidecar.Handler)
        handler.path = "/smart-disk?" + urlencode(
            {"path": record["devpath"], "protect": 1}
        )
        handler._send_json_response = Mock()
        handler._send_error_response = Mock()

        with patch.object(sidecar, "_ssacli_record_for_path", return_value=record):
            handler._handle_smart_disk()

        payload = json.loads(handler._send_json_response.call_args.args[0])
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["data"]["serial"], "DRIVE-SERIAL-1")
        handler._send_error_response.assert_not_called()


if __name__ == "__main__":
    unittest.main()
