"""Per-entry SMART polling cache."""


class SmartCache:
    def __init__(self, interval_minutes):
        self.interval_seconds = interval_minutes * 60
        self.last_refresh = None
        self.data = None

    def due(self, now):
        return self.last_refresh is None or now - self.last_refresh >= self.interval_seconds

    def should_refresh(self, enabled, now):
        return enabled and self.due(now)

    def accept(self, data, now):
        if not isinstance(data, dict) or "error" in data:
            return False
        self.data = data
        self.last_refresh = now
        return True

    def snapshot(self, node):
        return {node: self.data if self.data is not None else {}}
