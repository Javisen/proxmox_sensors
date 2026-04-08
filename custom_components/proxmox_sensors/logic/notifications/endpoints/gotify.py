"""Gotify notification endpoint implementation."""

from __future__ import annotations

import logging

import aiohttp

from ..base import BaseNotifier

_LOGGER = logging.getLogger(__name__)


class GotifyNotifier(BaseNotifier):
    """Send notifications to a Gotify server."""

    async def send(self, title: str, message: str) -> None:
        """Send a message to the configured Gotify endpoint."""
        server = str(self.endpoint.details.get("server", "")).rstrip("/")
        token = self.endpoint.details.get("token")

        if not server:
            raise ValueError(
                f"Missing 'server' for Gotify endpoint '{self.endpoint.name}'"
            )

        if not token:
            raise ValueError(
                f"Missing 'token' for Gotify endpoint '{self.endpoint.name}'"
            )

        payload = {
            "title": title,
            "message": message,
        }

        priority = self.endpoint.details.get("priority")
        if priority is not None:
            payload["priority"] = priority

        headers = {
            "Content-Type": "application/json",
            "X-Gotify-Key": str(token),
        }

        url = f"{server}/message"

        _LOGGER.debug(
            "Sending Gotify notification via endpoint '%s' to '%s'",
            self.endpoint.name,
            url,
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                response.raise_for_status()
