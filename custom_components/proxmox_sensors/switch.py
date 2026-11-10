"""Per-physical-disk SMART switches."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DOMAIN
from .logic.disk_smart import preferences, with_preference


class PhysicalDiskSmartSwitch(SwitchEntity):
    _attr_has_entity_name = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hass, entry, coordinator, identifier, key):
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self.identifier = identifier
        self.key = key
        self._attr_unique_id = f"{identifier}_{key}"
        self._attr_translation_key = (
            "smart_disk_monitoring" if key == "enabled" else "smart_disk_standby"
        )
        self._attr_name = (
            "SMART monitoring" if key == "enabled" else "Protect HDD standby"
        )
        self._attr_device_info = {"identifiers": {(DOMAIN, identifier)}}

    @property
    def is_on(self):
        global_minutes = self.entry.options.get(
            "smart_refresh_interval", self.entry.data.get("smart_refresh_interval", 1)
        )
        return preferences(
            self.entry.options, self.identifier, global_minutes,
            self.entry.options.get(
                "enable_smart_monitoring",
                self.entry.data.get("enable_smart_monitoring", True),
            ),
        )[self.key]

    async def _set(self, value):
        self.hass.config_entries.async_update_entry(
            self.entry,
            options=with_preference(self.entry.options, self.identifier, self.key, value),
        )
        if self.key == "enabled" and not value:
            self.coordinator.disk_smart_schedule.invalidate(self.identifier)
            data = self.coordinator.data or {}
            snapshots = dict(data.get("physical_smart", {}))
            snapshots[self.identifier] = {
                "data": None, "last_read": None, "age_seconds": None,
                "status": "disabled",
            }
            self.coordinator.async_set_updated_data({**data, "physical_smart": snapshots})
        else:
            self.coordinator.disk_smart_schedule.last_attempt.pop(self.identifier, None)
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._set(True)

    async def async_turn_off(self, **kwargs):
        await self._set(False)


async def async_setup_entry(hass, entry, async_add_entities):
    if entry.data.get("platform_type") != "PVE":
        return
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator = runtime["coordinator"]
    added = set()

    def sync():
        registry = er.async_get(hass)
        devices = dr.async_get(hass)
        for path, identifier in runtime.get("physical_disk_ids", {}).items():
            kind = str(coordinator.data.get("disks", {}).get(path, {}).get("type") or "").lower()
            if kind in ("ssd", "nvme") and coordinator.data.get(
                "_cleanup_confirmed", {}
            ).get("node_disks") is True:
                row_id = registry.async_get_entity_id(
                    "switch", DOMAIN, f"{identifier}_protect_standby",
                )
                device = devices.async_get_device_by_identifier(
                    (DOMAIN, identifier), config_entry_id=entry.entry_id,
                )
                row = registry.async_get(row_id) if row_id else None
                if (row is not None and device is not None
                        and row.config_entry_id == entry.entry_id
                        and row.device_id in (None, device.id)):
                    registry.async_remove(row_id)
            if identifier not in added:
                added.add(identifier)
                controls = [PhysicalDiskSmartSwitch(
                    hass, entry, coordinator, identifier, "enabled",
                )]
                if kind not in ("ssd", "nvme"):
                    controls.append(PhysicalDiskSmartSwitch(
                        hass, entry, coordinator, identifier, "protect_standby",
                    ))
                async_add_entities(controls)

    sync()
    runtime.setdefault("physical_disk_control_sync", []).append(sync)
    entry.async_on_unload(coordinator.async_add_listener(sync))
