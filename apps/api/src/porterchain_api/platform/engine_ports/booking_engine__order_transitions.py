"""Platform port for ``porterchain_api.booking_engine.order_transitions`` (§3.2.9 — no direct cross-engine imports).

Attributes resolve lazily on every access so callers see the owning module's live
objects (identical behaviour to importing it directly, including test patches).
"""

from __future__ import annotations

import importlib
from typing import Any

_TARGET = "porterchain_api.booking_engine.order_transitions"

__all__ = [
    "transition_order_state",
]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    target = importlib.import_module(_TARGET)
    try:
        return getattr(target, name)
    except AttributeError:
        return importlib.import_module(f"{_TARGET}.{name}")
