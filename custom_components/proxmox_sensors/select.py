"""Per-physical-disk SMART interval controls."""

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory

from .const import DOMAIN
from .logic.disk_smart import INTERVALS, preferences, with_preference
from .logic.physical_disk_type import TYPE_OPTIONS, selected_type, with_type


class PhysicalDiskSmartIntervalSelect(SelectEntity):
    _attr_has_entity_name = False
    _attr_name = "SMART interval"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "smart_disk_interval"
    _attr_options = ["inherit", *(str(minutes) for minutes in INTERVALS)]

    def __init__(self, hass, entry, coordinator, identifier):
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self.identifier = identifier
        self._attr_unique_id = f"{identifier}_smart_interval"
        self._attr_device_info = {"identifiers": {(DOMAIN, identifier)}}

    @property
    def current_option(self):
        global_minutes = self.entry.options.get(
            "smart_refresh_interval", self.entry.data.get("smart_refresh_interval", 1)
        )
        return str(preferences(self.entry.options, self.identifier, global_minutes)["interval"])

    async def async_select_option(self, option):
        value = "inherit" if option == "inherit" else int(option)
        if option not in self.options:
            raise ValueError("Invalid SMART interval")
        self.hass.config_entries.async_update_entry(
            self.entry,
            options=with_preference(self.entry.options, self.identifier, "interval", value),
        )
        self.coordinator.disk_smart_schedule.last_attempt.pop(self.identifier, None)
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()


class PhysicalDiskTypeSelect(SelectEntity):
    _attr_has_entity_name = False
    _attr_name = "Disk type"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "physical_disk_type"
    _attr_options = list(TYPE_OPTIONS)

    def __init__(self, hass, entry, identifier):
        self.hass = hass
        self.entry = entry
        self.identifier = identifier
        self._attr_unique_id = f"{identifier}_disk_type"
        self._attr_device_info = {"identifiers": {(DOMAIN, identifier)}}

    @property
    def current_option(self):
        return selected_type(self.entry.options, self.identifier)

    async def async_select_option(self, option):
        if option not in self.options:
            raise ValueError("Invalid Physical Disk type")
        if option == self.current_option:
            return
        self.hass.config_entries.async_update_entry(
            self.entry, options=with_type(self.entry.options, self.identifier, option),
        )
        await self.hass.config_entries.async_reload(self.entry.entry_id)


async def async_setup_entry(hass, entry, async_add_entities):
    if entry.data.get("platform_type") != "PVE":
        return
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator = runtime["coordinator"]
    added = set()

    def sync():
        for identifier in runtime.get("physical_disk_ids", {}).values():
            if identifier not in added:
                added.add(identifier)
                async_add_entities([
                    PhysicalDiskSmartIntervalSelect(hass, entry, coordinator, identifier),
                    PhysicalDiskTypeSelect(hass, entry, identifier),
                ])

    sync()
    runtime.setdefault("physical_disk_control_sync", []).append(sync)
    entry.async_on_unload(coordinator.async_add_listener(sync))
