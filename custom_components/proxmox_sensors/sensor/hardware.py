"""Hardware sensors for Proxmox Extended Sensors."""

from .base import ProxmoxBaseSensor
from ..const import DOMAIN


class ProxmoxHardwareSensor(ProxmoxBaseSensor):
    def __init__(self, coordinator, sensor_key, node):

        self._key = sensor_key.lower()

        self._is_chipset = "pch" in self._key

        # CPU grouping
        self._is_cpu = any(
            x in self._key
            for x in [
                "coretemp",
                "k10temp",
                "zenpower",
                "package",
                "cpu",
                "core",
                "tctl",
                "tdie",
                "tccd",
            ]
        )

        if self._is_cpu:
            name = f"CPU Temperature"
            unique_id = f"proxmox_cpu_temp_{node}"
            unit = "°C"
            sensor_id = "cpu_temperature"
        else:
            name = sensor_key
            clean_id = self._key.replace(" ", "_").replace("-", "_")
            unique_id = f"proxmox_hw_{node}_{clean_id}"
            unit = "°C"
            sensor_id = sensor_key

        super().__init__(coordinator, sensor_id, name, unit, unique_id, node)

        self._attr_device_class = "temperature"
        self._attr_state_class = "measurement"
        self._attr_icon = "mdi:thermometer-lines"

    # ================= MAIN VALUE ==================

    def _get_value(self):
        hw = self.coordinator.data.get("hardware", {})

        if self._is_cpu:
            package_temp = None
            cores = []
            cpu_critical = None

            for key, val in hw.items():
                kl = key.lower()

                # -------- CASE 1: Dict type structure --------
                if isinstance(val, dict):

                    # 1. Detect package/core using primary KEY (flattened support)
                    if any(x in kl for x in ["package", "tctl", "tdie"]):
                        v = self._parse(val)
                        if v is not None:
                            package_temp = v

                    elif "core" in kl:
                        v = self._parse(val)
                        if v is not None:
                            cores.append(v)

                    # 2. Look for internal metrics (input, crit, etc.)
                    for k, v in val.items():
                        try:
                            kl2 = k.lower()
                            f = float(v)

                            # critical temp
                            if "crit" in kl2:
                                if cpu_critical is None and 1 < f < 145:
                                    cpu_critical = round(f, 1)

                        except (ValueError, TypeError):
                            continue

                # -------- CASE 2: loose values --------
                else:
                    if any(x in kl for x in ["package", "tctl", "tdie"]):
                        v = self._parse(val)
                        if v is not None:
                            package_temp = v

                    elif "core" in kl:
                        v = self._parse(val)
                        if v is not None:
                            cores.append(v)

            # -------- priority --------
            if package_temp is not None:
                return package_temp

            if cores:
                return round(sum(cores) / len(cores), 1)

            return None

        # -------- Non-CPU --------
        return self._parse(hw.get(self._key))

    # ================= ATTRIBUTES ==================

    @property
    def extra_state_attributes(self):
        hw = self.coordinator.data.get("hardware", {})

        attrs = {}

        # ---------------- CPU ----------------
        if self._is_cpu:
            cpu_critical = None
            package_temp = None

            for key, val in hw.items():
                kl = key.lower()

                if any(x in kl for x in ["package", "tctl", "tdie"]):
                    v = self._parse(val)
                    if v is not None:
                        attrs["package"] = v
                        package_temp = v

                if "core" in kl or "tccd" in kl:
                    v = self._parse(val)
                    if v is not None:
                        attrs[kl.replace(" ", "_").replace("-", "_")] = v

                if isinstance(val, dict):
                    for sub_key, sub_val in val.items():
                        skl = sub_key.lower()

                        # -------- Core temps --------
                        if "core" in skl:
                            v = self._parse(sub_val)
                            if v is not None:
                                attrs[skl.replace(" ", "_")] = v

                        # -------- Package --------
                        if any(x in skl for x in ["package", "tctl", "tdie"]):
                            v = self._parse(sub_val)
                            if v is not None:
                                attrs["package"] = v
                                package_temp = v

                        # -------- Critical temp --------
                        try:
                            if "crit" in skl and cpu_critical is None:
                                f = float(sub_val)
                                if 1 < f < 145:
                                    cpu_critical = round(f, 1)
                        except (ValueError, TypeError):
                            pass

                        if isinstance(sub_val, dict):
                            for k, v in sub_val.items():
                                try:
                                    if "crit" in k.lower() and cpu_critical is None:
                                        f = float(v)
                                        if 1 < f < 145:
                                            cpu_critical = round(f, 1)
                                except (ValueError, TypeError):
                                    continue

            if cpu_critical is not None:
                attrs["cpu_critical_temp"] = cpu_critical

            if cpu_critical is not None and package_temp is not None:
                attrs["thermal_margin"] = round(cpu_critical - package_temp, 1)

        # ---------------- CHIPSET ----------------
        elif self._is_chipset:
            acpi_values = []

            for key, val in hw.items():
                kl = key.lower()

                if "acpitz" in kl:
                    v = self._parse(val)
                    if v is not None:
                        acpi_values.append(v)

            if acpi_values:
                attrs["acpi_temp"] = round(sum(acpi_values) / len(acpi_values), 1)

        return attrs

    # ================= HELPERS ==================

    def _parse(self, val):
        try:
            # If dict (lm-sensors style)
            if isinstance(val, dict):
                for k, v in val.items():
                    if "input" in k.lower():
                        val = v
                        break

            f = float(val)
            if 1 < f < 145:
                return round(f, 1)
        except Exception:
            pass

        return None


class ProxmoxHardwareNVMeSensor(ProxmoxBaseSensor):
    def __init__(self, coordinator, device_prefix, node):
        self._device_prefix = device_prefix.lower()
        self._node = node

        # Nombre provisional (fallback)
        display_name = device_prefix.replace("nvme-pci-", "NVMe ").replace("_", " ")
        name = f"{display_name} ({node})"
        unique_id = f"proxmox_nvme_{device_prefix}_{node}"

        super().__init__(coordinator, "nvme_temperature", name, "°C", unique_id, node)

        smart = self._get_smart_info()

        if smart:
            model = smart.get("model", "NVMe")
            capacity = smart.get("capacity_gb")

            if capacity:
                display_name = f"{model} {int(capacity)}GB"
            else:
                display_name = model

            # dynamic name
            self._attr_name = f"{display_name} ({node})"

        self._attr_device_class = "temperature"
        self._attr_state_class = "measurement"
        self._attr_icon = "mdi:thermometer-lines"

    def _get_smart_info(self):
        smart_data = self.coordinator.data.get("smart", {}).get(self._node, {})

        if self._device_prefix in smart_data:
            disk = smart_data[self._device_prefix]
            if disk.get("device_type") == "nvme":
                return disk

        nvme_disks = [
            disk for disk in smart_data.values() if disk.get("device_type") == "nvme"
        ]

        if len(nvme_disks) == 1:
            return nvme_disks[0]

        return None

    # ================= MAIN VALUE ==================

    def _get_value(self):
        hw = self.coordinator.data.get("hardware", {})

        #  1: nested (nvme-pci-xxxx → Composite / Sensor X)
        for key, val in hw.items():
            if not self._matches_hardware_key(key):
                continue

            if isinstance(val, dict):
                for sub_name, sub_val in val.items():
                    if "composite" in sub_name.lower():
                        v = self._extract_current(sub_val)
                        if v is not None:
                            return v

                for sub_val in val.values():
                    v = self._extract_current(sub_val)
                    if v is not None:
                        return v

        #  2: flatten
        for key, val in hw.items():
            if self._matches_hardware_key(key) and "composite" in key.lower():
                return self._extract_current(val)

        for key, val in hw.items():
            if self._matches_hardware_key(key):
                v = self._extract_current(val)
                if v is not None:
                    return v

        smart = self._get_smart_info()
        if smart:
            v = self._extract_current(smart.get("temperature_c"))
            if v is not None:
                return v

        return None

    # ================= ATTRIBUTES ==================

    @property
    def extra_state_attributes(self):
        hw = self.coordinator.data.get("hardware", {})
        attrs = {}
        temps = []

        for key, val in hw.items():
            if not self._matches_hardware_key(key):
                continue

            #  1: nested
            if isinstance(val, dict) and any(isinstance(v, dict) for v in val.values()):
                for sub_name, sub_val in val.items():

                    raw_name = sub_name.strip().lower()

                    # -------- Naming --------
                    if not raw_name or raw_name == "composite":
                        display_name = "Composite Temp"

                    elif "sensor" in raw_name or "temp" in raw_name:
                        import re

                        match = re.search(r"(\d+)", raw_name)

                        if match:
                            num = int(match.group(1))
                            if num == 1:
                                display_name = "NAND Temp"
                            elif num == 2:
                                display_name = "Controller Temp"
                            else:
                                display_name = f"Sensor {num}"
                        else:
                            display_name = sub_name.replace("_", " ").title()
                    else:
                        display_name = sub_name.replace("_", " ").title()

                    v = self._extract_current(sub_val)
                    if v is not None:
                        attrs[display_name] = v
                        temps.append(v)

                continue

            #  2: flatten
            raw_name = key.replace(self._device_prefix, "").strip("_")
            kl = raw_name.lower()

            if not raw_name or kl == "composite":
                display_name = "Composite Temp"

            elif "sensor" in kl or "temp" in kl:
                import re

                match = re.search(r"(\d+)", kl)

                if match:
                    num = int(match.group(1))
                    if num == 1:
                        display_name = "NAND Temp"
                    elif num == 2:
                        display_name = "Controller Temp"
                    else:
                        display_name = f"Sensor {num}"
                else:
                    display_name = raw_name.replace("_", " ").title()
            else:
                display_name = raw_name.replace("_", " ").title()

            # -------- Parse --------
            if isinstance(val, dict):
                parsed = {}

                for k, v in val.items():
                    try:
                        f = float(v)
                        kl = k.lower()

                        if "input" in kl:
                            parsed["current"] = round(f, 1)
                        elif "max" in kl or "high" in kl:
                            parsed["max"] = round(f, 1)
                        elif "crit" in kl:
                            parsed["critical"] = round(f, 1)
                        elif "min" in kl or "low" in kl:
                            parsed["min"] = round(f, 1)

                    except (ValueError, TypeError):
                        continue

                if parsed:
                    for sub_key, sub_val in parsed.items():
                        attrs[f"{display_name}_{sub_key}"] = sub_val

                    if "current" in parsed:
                        temps.append(parsed["current"])

            else:
                v = self._extract_current(val)
                if v is not None:
                    attrs[display_name] = v
                    temps.append(v)

        # -------- Max temp global --------
        if temps:
            attrs["max_temp"] = round(max(temps), 1)

        smart = self._get_smart_info()
        if smart and smart.get("temperature_c") is not None:
            attrs["SMART Temp"] = smart.get("temperature_c")

        return attrs

    # ================= HELPERS ==================

    def _matches_hardware_key(self, key):
        normalized_key = key.lower().replace("_", "-")
        normalized_prefix = self._device_prefix.replace("_", "-")

        return normalized_prefix in normalized_key

    def _extract_current(self, val):
        try:
            if isinstance(val, dict):
                for k, v in val.items():
                    if "input" in k.lower():
                        val = v
                        break

            f = float(val)
            if 1 < f < 145:
                return round(f, 1)

        except (ValueError, TypeError):
            pass

        return None
