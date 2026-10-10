"""Equipment matching: one shared vehicle field (``vehicles.capabilities``) and one order flag.

Order flag: ``compliance_metadata.requires_liftgate`` (set by booking, imports and pricing).
Vehicle flag: ``"liftgate" in vehicles.capabilities``. Liftgate is a hard constraint.
"""

from __future__ import annotations

from typing import Any

LIFTGATE = "liftgate"


def order_needs_liftgate(order: Any) -> bool:
    meta = getattr(order, "compliance_metadata", None)
    return bool(isinstance(meta, dict) and meta.get("requires_liftgate"))


def has_liftgate(capabilities: Any) -> bool:
    return isinstance(capabilities, list | tuple | set) and LIFTGATE in capabilities
