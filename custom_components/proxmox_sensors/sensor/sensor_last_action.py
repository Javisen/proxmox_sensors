"""LAST ACTION for Proxmox Extended Sensors."""

import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import callback

_logger = logging.getLogger(__name__)


class PBSLastActionSensor(CoordinatorEntity, SensorEntity):

    def __init__(self, coordinator, datastore):
        super().__init__(coordinator)

        self._datastore = datastore

        self._attr_name = "Last Action"
        self._attr_unique_id = f"{datastore.lower()}_last_action"
        self._attr_should_poll = False

        self._state = STATE_UNKNOWN
        self._attr_extra_state_attributes = {}

        self._attr_device_info = {
            "identifiers": {("proxmox_sensors", f"maintenance_{datastore}")},
            "name": f"Maintenance: {datastore}",
            "manufacturer": "Proxmox",
            "model": "Proxmox Backup Server",
        }

    @property
    def state(self):
        return self._state

    def _map_task_type(self, task_type: str) -> str:
        task_type = (task_type or "").lower()

        mapping = {
            "garbage_collection": "GC",
            "prune": "Prune",
            "verify": "Verify",
            "sync": "Sync",
        }

        return mapping.get(task_type, task_type.capitalize())

    @callback
    def _handle_coordinator_update(self):
        tasks = self.coordinator.data.get("pbs_tasks", [])

        tasks = [
            t
            for t in tasks
            if (
                t.get("datastore") == self._datastore
                or (t.get("worker_id") or "").startswith(self._datastore)
            )
        ]

        if not tasks:
            self._state = "Idle"
            self.async_write_ha_state()
            return

        latest_task = max(tasks, key=lambda t: t.get("starttime", 0))

        raw_type = (
            latest_task.get("type") or latest_task.get("worker_type") or "unknown"
        )

        self._state = self._map_task_type(raw_type)

        self._attr_extra_state_attributes = {
            "raw_type": raw_type,
            "status": latest_task.get("status"),
            "starttime": latest_task.get("starttime"),
        }

        self.async_write_ha_state()
