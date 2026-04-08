"""Coordinator-agnostic notification manager."""

from __future__ import annotations

import logging

from .base import BaseNotifier
from .factory import create_notifier
from .models import NotificationEndpoint

_LOGGER = logging.getLogger(__name__)


class NotificationManager:
    """Manage a set of notification backends."""

    def __init__(self, endpoints: list[NotificationEndpoint]) -> None:
        self._endpoints = endpoints
        self._notifiers = self._build_notifiers(endpoints)

    @staticmethod
    def _build_notifiers(
        endpoints: list[NotificationEndpoint],
    ) -> list[tuple[NotificationEndpoint, BaseNotifier]]:
        """Instantiate enabled notifiers from endpoint definitions."""
        notifiers: list[tuple[NotificationEndpoint, BaseNotifier]] = []

        for endpoint in endpoints:
            if not endpoint.enabled:
                _LOGGER.debug(
                    "Skipping disabled notification endpoint '%s'", endpoint.name
                )
                continue

            try:
                notifiers.append((endpoint, create_notifier(endpoint)))
            except Exception as err:
                _LOGGER.exception(
                    "Failed to initialize notification endpoint '%s': %s",
                    endpoint.name,
                    err,
                )

        return notifiers

    async def send_all(self, title: str, message: str) -> None:
        """Send a notification to every initialized backend."""
        for endpoint, notifier in self._notifiers:
            try:
                await notifier.send(title, message)
            except Exception as err:
                _LOGGER.exception(
                    "Failed to send notification through '%s': %s",
                    endpoint.name,
                    err,
                )
