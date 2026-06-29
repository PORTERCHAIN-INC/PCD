"""Handler registry — modules subscribe without depending on each other."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

EventHandler = Callable[[dict[str, Any]], None]


class HandlerRegistry:
    """Maps event types (and wildcards) to handler callables."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}
        self._wildcard_handlers: list[tuple[re.Pattern[str], EventHandler]] = []

    def subscribe(self, event_pattern: str, handler: EventHandler) -> None:
        if "*" in event_pattern:
            pattern = re.compile("^" + re.escape(event_pattern).replace(r"\*", ".*") + "$")
            self._wildcard_handlers.append((pattern, handler))
            logger.info("subscribed wildcard handler %s -> %s", event_pattern, getattr(handler, "__name__", handler))
            return
        self._handlers.setdefault(event_pattern, []).append(handler)
        logger.info("subscribed handler %s -> %s", event_pattern, getattr(handler, "__name__", handler))

    def handlers_for(self, event_type: str) -> list[EventHandler]:
        matched = list(self._handlers.get(event_type, []))
        for pattern, handler in self._wildcard_handlers:
            if pattern.match(event_type):
                matched.append(handler)
        return matched

    def clear(self) -> None:
        self._handlers.clear()
        self._wildcard_handlers.clear()


_global_registry = HandlerRegistry()


def get_handler_registry() -> HandlerRegistry:
    return _global_registry
