"""Physical disk sensors for Proxmox Extended Sensors."""

import logging
import math

from homeassistant.const import EntityCategory
from homeassistant.helpers import device_registry as dr

from .base import ProxmoxBaseSensor, node_section
from ..const import DOMAIN
from ..logic.disk_smart import preferences as disk_smart_preferences
from ..logic.pve_local_identity import (
    coordinator_pve_local_identity_context,
    disks_group_identifier,
    node_device_identifier,
)
from ..logic.physical_disks import capacity_unique_id, hardware_value

_LOGGER = logging.getLogger(__name__)


def _format_gb(value):
    try:
        if value is None:
            return 0
        return round(float(value) / (1024**3), 2)
    except (ValueError, TypeError):
        return 0


class ProxmoxDiskSensor(ProxmoxBaseSensor):
    _attr_has_entity_name = False

    def __init__(self, coordinator, disk_id, node, label, physical_identifier=None):
        disks = coordinator.data.get("disks", {})
        disk_info = disks.get(disk_id, {})
        self._model = disk_info.get("model", label or "Unknown")
        self._serial = disk_info.get("serial", "")
        unique_id = f"proxmox_disk_{node}_{disk_id}_v1"

        super().__init__(
            coordinator, disk_id, None, "GB", unique_id, node,
            full_unique_id=capacity_unique_id(physical_identifier)
            if physical_identifier else None,
        )
        self._attr_translation_key = "disk_size"
        self._attr_name = "Capacity"

        self._disk_id = disk_id
        self._physical_identifier = physical_identifier
        self._attr_icon = "mdi:harddisk"
        self._attr_state_class = "measurement"
        self._attr_device_class = "data_size"

    @property
    def device_info(self):
        node_id = self._node.lower()
        context = coordinator_pve_local_identity_context(self.coordinator)
        disk = self._current_disk(self.coordinator.data.get("disks", {})) or {}
        size = disk.get("size")
        size_tb = round(size / (1024**4), 1) if isinstance(size, (int, float)) else None
        kind = str(disk.get("type") or "Disk").upper()
        info = {
            "identifiers": {(
                DOMAIN, self._physical_identifier or disks_group_identifier(context, node_id)
            )},
            "name": (
                f"2. {kind} {self._model} {size_tb:g} TB" if self._physical_identifier and size_tb
                else f"2. {kind} {self._model}" if self._physical_identifier
                else f"2. Disks: {self._node.capitalize()}"
            ),
            "manufacturer": str(disk.get("vendor") or "Proxmox")
            if self._physical_identifier else "Proxmox",
            "model": str(self._model) if self._physical_identifier else "Physical Disks Storage",
        }
        if self._physical_identifier and (serial := hardware_value(disk.get("serial"))):
            info["serial_number"] = serial

        try:
            info["via_device_id"] = dr.async_get_device_id_by_identifier(
                self.coordinator.hass,
                (DOMAIN, node_device_identifier(context, node_id)),
                config_entry_id=self.coordinator.config_entry.entry_id,
            )
        except ValueError:
            _LOGGER.debug(
                "Parent node device %s not found in config entry %s; omitting via_device_id",
                node_id,
                self.coordinator.config_entry.entry_id,
            )
        return info

    def _get_value(self):
        disks = self.coordinator.data.get("disks", {})
        disk = self._current_disk(disks)
        if not disk:
            return None
        size = disk.get("size")
        return _format_gb(size) if size is not None else None

    def _current_disk(self, disks):
        if self._physical_identifier:
            ids = self.coordinator.data.get("physical_disk_ids", {})
            paths = [path for path, identifier in ids.items()
                     if identifier == self._physical_identifier]
            return disks.get(paths[0]) if len(paths) == 1 else None
        return disks.get(self._disk_id)

    def _find_smart_data_by_serial(self):
        """Search SMART data by serial number."""
        if self._physical_identifier:
            if not self._smart_monitoring_enabled():
                return None
            snapshot = self.coordinator.data.get("physical_smart", {}).get(
                self._physical_identifier, {}
            )
            return snapshot.get("data") if isinstance(snapshot, dict) else None
        smart_data = {
            disk_id: disk_smart
            for disk_id, disk_smart in node_section(
                self.coordinator.data, "smart", self._node
            ).items()
            if isinstance(disk_smart, dict)
        }

        if not smart_data or not self._serial:
            return None

        matching = [disk_smart for disk_smart in smart_data.values()
                    if disk_smart.get("serial") == self._serial]
        return matching[0] if len(matching) == 1 else None

    def _smart_monitoring_enabled(self):
        entry = getattr(self.coordinator, "config_entry", None)
        if entry is None or not self._physical_identifier:
            return True
        return disk_smart_preferences(
            entry.options, self._physical_identifier, 1,
            entry.options.get("enable_smart_monitoring",
                              entry.data.get("enable_smart_monitoring", True)),
        )["enabled"]

    @property
    def extra_state_attributes(self):
        """Add all disk attributes including SMART."""
        disks = self.coordinator.data.get("disks", {})
        disk = self._current_disk(disks)

        if not disk:
            return {}

        # Basic attributes
        attributes = {
            "Model": disk.get("model", "Unknown"),
            "Serial": disk.get("serial", "N/A"),
            "Type": disk.get("type", "N/A"),
            "Raw Capacity (Bytes)": disk.get("size"),
        }

        # Search for SMART data
        disk_smart = self._find_smart_data_by_serial()
        if self._physical_identifier:
            snapshot = self.coordinator.data.get("physical_smart", {}).get(
                self._physical_identifier, {}
            )
            if not self._smart_monitoring_enabled():
                snapshot = {"status": "disabled"}
            attributes["SMART Poll Status"] = snapshot.get("status", "pending")
            attributes["SMART Last Read"] = snapshot.get("last_read")
            attributes["SMART Data Age (s)"] = snapshot.get("age_seconds")

        if disk_smart:
            # Basic information
            if disk_smart.get("model"):
                attributes["SMART Model"] = disk_smart.get("model")

            if disk_smart.get("serial"):
                attributes["SMART Serial"] = disk_smart.get("serial")

            if disk_smart.get("firmware"):
                attributes["Firmware"] = disk_smart.get("firmware")

            # Health status
            if "smart_passed" in disk_smart:
                attributes["Health Status"] = (
                    "OK" if disk_smart.get("smart_passed") else "FAILED"
                )

            if disk_smart.get("smart_available") is not None:
                attributes["SMART Available"] = disk_smart.get("smart_available")

            # Temperature
            if disk_smart.get("temperature_c") is not None:
                temp = disk_smart.get("temperature_c")
                if temp > 50:
                    attributes["Temperature"] = f"⚠️ {temp} °C"
                else:
                    attributes["Temperature"] = f"{temp} °C"

            # Operating hours
            if disk_smart.get("power_on_hours") is not None:
                hours = disk_smart.get("power_on_hours")
                years = hours / (24 * 365)
                if years > 3:
                    attributes["Age"] = f"{years:.1f} years"
                attributes["Power On Hours"] = f"{hours:,}"

            # SMART Capability
            if disk_smart.get("capacity_gb") is not None:
                attributes["Capacity"] = f"{disk_smart.get('capacity_gb')} GB"

            # Reallocated_Sector_Ct
            if disk_smart.get("reallocated_sectors") is not None:
                reallocated = disk_smart.get("reallocated_sectors")
                if reallocated > 10:
                    attributes["Reallocated Sectors"] = f"🚨 {reallocated}"
                elif reallocated > 0:
                    attributes["Reallocated Sectors"] = f"⚠️ {reallocated}"
                else:
                    attributes["Reallocated Sectors"] = reallocated

            # Current_Pending_Sector
            if disk_smart.get("pending_sectors") is not None:
                pending = disk_smart.get("pending_sectors")
                if pending > 0:
                    attributes["Pending Sectors"] = f"🚨 CRITICAL: {pending}"
                else:
                    attributes["Pending Sectors"] = pending

            # Uncorrectable_Error_Cnt
            if disk_smart.get("uncorrectable_errors") is not None:
                uncorrectable = disk_smart.get("uncorrectable_errors")
                if uncorrectable > 0:
                    attributes["Uncorrectable Errors"] = f"🚨 {uncorrectable}"
                else:
                    attributes["Uncorrectable Errors"] = uncorrectable

            # Media Errors (NVMe)
            if disk_smart.get("media_errors") is not None:
                media_err = disk_smart.get("media_errors")
                if media_err > 0:
                    attributes["Media Errors"] = f"⚠️ {media_err}"
                else:
                    attributes["Media Errors"] = media_err

            # Spin Retry Count (HDD)
            if disk_smart.get("spin_retry_count") is not None:
                spin_retry = disk_smart.get("spin_retry_count")
                if spin_retry > 0:
                    attributes["Spin Retry Count"] = f"⚠️ {spin_retry}"
                else:
                    attributes["Spin Retry Count"] = spin_retry

            # Seagate SMART 7 RAW is vendor-encoded; show its normalized value.
            if (disk_smart.get("seek_error_rate_normalized") is not None
                    or disk_smart.get("seek_error_rate_raw") is not None):
                attributes["Seek Error Rate"] = disk_smart.get("seek_error_rate_normalized")
                attributes["Seek Error Rate RAW"] = disk_smart["seek_error_rate_raw"]
                attributes["Seek Error Rate WORST"] = disk_smart.get("seek_error_rate_worst")
                attributes["Seek Error Rate THRESH"] = disk_smart.get("seek_error_rate_threshold")
            elif disk_smart.get("seek_error_rate") is not None:
                seek_err = disk_smart.get("seek_error_rate")
                if seek_err > 0:
                    attributes["Seek Error Rate"] = f"⚠️ {seek_err}"
                else:
                    attributes["Seek Error Rate"] = seek_err

            # Additional information
            if disk_smart.get("device_type"):
                attributes["Device Type"] = disk_smart.get("device_type")

            if disk_smart.get("returncode") is not None:
                attributes["SMART Return Code"] = disk_smart.get("returncode")

            # === NVMe ATTRIBUTES ===

            # Available Spare
            if disk_smart.get("available_spare") is not None:
                attributes["Available Spare (%)"] = disk_smart.get("available_spare")

            # Available Spare Threshold
            if disk_smart.get("available_spare_threshold") is not None:
                attributes["Available Spare Threshold (%)"] = disk_smart.get(
                    "available_spare_threshold"
                )

            # Percentage Used
            if disk_smart.get("percentage_used") is not None:
                attributes["Percentage Used (%)"] = disk_smart.get("percentage_used")

            # Data Units Read / Written
            if disk_smart.get("data_units_read") is not None:
                attributes["Data Units Read"] = f"{disk_smart.get('data_units_read'):,}"
            if disk_smart.get("data_units_read_tb") is not None:
                attributes["Data Read (TB)"] = disk_smart.get("data_units_read_tb")

            if disk_smart.get("data_units_written") is not None:
                attributes["Data Units Written"] = (
                    f"{disk_smart.get('data_units_written'):,}"
                )
            if disk_smart.get("data_units_written_tb") is not None:
                attributes["Data Written (TB)"] = disk_smart.get(
                    "data_units_written_tb"
                )

            # Host Commands
            if disk_smart.get("host_read_commands") is not None:
                attributes["Host Read Commands"] = (
                    f"{disk_smart.get('host_read_commands'):,}"
                )
            if disk_smart.get("host_write_commands") is not None:
                attributes["Host Write Commands"] = (
                    f"{disk_smart.get('host_write_commands'):,}"
                )

            # Controller Busy Time
            if disk_smart.get("controller_busy_time") is not None:
                attributes["Controller Busy Time (min)"] = disk_smart.get(
                    "controller_busy_time"
                )

            # Error Log Entries
            if disk_smart.get("error_info_log_entries") is not None:
                attributes["Error Log Entries"] = disk_smart.get(
                    "error_info_log_entries"
                )

            # Temperature Time
            if disk_smart.get("warning_temp_time") is not None:
                attributes["Warning Temp Time"] = disk_smart.get("warning_temp_time")
            if disk_smart.get("critical_temp_time") is not None:
                attributes["Critical Temp Time"] = disk_smart.get("critical_temp_time")

            # Critical Warning
            if disk_smart.get("critical_warning") is not None:
                attributes["Critical Warning"] = disk_smart.get("critical_warning")

            # Health Score
            health_score = self._calculate_health_score(disk_smart)
            attributes["Health Score"] = f"{health_score}/100"

            # General condition
            health_status = self._determine_health_status(disk_smart)
            attributes["Disk Health"] = health_status

        return attributes

    def _calculate_health_score(self, disk_smart):
        """Calculate health score 0-100 based on SMART."""
        score = 100

        # Penalize by reallocated sectors
        reallocated = disk_smart.get("reallocated_sectors", 0) or 0
        if reallocated > 100:
            score -= 50
        elif reallocated > 50:
            score -= 30
        elif reallocated > 10:
            score -= 15
        elif reallocated > 0:
            score -= 5

        # Penalize for pending sectors
        pending = disk_smart.get("pending_sectors", 0) or 0
        if pending > 10:
            score -= 60
        elif pending > 0:
            score -= 40

        # Penalize for uncorrectable errors
        uncorrectable = disk_smart.get("uncorrectable_errors", 0) or 0
        if uncorrectable > 0:
            score -= 50

        # Penalize for media errors
        media_err = disk_smart.get("media_errors", 0) or 0
        if media_err > 10:
            score -= 30
        elif media_err > 0:
            score -= 15

        # Penalize for high temperature
        temp = disk_smart.get("temperature_c")
        if temp:
            if temp > 60:
                score -= 30
            elif temp > 50:
                score -= 15

        # Penalize if SMART failed
        if disk_smart.get("smart_passed") is False:
            score = 0

        # Ensure not negative
        return max(0, score)

    def _determine_health_status(self, disk_smart):
        """Determine the health status of the disk."""
        # Check if SMART failed
        if disk_smart.get("smart_passed") is False:
            return "🔴 FAILED"

        # Check critical attributes
        pending = disk_smart.get("pending_sectors", 0) or 0
        uncorrectable = disk_smart.get("uncorrectable_errors", 0) or 0
        reallocated = disk_smart.get("reallocated_sectors", 0) or 0

        if pending > 0 or uncorrectable > 0:
            return "🔴 CRITICAL"
        elif reallocated > 50:
            return "🟠 WARNING"
        elif reallocated > 10:
            return "🟡 CAUTION"
        else:
            return "🟢 HEALTHY"


SMART_METRICS = {
    "smart_status": ("SMART health", None, None),
    "smart_poll_status": ("SMART Poll Status", None, None),
    "temperature_c": ("Temperature", "°C", "temperature"),
    "power_on_hours": ("Power-on hours", "h", "duration"),
    "percentage_used": ("Percentage used", "%", None),
    "available_spare": ("Available spare", "%", None),
    "reallocated_sectors": ("Reallocated sectors", None, None),
    "pending_sectors": ("Pending sectors", None, None),
    "media_errors": ("Media errors", None, None),
    "seek_error_rate": ("Seek error rate", None, None),
}


class ProxmoxDiskSmartSensor(ProxmoxDiskSensor):
    """One measured SMART value from the verified per-disk sidecar result."""

    def __init__(self, coordinator, disk_id, node, label, physical_identifier, metric):
        super().__init__(coordinator, disk_id, node, label, physical_identifier)
        name, unit, device_class = SMART_METRICS[metric]
        self._metric = metric
        self._attr_unique_id = f"{physical_identifier}_{metric}"
        self._attr_translation_key = f"disk_{metric}"
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        if metric == "smart_poll_status":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_state_class = (
            "measurement" if metric not in ("smart_status", "smart_poll_status", "seek_error_rate") else None
        )

    def _get_value(self):
        if self._metric == "smart_poll_status":
            if not self._smart_monitoring_enabled():
                return "disabled"
            snapshot = self.coordinator.data.get("physical_smart", {}).get(
                self._physical_identifier, {}
            )
            status = snapshot.get("status")
            return status if status in {
                "ok", "pending", "standby", "unsupported", "error", "disabled",
            } else None
        data = self._find_smart_data_by_serial()
        if not isinstance(data, dict):
            return None
        if self._metric == "smart_status":
            passed = data.get("smart_passed")
            return "Healthy" if passed is True else "Failed" if passed is False else None
        value = data.get(
            "seek_error_rate_normalized" if self._metric == "seek_error_rate" else self._metric
        )
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return value if math.isfinite(value) else None

    @property
    def extra_state_attributes(self):
        snapshot = self.coordinator.data.get("physical_smart", {}).get(
            self._physical_identifier, {}
        )
        if not self._smart_monitoring_enabled():
            snapshot = {"status": "disabled"}
        attributes = {
            "SMART Poll Status": snapshot.get("status", "pending"),
            "SMART Last Read": snapshot.get("last_read"),
            "SMART Data Age (s)": snapshot.get("age_seconds"),
        }
        if self._metric == "seek_error_rate":
            data = snapshot.get("data") or {}
            attributes["RAW"] = data.get("seek_error_rate_raw")
            attributes["WORST"] = data.get("seek_error_rate_worst")
            attributes["THRESH"] = data.get("seek_error_rate_threshold")
        return attributes
