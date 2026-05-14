"""Data models for the notification subsystem."""

from __future__ import annotations

from typing import Any, Optional, Literal
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class NotificationEndpoint:
    """Normalized notification endpoint configuration."""

    name: str
    type: str
    details: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass(slots=True)
class NotificationEvent:
    """Portable notification event payload."""

    title: str
    message: str

    severity: Literal["info", "warning", "error"] = "info"
    source: str = "proxmox"

    metadata: dict[str, Any] = field(default_factory=dict)

    id: Optional[str] = None
    timestamp: Optional[datetime] = None
