"""Factory for creating notification backend instances."""

from __future__ import annotations

from typing import Callable

from .base import BaseNotifier
from .endpoints.gotify import GotifyNotifier
from .models import NotificationEndpoint

NotifierFactory = Callable[[NotificationEndpoint], BaseNotifier]

NOTIFIER_TYPES: dict[str, NotifierFactory] = {
    "gotify": GotifyNotifier,
}


def create_notifier(endpoint: NotificationEndpoint) -> BaseNotifier:
    """Create a notifier instance for the provided endpoint."""
    notifier_factory = NOTIFIER_TYPES.get(endpoint.type)
    if notifier_factory is None:
        raise ValueError(f"Unsupported notification endpoint type: {endpoint.type}")

    return notifier_factory(endpoint)
