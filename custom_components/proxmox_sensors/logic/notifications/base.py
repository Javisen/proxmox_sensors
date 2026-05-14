"""Base classes for notification delivery backends."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import NotificationEndpoint


class BaseNotifier(ABC):
    """Abstract base class for notification endpoint implementations."""

    def __init__(self, endpoint: NotificationEndpoint) -> None:
        self.endpoint = endpoint

    @abstractmethod
    async def send(self, title: str, message: str) -> None:
        """Send a notification using the configured endpoint."""
