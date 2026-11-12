#!/usr/bin/env python3
import json
import os
import subprocess
import re
import hashlib
import math
import shutil
import threading
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import stat
from urllib.parse import parse_qs, urlsplit

CONFIG_PATH = "/etc/proxmox-sensors/sidecar.conf"


def load_allowed_ips():
    """Load and validate the allowed client IP list from the sidecar config."""
    if not os.path.exists(CONFIG_PATH):
        raise RuntimeError(f"Missing sidecar configuration: {CONFIG_PATH}")

    allowed = []
    with open(CONFIG_PATH, "r", encoding="utf-8") as config_file:
        for raw_line in config_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "ALLOWED_IPS":
                for item in value.split(","):
                    candidate = item.strip()
                    if not candidate:
                        continue
                    allowed.append(str(ipaddress.ip_address(candidate)))

    if not allowed:
        raise RuntimeError("ALLOWED_IPS is missing or empty")

    return frozenset(allowed)


ALLOWED_IPS = load_allowed_ips()

STORCLI_CANDIDATES = (
    "storcli64", "storcli", "/opt/MegaRAID/storcli/storcli64",
    "/usr/local/sbin/storcli64",
)
SSACLI_CANDIDATES = (
    "/usr/sbin/ssacli",
    "/usr/sbin/hpssacli",
    "/opt/smartstorageadmin/ssacli/bin/ssacli",
)
SSACLI_DEVICE_PREFIX = "/dev/ssacli-"


class SsacliSnapshotError(RuntimeError):
    """The controller inventory could not be refreshed safely."""


def _parse_ssacli_size(value):
    """Convert an SSA capacity such as '1 TB' to decimal bytes."""
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([KMGTPE]?B)\s*", value or "", re.I)
    if not match:
        return None
    powers = {unit: exponent for exponent, unit in enumerate(("B", "KB", "MB", "GB", "TB", "PB", "EB"))}
    try:
        amount = float(match.group(1))
        size = int(amount * (1000 ** powers[match.group(2).upper()]))
    except (OverflowError, ValueError):
        return None
    return size if math.isfinite(amount) and 0 < size < 10**18 else None


def _ssacli_component(value):
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _ssacli_identity_value(value):
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    candidate = re.sub(r"[^a-z0-9]", "", cleaned.casefold().removeprefix("0x"))
    invalid = {
        "", "unknown", "none", "null", "na", "notavailable", "notspecified",
        "tobefilledbyoem", "serialnumber", "123456789",
    }
    if candidate in invalid or not candidate or re.fullmatch(r"0+", candidate):
        return None
    return cleaned


def _ssacli_identity_key(kind, value):
    value = _ssacli_identity_value(value)
    if value is None:
        return None
    if kind == "wwn":
        return re.sub(r"[^a-z0-9]", "", value.casefold().removeprefix("0x"))
    return value.casefold()


def _parse_ssacli_records(output):
    """Parse fixed `ssacli ctrl all show config detail` output."""
    records = []
    controller = None
    slot = None
    current = None
    invalid = False
    controllers_seen = set()
    summary_locations = set()
    detail_locations = set()

    def finish():
        nonlocal current, invalid
        if not current:
            return
        serial = _ssacli_identity_value(current.get("serial"))
        wwn = _ssacli_identity_value(current.get("wwn"))
        size = _parse_ssacli_size(current.get("size_text"))
        location = current.get("location")
        exposure = current.get("exposed_to_os")
        status = current.get("status")
        authentication = current.get("authentication_status")
        if (not location or not slot or not (serial or wwn) or size is None
                or not isinstance(exposure, str)
                or exposure.casefold() not in ("true", "false")
                or not isinstance(status, str) or not status.strip()
                or not isinstance(authentication, str) or not authentication.strip()):
            invalid = True
            current = None
            return
        slot_component = _ssacli_component(slot)
        location_component = _ssacli_component(location)
        if not slot_component or not location_component:
            invalid = True
            current = None
            return
        path = (
            f"{SSACLI_DEVICE_PREFIX}slot-{slot_component}-"
            f"pd-{location_component}"
        )
        rotational = current.get("rotational_speed")
        if isinstance(rotational, (int, float)) and rotational > 0:
            disk_type = "hdd"
        elif rotational == 0:
            disk_type = "ssd"
        else:
            disk_type = "unknown"
        model = re.sub(r"\s+", " ", current.get("model", "Unknown")).strip()
        controller_health_passed = (
            status.casefold() == "ok"
            and authentication.casefold() in ("ok", "not applicable", "n/a")
        )
        exposed_to_os = exposure.casefold() == "true"
        record = {
            "devpath": path,
            "path": path,
            "controller": controller,
            "controller_slot": slot,
            "location": location,
            "vendor": "HPE",
            "model": model,
            "serial": serial or "",
            "wwn": wwn or "",
            "firmware": current.get("firmware", "Unknown"),
            "size": size,
            "capacity_gb": round(size / (1024**3), 1),
            "type": disk_type,
            "device_type": "ssacli",
            "exposed_to_os": exposed_to_os,
            "status": status,
            "health_source": "ssacli",
            "controller_health_passed": controller_health_passed,
            "smart_available": False,
            "temperature_c": current.get("temperature_c"),
            "max_temperature_c": current.get("max_temperature_c"),
            "power_on_hours": current.get("power_on_hours"),
            "returncode": 0,
            "reallocated_sectors": None,
            "pending_sectors": None,
            "uncorrectable_errors": None,
            "media_errors": None,
            "spin_retry_count": None,
            "seek_error_rate": None,
        }
        records.append(record)
        current = None

    field_map = {
        "status": "status",
        "interface type": "interface_type",
        "size": "size_text",
        "drive exposed to os": "exposed_to_os",
        "rotational speed": "rotational_speed",
        "firmware revision": "firmware",
        "serial number": "serial",
        "wwid": "wwn",
        "model": "model",
        "current temperature (c)": "temperature_c",
        "maximum temperature (c)": "max_temperature_c",
        "power on hours": "power_on_hours",
        "drive authentication status": "authentication_status",
    }
    integer_fields = {
        "rotational_speed", "temperature_c", "max_temperature_c", "power_on_hours"
    }

    for line in (output or "").splitlines():
        controller_match = re.match(
            r"^\s*((?:HPE\s+)?Smart Array .+?) in Slot\s+(.+?)\s*$", line
        )
        if controller_match:
            finish()
            controller, slot = controller_match.groups()
            controllers_seen.add((controller.casefold(), slot.casefold()))
            continue
        summary_drive_match = re.match(
            r"^\s*physicaldrive\s+([A-Za-z0-9:._-]+)\s+\(port\s+[^)\r\n]+\)\s*$",
            line,
            re.I,
        )
        if summary_drive_match:
            if not controller or not slot:
                invalid = True
            else:
                summary_locations.add((
                    controller.casefold(), slot.casefold(),
                    summary_drive_match.group(1).casefold(),
                ))
            continue
        drive_match = re.match(r"^\s*physicaldrive\s+([A-Za-z0-9:._-]+)\s*$", line)
        if line.strip().casefold().startswith("physicaldrive"):
            finish()
            if not drive_match:
                invalid = True
                current = None
                continue
            if not controller or not slot:
                invalid = True
                current = None
                continue
            location = drive_match.group(1)
            detail_locations.add((
                controller.casefold(), slot.casefold(), location.casefold(),
            ))
            current = {"location": location, "_seen_fields": set()}
            continue
        if current is not None and line.strip():
            indentation = len(line) - len(line.lstrip())
            if indentation <= 6:
                finish()
        if current is None:
            continue
        field_match = re.match(r"^\s*([^:]+):\s*(.*?)\s*$", line)
        if not field_match:
            continue
        label, value = field_match.groups()
        target = field_map.get(label.strip().casefold())
        if not target:
            continue
        if target in current["_seen_fields"]:
            invalid = True
            continue
        current["_seen_fields"].add(target)
        if target in integer_fields:
            number = re.search(r"-?\d+", value)
            if number:
                current[target] = int(number.group())
        else:
            current[target] = value.strip()
    finish()
    if invalid:
        return []
    summary_controllers = {location[:2] for location in summary_locations}
    if (records and (
            not summary_locations
            or summary_locations != detail_locations
            or controllers_seen != summary_controllers
    )):
        return []
    paths = [record["devpath"] for record in records]
    identities = {
        kind: [
            key for record in records
            if (key := _ssacli_identity_key(kind, record.get(kind))) is not None
        ]
        for kind in ("wwn", "serial")
    }
    if (len(set(paths)) != len(paths)
            or any(len(values) != len(set(values)) for values in identities.values())):
        return []
    return records


def _trusted_ssacli_parent_chain(path):
    if not os.path.isabs(path):
        return False
    parent = os.path.dirname(path)
    while parent:
        try:
            parent_info = os.stat(parent)
        except OSError:
            return False
        if (not stat.S_ISDIR(parent_info.st_mode)
                or parent_info.st_uid != 0
                or parent_info.st_mode & 0o022):
            return False
        if parent == os.path.sep:
            return True
        parent = os.path.dirname(parent)
    return False


def _trusted_ssacli_binary():
    unsafe_found = False
    for candidate in SSACLI_CANDIDATES:
        if not os.path.lexists(candidate):
            continue
        unsafe_found = True
        resolved = os.path.realpath(candidate)
        try:
            info = os.stat(resolved)
            trusted_file = (
                stat.S_ISREG(info.st_mode)
                and info.st_uid == 0
                and not info.st_mode & 0o022
                and os.access(resolved, os.X_OK)
            )
        except OSError:
            continue
        if (trusted_file
                and _trusted_ssacli_parent_chain(candidate)
                and _trusted_ssacli_parent_chain(resolved)):
            return resolved
    if unsafe_found:
        raise SsacliSnapshotError("ssacli executable path is not trusted")
    return None


def _query_ssacli_records():
    binary = _trusted_ssacli_binary()
    if not binary:
        return []
    try:
        result = subprocess.run(
            [binary, "ctrl", "all", "show", "config", "detail"],
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
    except subprocess.TimeoutExpired as err:
        raise SsacliSnapshotError("ssacli inventory command timed out") from err
    except OSError as err:
        raise SsacliSnapshotError("ssacli inventory command could not run") from err
    if result.returncode != 0:
        raise SsacliSnapshotError("ssacli inventory command failed")
    output = result.stdout or ""
    if not output.strip():
        raise SsacliSnapshotError("ssacli inventory output is empty")
    records = _parse_ssacli_records(output)
    has_drive_markers = any(
        line.strip().casefold().startswith("physicaldrive")
        for line in output.splitlines()
    )
    has_controller = any(
        re.match(r"^\s*((?:HPE\s+)?Smart Array .+?) in Slot\s+(.+?)\s*$", line)
        for line in output.splitlines()
    )
    no_controller = bool(re.search(r"\bno\s+controllers?\b", output, re.I))
    if ((has_drive_markers and not records)
            or (has_controller and not records)
            or (not records and not no_controller)):
        raise SsacliSnapshotError("ssacli inventory is malformed or ambiguous")
    return records


_ssacli_lock = threading.Lock()
_ssacli_records_cache = []
_ssacli_next_refresh = 0.0
_ssacli_last_error = None


def _cached_ssacli_records():
    global _ssacli_records_cache, _ssacli_next_refresh, _ssacli_last_error
    with _ssacli_lock:
        now = time.monotonic()
        if now < _ssacli_next_refresh:
            if _ssacli_last_error is not None:
                raise _ssacli_last_error
            return [dict(record) for record in _ssacli_records_cache]
        try:
            records = _query_ssacli_records()
        except SsacliSnapshotError as err:
            _ssacli_last_error = err
            _ssacli_next_refresh = time.monotonic() + 5
            raise
        _ssacli_records_cache = records
        _ssacli_last_error = None
        _ssacli_next_refresh = time.monotonic() + 30
        return [dict(record) for record in _ssacli_records_cache]


def _ssacli_record_for_path(path):
    if not isinstance(path, str) or not path.startswith(SSACLI_DEVICE_PREFIX):
        return None
    matches = [record for record in _cached_ssacli_records() if record.get("devpath") == path]
    return dict(matches[0]) if len(matches) == 1 else None


_hba_lock = threading.Lock()
_hba_temps = {}
_hba_next_refresh = 0.0
_hba_refreshing = False


def _controller_identities(payload):
    """Return only controllers with a unique, persistent hardware identifier."""
    controllers = payload.get("Controllers") if isinstance(payload, dict) else None
    if not isinstance(controllers, list):
        return {}
    found = {}
    used = set()
    for controller in controllers:
        if not isinstance(controller, dict):
            continue
        status = controller.get("Command Status")
        data = controller.get("Response Data")
        if not isinstance(status, dict) or not isinstance(data, dict):
            continue
        if status.get("Status") != "Success":
            continue
        index = status.get("Controller")
        basics = data.get("Basics")
        if isinstance(index, bool) or not isinstance(index, int) or not isinstance(basics, dict):
            continue
        identity = next(
            (f"{field}:{value.strip().casefold()}"
             for field in ("SAS Address", "Serial Number")
             if isinstance(value := basics.get(field), str)
             and value.strip().casefold() not in ("", "n/a", "unknown", "none", "0")
             and set(value.strip()) != {"0"}),
            None,
        )
        if identity is None or index in found or identity in used:
            return {}
        found[index] = identity
        used.add(identity)
    return found


def _controller_temperatures(output):
    found = {}
    controller = None
    for line in output.splitlines():
        match = re.match(r"^\s*Controller\s*=\s*(\d+)\s*$", line)
        if match:
            controller = int(match.group(1))
            continue
        status = re.match(r"^\s*Status\s*=\s*(\S+)", line)
        if status and status.group(1) != "Success":
            return {}
        match = re.search(
            r"ROC temperature\(Degree Celsius\)\s*(?:=\s*)?(-?\d+(?:\.\d+)?)\b",
            line,
        )
        if match and controller is not None:
            value = float(match.group(1))
            if controller in found or not math.isfinite(value) or not 1 < value < 145:
                return {}
            found[controller] = value
    return found


def _refresh_hba_temps():
    global _hba_temps, _hba_next_refresh, _hba_refreshing
    temperatures = {}
    try:
        binary = next((path for candidate in STORCLI_CANDIDATES
                       if (path := shutil.which(candidate))), None)
        if binary:
            metadata = subprocess.run(
                [binary, "/call", "show", "all", "J"],
                capture_output=True, text=True, timeout=10, check=False,
            )
            readings = subprocess.run(
                [binary, "/call", "show", "temperature"],
                capture_output=True, text=True, timeout=10, check=False,
            )
            if metadata.returncode == 0 and readings.returncode == 0:
                identities = _controller_identities(json.loads(metadata.stdout))
                for index, value in _controller_temperatures(readings.stdout).items():
                    if identity := identities.get(index):
                        key = hashlib.sha256(identity.encode()).hexdigest()[:16]
                        temperatures[f"storcli-hba-{key}"] = {
                            "Adapter": "LSI/Broadcom HBA",
                            "ROC temperature": {"temp1_input": value},
                        }
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    finally:
        with _hba_lock:
            _hba_temps = temperatures
            _hba_next_refresh = time.monotonic() + 90
            _hba_refreshing = False


def _cached_hba_temps():
    global _hba_refreshing
    with _hba_lock:
        if not _hba_refreshing and time.monotonic() >= _hba_next_refresh:
            _hba_refreshing = True
            try:
                threading.Thread(target=_refresh_hba_temps, daemon=True).start()
            except RuntimeError:
                _hba_refreshing = False
        return dict(_hba_temps)


class Handler(BaseHTTPRequestHandler):
    def _client_is_allowed(self):
        return self.client_address[0] in ALLOWED_IPS

    def _send_forbidden(self):
        payload = json.dumps({"error": "forbidden"})
        self.send_response(403)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload.encode())))
        self.end_headers()
        self.wfile.write(payload.encode())

    def do_GET(self):
        if not self._client_is_allowed():
            self._send_forbidden()
            return
        if self.path == "/disks":
            self._handle_disks()
        elif self.path == "/sensors":
            self._handle_sensors()
        elif self.path == "/smart":
            self._handle_smart()
        elif self.path.startswith("/smart-disk?"):
            self._handle_smart_disk()
        elif self.path == "/smart-extended":
            self._handle_smart_extended()
        elif self.path == "/memory":
            self._handle_memory()
        elif self.path == "/health":
            self._handle_health()
        elif self.path == "/mounts":
            self._handle_mounts()
        elif self.path == "/ksm":
            self._handle_ksm()
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_disks(self):
        """Return controller-backed physical disk inventory."""
        try:
            records = _cached_ssacli_records()
        except SsacliSnapshotError:
            self._send_error_response("ssacli inventory unavailable")
            return
        records = [record for record in records if not record.get("exposed_to_os")]
        self._send_json_response(json.dumps(records))

    def _handle_sensors(self):
        """Handle lm-sensors data."""
        try:
            data = subprocess.check_output(["sensors", "-j"], timeout=5)
            hba = _cached_hba_temps()
            if hba:
                try:
                    sensors = json.loads(data)
                    if isinstance(sensors, dict) and not any(
                        chip.lower().startswith("mpt3sas") for chip in sensors
                    ):
                        for chip, values in hba.items():
                            if chip not in sensors:
                                sensors[chip] = values
                        data = json.dumps(sensors).encode()
                except (ValueError, TypeError):
                    pass
            self._send_json_response(data)
        except Exception as e:
            self._send_error_response(f"Error getting sensors: {e}")

    def _handle_smart(self):
        """Handle SMART data - optimized version."""
        try:
            smart_data = self._get_smart_data_fast()
            self._send_json_response(json.dumps(smart_data))
        except Exception as e:
            self._send_error_response(f"Error getting SMART data: {e}")

    def _handle_smart_disk(self):
        """Query one inventory-selected block device, without a global scan."""
        query = parse_qs(urlsplit(self.path).query)
        paths = query.get("path", [])
        protect = query.get("protect", [])
        if len(paths) != 1 or protect not in (["0"], ["1"]):
            self._send_error_response("Invalid SMART disk request")
            return
        path = paths[0]
        if not re.fullmatch(r"/dev/[A-Za-z0-9_./-]+", path) or ".." in path.split("/"):
            self._send_error_response("Invalid block device path")
            return
        if path.startswith(SSACLI_DEVICE_PREFIX):
            try:
                record = _ssacli_record_for_path(path)
            except SsacliSnapshotError:
                self._send_error_response("ssacli inventory unavailable")
                return
            payload = {"status": "ok", "data": record} if record else {"status": "error"}
            self._send_json_response(json.dumps(payload))
            return
        try:
            if not stat.S_ISBLK(os.stat(path).st_mode):
                self._send_error_response("Path is not a block device")
                return
            command = ["smartctl"]
            if protect == ["1"]:
                command.extend(("-n", "standby,3,5"))
            command.extend(("-a", "-j", path))
            result = subprocess.run(command, capture_output=True, text=True, timeout=7)
            if protect == ["1"] and result.returncode in (3, 5):
                status = "standby" if result.returncode == 3 else "unsupported"
                self._send_json_response(json.dumps({"status": status}))
                return
            try:
                raw = json.loads(result.stdout)
            except ValueError:
                raw = None
            smartctl_info = raw.get("smartctl") if isinstance(raw, dict) else None
            messages = smartctl_info.get("messages") if isinstance(smartctl_info, dict) else None
            unknown_usb_bridge = "Unknown USB bridge" in (result.stderr or "") or any(
                isinstance(message, dict) and isinstance(message.get("string"), str)
                and "Unknown USB bridge" in message["string"]
                for message in (messages if isinstance(messages, list) else [])
            )
            if result.returncode and unknown_usb_bridge and not (
                isinstance(raw, dict) and isinstance(raw.get("smart_status"), dict)
            ):
                sat_command = command[:-3] + ["-d", "sat"] + command[-3:]
                result = subprocess.run(sat_command, capture_output=True, text=True, timeout=7)
                if protect == ["1"] and result.returncode in (3, 5):
                    status = "standby" if result.returncode == 3 else "unsupported"
                    self._send_json_response(json.dumps({"status": status}))
                    return
                raw = json.loads(result.stdout)
            if (not isinstance(raw, dict)
                    or not isinstance(raw.get("smart_status"), dict)
                    or type(raw["smart_status"].get("passed")) is not bool):
                self._send_json_response(json.dumps({"status": "error"}))
                return
            parsed = self._parse_smart_info(raw, result.returncode)
            self._send_json_response(json.dumps({"status": "ok", "data": parsed}))
        except (OSError, ValueError, subprocess.TimeoutExpired):
            self._send_json_response(json.dumps({"status": "error"}))

    def _handle_smart_extended(self):
        """Extended SMART data with more details."""
        try:
            smart_data = self._get_smart_data_extended()
            self._send_json_response(json.dumps(smart_data))
        except Exception as e:
            self._send_error_response(f"Error: {e}")

    def _handle_memory(self):
        """Handle memory information from dmidecode."""
        try:
            cmd = ["dmidecode", "-t", "memory"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10, check=False
            )

            if result.returncode != 0:
                self._send_error_response(f"dmidecode failed: {result.stderr}")
                return

            memory_data = []
            current_module = {}

            for line in result.stdout.split("\n"):
                if "Memory Device" in line and "Array" not in line:
                    if current_module:
                        memory_data.append(current_module)
                    current_module = {}

                if "Locator:" in line and "Bank" not in line:
                    current_module["locator"] = line.split(":", 1)[1].strip()
                elif (
                    line.strip().startswith("Size:")
                    and "No Module Installed" not in line
                ):
                    current_module["size"] = line.split(":", 1)[1].strip()
                elif "Type:" in line and "Unknown" not in line:
                    current_module["type"] = line.split(":", 1)[1].strip()
                elif (
                    "Speed:" in line
                    and "Configured" not in line
                    and "Unknown" not in line
                ):
                    current_module["speed"] = line.split(":", 1)[1].strip()
                elif "Configured Memory Speed:" in line:
                    current_module["configured_speed"] = line.split(":", 1)[1].strip()
                elif "Manufacturer:" in line and "NO DIMM" not in line:
                    current_module["manufacturer"] = line.split(":", 1)[1].strip()

            if current_module:
                memory_data.append(current_module)

            memory_data = [
                m
                for m in memory_data
                if m.get("size") and "No Module Installed" not in m.get("size", "")
            ]

            total_gb = 0
            for module in memory_data:
                size_str = module.get("size", "0")
                if "GB" in size_str:
                    total_gb += int(size_str.replace("GB", "").strip())
                elif "MB" in size_str:
                    total_gb += int(size_str.replace("MB", "").strip()) / 1024

            result_data = {
                "modules": memory_data,
                "total_modules": len(memory_data),
                "total_gb": round(total_gb, 1),
                "timestamp": subprocess.check_output(["date", "+%s"]).decode().strip(),
            }

            self._send_json_response(json.dumps(result_data, indent=2))

        except subprocess.TimeoutExpired:
            self._send_error_response("dmidecode timeout (10s)")
        except Exception as e:
            self._send_error_response(f"Error getting memory info: {e}")

    def _handle_health(self):
        """Return health status."""
        try:
            sensors_ok = self._check_sensors()
            smart_ok = self._check_smartctl()
            disks = self._get_disk_health_summary()

            health_data = {
                "status": "healthy" if sensors_ok and smart_ok else "degraded",
                "sensors": sensors_ok,
                "smartctl": smart_ok,
                "disks_working": disks["working"],
                "disks_failed": disks["failed"],
                "disks_total": disks["total"],
                "timestamp": subprocess.check_output(["date", "+%s"]).decode().strip(),
            }
            self._send_json_response(json.dumps(health_data))
        except Exception as e:
            self._send_error_response(f"Error: {e}")

    def _handle_mounts(self):
        """Handle disk mount status via lsblk."""
        try:
            result = subprocess.run(
                ["lsblk", "-J", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,LABEL,UUID"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                self._send_error_response(f"lsblk failed: {result.stderr}")
                return

            raw = json.loads(result.stdout)
            mounted = []
            unmounted = []

            def _walk(devices, parent=None):
                for dev in devices or []:
                    name = dev.get("name", "")
                    dtype = dev.get("type", "")
                    fstype = dev.get("fstype")
                    mountpoint = dev.get("mountpoint")

                    # Solo particiones y discos con filesystem
                    if dtype in ("part", "disk") and fstype:
                        entry = {
                            "name": name,
                            "size": dev.get("size"),
                            "fstype": fstype,
                            "mountpoint": mountpoint,
                            "label": dev.get("label"),
                            "parent": parent,
                        }
                        if mountpoint:
                            mounted.append(entry)
                        else:
                            unmounted.append(entry)

                    # Recursivo para children
                    _walk(dev.get("children", []), parent=name)

            _walk(raw.get("blockdevices", []))

            df_mounts = []

            try:
                df = subprocess.run(
                    ["df", "-h", "--output=source,target"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if df.returncode == 0:
                    lines = df.stdout.strip().split("\n")[1:]  # skip header

                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 2:
                            source = parts[0]
                            target = parts[1]

                            if source.startswith(
                                ("tmpfs", "udev", "overlay", "efivarfs")
                            ):
                                continue

                            if target.startswith(("/run", "/sys", "/proc", "/dev")):
                                continue

                            if target in ("/", "/boot/efi", "/etc/pve"):
                                continue

                            df_mounts.append({"source": source, "target": target})

            except Exception:
                pass

            response = {
                "mounted": mounted,
                "unmounted": unmounted,
                "mounted_count": len(mounted),
                "unmounted_count": len(unmounted),
                "mount_points": df_mounts,
            }

            self._send_json_response(json.dumps(response))

        except Exception as e:
            self._send_error_response(f"Error getting mount info: {e}")

    def _handle_ksm(self):
        """Expose a fixed, read-only KSM snapshot without client-controlled commands."""
        base = Path("/sys/kernel/mm/ksm")
        fields = ("run", "pages_shared", "pages_sharing", "pages_unshared",
                  "pages_volatile", "full_scans", "pages_to_scan", "sleep_millisecs")
        payload = {"available": False, "error": None, "ksmtuned": {}}
        values = {}
        if base.is_dir():
            try:
                for field in fields:
                    values[field] = int((base / field).read_text(encoding="ascii").strip())
                payload.update(values)
                payload["available"] = True
                payload["page_size"] = os.sysconf("SC_PAGE_SIZE")
                # pages_sharing counts mappings beyond the first mapping per page.
                payload["memory_saved_bytes"] = values["pages_sharing"] * payload["page_size"]
            except (OSError, ValueError):
                payload["error"] = "KSM counters are unavailable"
        else:
            payload["error"] = "KSM subsystem is unavailable"
        try:
            result = subprocess.run(
                ["systemctl", "show", "ksmtuned", "--property=LoadState,ActiveState,SubState,UnitFileState"],
                capture_output=True, text=True, timeout=5, check=False,
            )
            payload["ksmtuned"] = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
            if result.returncode and not payload["ksmtuned"]:
                payload["ksmtuned_error"] = "ksmtuned status is unavailable"
        except (OSError, subprocess.TimeoutExpired):
            payload["ksmtuned_error"] = "ksmtuned status is unavailable"
        self._send_json_response(json.dumps(payload))

    def _get_smart_data_fast(self):
        """Universal SMART data collection for all disks."""
        smart_data = {}

        try:
            scan_cmd = ["smartctl", "--scan-open"]
            result = subprocess.run(
                scan_cmd, capture_output=True, text=True, timeout=20
            )

            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split("\n")

                for line in lines:
                    if line and not line.startswith("#"):
                        parts = line.split()
                        if len(parts) >= 3:
                            device = parts[0]
                            device_type = parts[2]
                            device_key = device.replace("/dev/", "")

                            disk_info = self._get_disk_info_safe(
                                device, device_type, timeout=10
                            )

                            if disk_info:
                                smart_data[device_key] = disk_info
                            else:
                                smart_data[device_key] = {
                                    "model": "Device (no SMART)",
                                    "smart_available": False,
                                    "device_type": device_type,
                                    "path": device,
                                }

            if not smart_data:
                basic_checks = [
                    ("/dev/sda", "sat"),
                    ("/dev/nvme0", "nvme"),
                ]

                for device, dev_type in basic_checks:
                    device_key = device.replace("/dev/", "")
                    info = self._get_disk_info_safe(device, dev_type, timeout=5)
                    if info:
                        smart_data[device_key] = info

            for record in _cached_ssacli_records():
                if record.get("exposed_to_os"):
                    continue
                device_key = record["devpath"].removeprefix("/dev/")
                if device_key not in smart_data:
                    smart_data[device_key] = record

            return smart_data

        except SsacliSnapshotError:
            raise
        except Exception as e:
            return {"error": f"Scan failed: {str(e)}"}

    def _get_smart_data_extended(self):
        """Get extended SMART data with retry logic."""
        smart_data = self._get_smart_data_fast()

        for disk_key in list(smart_data.keys()):
            disk = smart_data[disk_key]
            if (isinstance(disk, dict) and disk.get("smart_available")
                    and disk.get("device_type") != "ssacli"):
                detailed = self._get_detailed_smart_attributes(f"/dev/{disk_key}")
                if detailed:
                    disk.update(detailed)

        return smart_data

    def _get_disk_info_safe(self, device, device_type, timeout=10):
        device_key = device.replace("/dev/", "")

        try:
            if device_type == "scsi":
                base_cmd = ["smartctl", "-a", "-d", "scsi"]
            elif device_type == "nvme":
                base_cmd = ["smartctl", "-a", "-d", "nvme"]
            else:
                base_cmd = ["smartctl", "-a", "-d", "sat"]

            cmd_json = base_cmd + ["-j", device]
            result = subprocess.run(
                cmd_json, capture_output=True, text=True, timeout=timeout
            )

            if result.returncode == 0:
                disk_info = json.loads(result.stdout)
                return self._parse_smart_info(disk_info, result.returncode)
            else:
                cmd_info = ["smartctl", "-i", device]
                result_info = subprocess.run(
                    cmd_info, capture_output=True, text=True, timeout=timeout
                )

                if result_info.returncode == 0:
                    return self._parse_basic_info_text(
                        result_info.stdout, result.returncode
                    )

        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
            pass

        return None

    def _parse_smart_info(self, disk_info, returncode):
        parsed = {
            "model": disk_info.get("model_name", "Unknown"),
            "serial": disk_info.get("serial_number", "Unknown"),
            "firmware": disk_info.get("firmware_version", "Unknown"),
            "capacity_gb": round(
                disk_info.get("user_capacity", {}).get("bytes", 0) / (1024**3), 1
            ),
            "smart_passed": disk_info.get("smart_status", {}).get("passed", False),
            "smart_available": bool(
                disk_info.get("smart_status")
                or disk_info.get("ata_smart_attributes")
                or disk_info.get("nvme_smart_health_information_log")
            ),
            "temperature_c": None,
            "power_on_hours": None,
            "device_type": disk_info.get("device", {}).get("type", ""),
            "returncode": returncode,
            "reallocated_sectors": None,
            "pending_sectors": None,
            "uncorrectable_errors": None,
            "media_errors": None,
            "spin_retry_count": None,
            "seek_error_rate": None,
            "available_spare": None,
            "available_spare_threshold": None,
            "percentage_used": None,
            "data_units_read": None,
            "data_units_written": None,
            "data_units_read_tb": None,
            "data_units_written_tb": None,
            "host_read_commands": None,
            "host_write_commands": None,
            "controller_busy_time": None,
            "power_cycles": None,
            "unsafe_shutdowns": None,
            "error_info_log_entries": None,
            "warning_temp_time": None,
            "critical_temp_time": None,
            "critical_warning": None,
        }

        device_type = disk_info.get("device", {}).get("type", "").lower()

        if "nvme" in device_type:
            nvme_smart = disk_info.get("nvme_smart_health_information_log", {})
            if nvme_smart:
                def nvme_value(*keys):
                    for key in keys:
                        value = nvme_smart.get(key)
                        if value is not None:
                            return value
                    return None

                parsed["temperature_c"] = nvme_smart.get("temperature")
                parsed["available_spare"] = nvme_smart.get("available_spare")
                parsed["available_spare_threshold"] = nvme_smart.get(
                    "available_spare_threshold"
                )
                parsed["percentage_used"] = nvme_smart.get("percentage_used")

                data_units_read = nvme_smart.get("data_units_read")
                if data_units_read is not None:
                    parsed["data_units_read"] = data_units_read
                    parsed["data_units_read_tb"] = round(
                        data_units_read * 512000 / (1000**4), 1
                    )

                data_units_written = nvme_smart.get("data_units_written")
                if data_units_written is not None:
                    parsed["data_units_written"] = data_units_written
                    parsed["data_units_written_tb"] = round(
                        data_units_written * 512000 / (1000**4), 1
                    )

                parsed["host_read_commands"] = nvme_value(
                    "host_reads", "host_read_commands",
                )
                parsed["host_write_commands"] = nvme_value(
                    "host_writes", "host_write_commands",
                )
                parsed["controller_busy_time"] = nvme_smart.get("controller_busy_time")
                parsed["power_cycles"] = nvme_smart.get("power_cycles")
                parsed["unsafe_shutdowns"] = nvme_smart.get("unsafe_shutdowns")
                parsed["media_errors"] = nvme_value(
                    "media_errors", "media_and_data_integrity_errors",
                )
                parsed["error_info_log_entries"] = nvme_value(
                    "num_err_log_entries", "error_information_log_entries",
                )
                parsed["warning_temp_time"] = nvme_value(
                    "warning_temp_time", "warning_composite_temperature_time",
                )
                parsed["critical_temp_time"] = nvme_value(
                    "critical_comp_time", "critical_composite_temperature_time",
                )
                parsed["critical_warning"] = nvme_smart.get("critical_warning")
                parsed["power_on_hours"] = nvme_smart.get("power_on_hours")

            if "pending_sectors" in parsed:
                parsed["pending_sectors"] = None

        else:
            model_name = str(disk_info.get("model_name") or "").strip()
            seagate = (
                any("seagate" in str(disk_info.get(key) or "").casefold()
                    for key in ("vendor", "model_family", "model_name"))
                or re.match(r"^ST[0-9]{3,}", model_name, re.IGNORECASE) is not None
            )
            if seagate:
                parsed.update({
                    "seek_error_rate_normalized": None,
                    "seek_error_rate_raw": None,
                    "seek_error_rate_worst": None,
                    "seek_error_rate_threshold": None,
                })
            temp = disk_info.get("temperature", {})
            if temp:
                parsed["temperature_c"] = temp.get("current", temp.get("value"))

            power_time = disk_info.get("power_on_time", {})
            if power_time:
                parsed["power_on_hours"] = power_time.get("hours")

            attributes = disk_info.get("ata_smart_attributes", {}).get("table", [])
            for attr in attributes:
                name = attr.get("name", "")
                raw_value = attr.get("raw", {}).get("value", 0)
                normalized_name = name.lower().replace("_", "").replace("-", "")

                if "temperature" in normalized_name:
                    parsed["temperature_c"] = (
                        raw_value
                        if not parsed["temperature_c"]
                        else parsed["temperature_c"]
                    )
                elif "poweronhours" in normalized_name:
                    parsed["power_on_hours"] = (
                        raw_value
                        if not parsed["power_on_hours"]
                        else parsed["power_on_hours"]
                    )
                elif any(
                    x in normalized_name for x in ["currentpendingsector", "pending"]
                ):
                    parsed["pending_sectors"] = raw_value
                elif any(
                    x in normalized_name for x in ["reallocatedsectorct", "reallocated"]
                ):
                    parsed["reallocated_sectors"] = raw_value
                elif any(
                    x in normalized_name
                    for x in ["uncorrectableerrorcnt", "offlineuncorrectable"]
                ):
                    parsed["uncorrectable_errors"] = raw_value
                elif "spinretrycount" in normalized_name:
                    parsed["spin_retry_count"] = raw_value
                elif "seekerrorrate" in normalized_name:
                    parsed["seek_error_rate"] = raw_value

                attr_id = attr.get("id")
                if attr_id:
                    if attr_id == 5:
                        parsed["reallocated_sectors"] = raw_value
                    elif attr_id == 197:
                        parsed["pending_sectors"] = raw_value
                    elif attr_id == 198:
                        parsed["uncorrectable_errors"] = raw_value
                    elif attr_id == 10:
                        parsed["spin_retry_count"] = raw_value
                    elif attr_id == 7:
                        parsed["seek_error_rate"] = raw_value

                if seagate and (attr_id == 7 or "seekerrorrate" in normalized_name):
                    raw = attr.get("raw")
                    parsed["seek_error_rate_raw"] = (
                        raw.get("value") if isinstance(raw, dict) else None
                    )
                    for field, source in (
                        ("seek_error_rate_normalized", "value"),
                        ("seek_error_rate_worst", "worst"),
                        ("seek_error_rate_threshold", "thresh"),
                    ):
                        value = attr.get(source)
                        if type(value) is int and 0 <= value <= 255:
                            parsed[field] = value

        return parsed

    def _parse_basic_info_text(self, text_output, returncode):
        parsed = {
            "model": "Unknown",
            "smart_available": False,
            "returncode": returncode,
            "reallocated_sectors": None,
            "pending_sectors": None,
            "uncorrectable_errors": None,
        }

        lines = text_output.split("\n")
        for line in lines:
            line_lower = line.lower()

            if "model:" in line_lower and "unknown" not in line_lower:
                parsed["model"] = line.split(":", 1)[1].strip()
            elif "serial number:" in line_lower:
                parsed["serial"] = line.split(":", 1)[1].strip()
            elif "user capacity:" in line_lower:
                match = re.search(r"(\d+[,\.]?\d*)\s*bytes", line, re.IGNORECASE)
                if match:
                    try:
                        bytes_str = match.group(1).replace(",", "").replace(".", "")
                        bytes_val = int(bytes_str)
                        parsed["capacity_gb"] = round(bytes_val / (1024**3), 1)
                    except:
                        pass

        return parsed

    def _get_detailed_smart_attributes(self, device):
        detailed = {}

        try:
            cmd_check = ["smartctl", "-i", device]
            result_check = subprocess.run(
                cmd_check, capture_output=True, text=True, timeout=5
            )

            device_type = "unknown"
            if "nvme" in result_check.stdout.lower():
                device_type = "nvme"
            elif (
                "ata" in result_check.stdout.lower()
                or "sata" in result_check.stdout.lower()
            ):
                device_type = "ata"

            if device_type == "nvme":
                cmd = ["smartctl", "-x", device]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

                if result.returncode == 0:
                    lines = result.stdout.split("\n")
                    for line in lines:

                        if "Available Spare:" in line:
                            match = re.search(r"Available Spare:\s+(\d+)%", line)
                            if match:
                                detailed["available_spare"] = int(match.group(1))

                        elif "Available Spare Threshold:" in line:
                            match = re.search(
                                r"Available Spare Threshold:\s+(\d+)%", line
                            )
                            if match:
                                detailed["available_spare_threshold"] = int(
                                    match.group(1)
                                )

                        elif "Percentage Used:" in line:
                            match = re.search(r"Percentage Used:\s+(\d+)%", line)
                            if match:
                                detailed["percentage_used"] = int(match.group(1))

                        elif "Data Units Read:" in line:
                            match = re.search(r"Data Units Read:\s+([\d,]+)", line)
                            if match:
                                val = int(match.group(1).replace(",", ""))
                                detailed["data_units_read"] = val
                                detailed["data_units_read_tb"] = round(
                                    val * 512000 / (1000**4), 1
                                )

                        elif "Data Units Written:" in line:
                            match = re.search(r"Data Units Written:\s+([\d,]+)", line)
                            if match:
                                val = int(match.group(1).replace(",", ""))
                                detailed["data_units_written"] = val
                                detailed["data_units_written_tb"] = round(
                                    val * 512000 / (1000**4), 1
                                )

                        elif "Host Read Commands" in line:
                            match = re.search(
                                r"Host\s+Read\s+Commands:\s+([\d,]+)", line
                            )
                            if match:
                                detailed["host_read_commands"] = int(
                                    match.group(1).replace(",", "")
                                )

                        elif "Host Write Commands" in line:
                            match = re.search(
                                r"Host\s+Write\s+Commands:\s+([\d,]+)", line
                            )
                            if match:
                                detailed["host_write_commands"] = int(
                                    match.group(1).replace(",", "")
                                )

                        elif "Controller Busy Time:" in line:
                            match = re.search(r"Controller Busy Time:\s+(\d+)", line)
                            if match:
                                detailed["controller_busy_time"] = int(match.group(1))

                        elif "Power Cycles:" in line:
                            match = re.search(r"Power Cycles:\s+(\d+)", line)
                            if match:
                                detailed["power_cycles"] = int(match.group(1))

                        elif "Power On Hours:" in line:
                            match = re.search(r"Power On Hours:\s+(\d+)", line)
                            if match:
                                detailed["power_on_hours"] = int(match.group(1))

                        elif "Unsafe Shutdowns:" in line:
                            match = re.search(r"Unsafe Shutdowns:\s+(\d+)", line)
                            if match:
                                detailed["unsafe_shutdowns"] = int(match.group(1))

                        elif "Media and Data Integrity Errors:" in line:
                            match = re.search(
                                r"Media and Data Integrity Errors:\s+(\d+)", line
                            )
                            if match:
                                detailed["media_errors"] = int(match.group(1))

                        elif "Error Information Log Entries" in line:
                            match = re.search(r"Entries:\s+(\d+)", line)
                            if match:
                                detailed["error_info_log_entries"] = int(match.group(1))

                        elif "Warning  Comp. Temperature Time" in line:
                            match = re.search(r"Time:\s+(\d+)", line)
                            if match:
                                detailed["warning_temp_time"] = int(match.group(1))

                        elif "Critical Comp. Temperature Time" in line:
                            match = re.search(r"Time:\s+(\d+)", line)
                            if match:
                                detailed["critical_temp_time"] = int(match.group(1))

            else:
                cmd = ["smartctl", "-A", device]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

                if result.returncode == 0:
                    lines = result.stdout.split("\n")
                    for line in lines:

                        if "Reallocated_Sector_Ct" in line:
                            match = re.search(r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", line)
                            if match:
                                detailed["reallocated_sectors"] = int(match.group(4))

                        elif "Current_Pending_Sector" in line:
                            match = re.search(r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", line)
                            if match:
                                detailed["pending_sectors"] = int(match.group(4))

                        elif "Uncorrectable_Error_Cnt" in line:
                            match = re.search(r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", line)
                            if match:
                                detailed["uncorrectable_errors"] = int(match.group(4))

        except Exception:
            pass

        return detailed

    def _check_sensors(self):
        try:
            result = subprocess.run(["sensors", "-v"], capture_output=True, timeout=3)
            return result.returncode == 0
        except Exception:
            return False

    def _check_smartctl(self):
        try:
            result = subprocess.run(
                ["smartctl", "--version"], capture_output=True, timeout=3
            )
            return result.returncode == 0
        except Exception:
            return False

    def _get_disk_health_summary(self):
        try:
            smart_data = self._get_smart_data_fast()
            working = 0
            failed = 0

            for disk, info in smart_data.items():
                if not isinstance(info, dict):
                    failed += 1
                elif info.get("device_type") == "ssacli":
                    if info.get("controller_health_passed"):
                        working += 1
                    else:
                        failed += 1
                elif info.get("smart_available") and info.get("smart_passed"):
                    working += 1
                else:
                    failed += 1

            return {"working": working, "failed": failed, "total": working + failed}
        except Exception:
            return {"working": 0, "failed": 0, "total": 0}

    def _send_json_response(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if isinstance(data, bytes):
            self.wfile.write(data)
        else:
            self.wfile.write(data.encode())

    def _send_error_response(self, message):
        error_data = json.dumps({"error": message})
        self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(error_data.encode())

    def log_message(self, format, *args):
        pass


def main():
    port = 9000
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"PVE Sensors API v2 started on port {port}")
    print(f"Allowed client IPs: {', '.join(sorted(ALLOWED_IPS))}")
    print("Endpoints:")
    print(f"  GET /disks           - Controller-backed physical disk inventory")
    print(f"  GET /sensors         - lm-sensors data")
    print(f"  GET /smart           - Basic SMART data (fast)")
    print(f"  GET /smart-disk      - One disk with optional standby protection")
    print(f"  GET /smart-extended  - Extended SMART data")
    print(f"  GET /memory          - Memory module information")
    print(f"  GET /health          - System health status")
    print(f"  GET /mounts          - Disk mount status")
    print(f"  GET /ksm             - KSM status and counters")
    server.serve_forever()


if __name__ == "__main__":
    main()
