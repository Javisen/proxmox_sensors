"""Per-physical-disk SMART cadence and retained observations."""

from __future__ import annotations


PREFERENCES_KEY = "physical_disk_smart_v2"
INTERVALS = (1, 5, 10, 15, 30, 60)


def preferences(options, identifier, global_interval, global_enabled=True):
    if global_interval not in INTERVALS:
        global_interval = 10
    saved = (options.get(PREFERENCES_KEY) or {}).get(identifier, {})
    interval = saved.get("interval", "inherit")
    if interval != "inherit" and interval not in INTERVALS:
        interval = "inherit"
    return {
        "enabled": saved.get("enabled", global_enabled) is True,
        "interval": interval,
        "minutes": global_interval if interval == "inherit" else interval,
        "protect_standby": saved.get("protect_standby", True) is not False,
    }


def with_preference(options, identifier, key, value):
    if key == "interval" and value != "inherit" and value not in INTERVALS:
        raise ValueError("Invalid SMART interval")
    if key in {"enabled", "protect_standby"} and type(value) is not bool:
        raise ValueError("Invalid SMART switch state")
    if key not in {"interval", "enabled", "protect_standby"}:
        raise ValueError("Invalid SMART preference")
    updated = dict(options)
    all_disks = dict(updated.get(PREFERENCES_KEY) or {})
    one = dict(all_disks.get(identifier) or {})
    one[key] = value
    all_disks[identifier] = one
    updated[PREFERENCES_KEY] = all_disks
    return updated


class DiskSmartSchedule:
    def __init__(self):
        self.last_attempt = {}
        self.last_good = {}
        self.status = {}
        self.generation = {}

    def invalidate(self, identifier):
        self.generation[identifier] = self.generation.get(identifier, 0) + 1
        self.last_attempt.pop(identifier, None)
        self.last_good.pop(identifier, None)
        self.status.pop(identifier, None)

    def due(self, identifier, now, minutes, enabled):
        previous = self.last_attempt.get(identifier)
        return enabled and (previous is None or now - previous >= minutes * 60)

    def accept(self, identifier, response, now, timestamp):
        self.last_attempt[identifier] = now
        if not isinstance(response, dict):
            self.status[identifier] = "error"
            return
        status = response.get("status")
        self.status[identifier] = status if status in {"ok", "standby", "unsupported", "error"} else "error"
        if status == "ok" and isinstance(response.get("data"), dict):
            self.last_good[identifier] = (response["data"], timestamp)

    def accept_if_current(self, identifier, response, now, timestamp, generation, enabled):
        if not enabled or generation != self.generation.get(identifier, 0):
            return False
        self.accept(identifier, response, now, timestamp)
        return True

    def snapshot(self, identifier, now, enabled):
        last = self.last_good.get(identifier) if enabled else None
        return {
            "data": last[0] if last else None,
            "last_read": last[1] if last else None,
            "age_seconds": max(0, int(now - last[1])) if last else None,
            "status": "disabled" if not enabled else self.status.get(identifier, "pending"),
        }
