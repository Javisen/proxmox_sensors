"""Data models for the notification subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class NotificationEndpoint:
    """Normalized notification endpoint configuration."""

    name: str
    type: str
    details: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
