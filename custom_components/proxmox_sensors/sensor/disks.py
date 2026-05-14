"""Physical disk sensors for Proxmox Extended Sensors."""

from .base import ProxmoxBaseSensor
from ..const import DOMAIN


def _format_gb(value):
    try:
        if value is None:
            return 0
        return round(float(value) / (1024**3), 2)
    except (ValueError, TypeError):
        return 0


class ProxmoxDiskSensor(ProxmoxBaseSensor):
    def __init__(self, coordinator, disk_id, node, label):
        disks = coordinator.data.get("disks", {})
        disk_info = disks.get(disk_id, {})
        self._model = disk_info.get("model", label or "Unknown")
        self._serial = disk_info.get("serial", "")
        name = f"{self._model} Size"
        unique_id = f"proxmox_disk_{node}_{disk_id}_v1"

        super().__init__(coordinator, disk_id, name, "GB", unique_id, node)

        self._disk_id = disk_id
        self._attr_icon = "mdi:harddisk"
        self._attr_state_class = "measurement"
        self._attr_device_class = "data_size"

    @property
    def device_info(self):
        node_id = self._node.lower()
        return {
            "identifiers": {(DOMAIN, f"proxmox_disks_group_{node_id}")},
            "name": f"2. Disks: {self._node.capitalize()}",
            "manufacturer": "Proxmox",
            "model": "Physical Disks Storage",
            "via_device": (DOMAIN, f"proxmox_node_{node_id}"),
        }

    def _get_value(self):
        disks = self.coordinator.data.get("disks", {})
        disk = disks.get(self._disk_id)
        if not disk:
            return None
        size = disk.get("size")
        return _format_gb(size) if size is not None else None

    def _find_smart_data_by_serial(self):
        """Search SMART data by serial number."""
        smart_data = self.coordinator.data.get("smart", {}).get(self._node, {})

        if not smart_data or not self._serial:
            return None

        # By exact serial number
        for disk_id, disk_smart in smart_data.items():
            if disk_smart.get("serial") == self._serial:
                return disk_smart

        # Try by disk ID
        if self._disk_id in smart_data:
            return smart_data[self._disk_id]

        # Search by model
        clean_model = self._model.replace(" ", "_").replace("-", "_").lower()
        for disk_id, disk_smart in smart_data.items():
            smart_model = (
                disk_smart.get("model", "").replace(" ", "_").replace("-", "_").lower()
            )
            if smart_model and clean_model in smart_model or smart_model in clean_model:
                return disk_smart

        return None

    @property
    def extra_state_attributes(self):
        """Add all disk attributes including SMART."""
        disks = self.coordinator.data.get("disks", {})
        disk = disks.get(self._disk_id)

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

            # Seek Error Rate (HDD)
            if disk_smart.get("seek_error_rate") is not None:
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
