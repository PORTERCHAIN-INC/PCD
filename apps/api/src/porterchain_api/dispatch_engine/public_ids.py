"""Fleetbase consumable public ids vs local fixture placeholders.

Live Fleetbase ids look like ``order_cuoncwg6zt`` or a UUID. Dev fixtures use
``fb-123`` / ``fb-1`` and must never be sent to the orchestrator.
"""

from __future__ import annotations

import re

_PLACEHOLDER_PREFIX = "fb-"
_PUBLIC = re.compile(r"^(order|vehicle|driver)_[a-z0-9]{6,}$", re.IGNORECASE)
_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def is_consumable_public_id(value: str | None) -> bool:
    if not value or not isinstance(value, str):
        return False
    stripped = value.strip()
    if not stripped or stripped.lower().startswith(_PLACEHOLDER_PREFIX):
        return False
    return bool(_PUBLIC.match(stripped) or _UUID.match(stripped))
