#!/usr/bin/env python3
"""§3.3.1 — order state changes stay within ORDER_TRANSITIONS."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps/api/src/porterchain_api"

# Canonical E2E / ops paths must be valid consecutive transitions (ORDER_LIFECYCLE.md).
_CANONICAL_PATHS: tuple[list[str], ...] = (
    [
        "DISPATCH_READY",
        "DRIVER_ASSIGNED",
        "DRIVER_ACCEPTED",
        "DRIVER_EN_ROUTE",
        "AT_PICKUP",
        "PICKED_UP",
        "IN_TRANSIT",
        "AT_DESTINATION",
        "DELIVERED",
        "POD_COMPLETED",
        "INVOICED",
        "CLOSED",
    ],
    [
        "BOOKED",
        "DISPATCH_READY",
        "DRIVER_ASSIGNED",
        "DRIVER_ACCEPTED",
        "DRIVER_EN_ROUTE",
        "AT_PICKUP",
        "PICKED_UP",
        "IN_TRANSIT",
        "AT_DESTINATION",
        "DELIVERED",
        "POD_COMPLETED",
        "INVOICED",
    ],
    ["DELIVERED", "FAILED", "RETURN_TO_SENDER", "CLOSED"],
    ["DAMAGED", "CLAIM_OPEN", "REFUNDED"],
    ["LOST", "CLAIM_OPEN", "CLOSED"],
)

_ORDER_STATE_ASSIGN_ALLOWLIST: frozenset[str] = frozenset(
    {
        "booking_engine/order_transitions.py",
        # Sandbox PURGE_TEST bulk cancel — not a live lifecycle path.
        "merchant_engine/integrations_service.py",
    }
)


def _check_fleetbase_maps() -> list[str]:
    failures: list[str] = []
    sys.path.insert(0, str(API_SRC.parent))
    try:
        from porterchain_api.domain.order_lifecycle import (  # noqa: WPS433
            FLEETBASE_EVENT_TO_STATE,
            FLEETBASE_STATUS_TO_STATE,
            PORTERCHAIN_STATE_TO_FLEETBASE_STATUS,
        )
    except ImportError as exc:
        return [f"§3.3.1 cannot import lifecycle maps: {exc}"]
    finally:
        if str(API_SRC.parent) in sys.path:
            sys.path.remove(str(API_SRC.parent))

    sys.path.insert(0, str(API_SRC.parent))
    try:
        from porterchain_api.domain.states import OrderState  # noqa: WPS433
    except ImportError as exc:
        return [f"§3.3.1 cannot import OrderState: {exc}"]
    finally:
        if str(API_SRC.parent) in sys.path:
            sys.path.remove(str(API_SRC.parent))

    valid = {s.value for s in OrderState}
    for label, mapping in (
        ("FLEETBASE_EVENT_TO_STATE", FLEETBASE_EVENT_TO_STATE),
        ("FLEETBASE_STATUS_TO_STATE", FLEETBASE_STATUS_TO_STATE),
    ):
        for key, state in mapping.items():
            if state not in valid:
                failures.append(f"§3.3.1 {label}[{key!r}] maps to unknown state {state!r}")
    for state in PORTERCHAIN_STATE_TO_FLEETBASE_STATUS:
        if state not in valid:
            failures.append(f"§3.3.1 PORTERCHAIN_STATE_TO_FLEETBASE_STATUS key {state!r} unknown")
    return failures


def _check_canonical_paths() -> list[str]:
    failures: list[str] = []
    sys.path.insert(0, str(API_SRC.parent))
    try:
        from porterchain_api.domain.states import OrderState, can_transition_order  # noqa: WPS433
    except ImportError as exc:
        return [f"§3.3.1 cannot import can_transition_order: {exc}"]
    finally:
        if str(API_SRC.parent) in sys.path:
            sys.path.remove(str(API_SRC.parent))

    for path in _CANONICAL_PATHS:
        states = [OrderState(value) for value in path]
        for left, right in zip(states, states[1:], strict=False):
            if not can_transition_order(left, right):
                failures.append(f"§3.3.1 canonical path invalid: {left.value} -> {right.value}")
    return failures


def _check_single_state_writer() -> list[str]:
    failures: list[str] = []
    pattern = re.compile(r"\border\.state\s*=(?!=)")
    for path in sorted(API_SRC.rglob("*.py")):
        rel = str(path.relative_to(API_SRC))
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not pattern.search(text):
            continue
        if rel in _ORDER_STATE_ASSIGN_ALLOWLIST:
            continue
        failures.append(f"§3.3.1 order.state assignment outside transition module: {rel}")
    return failures


def main() -> int:
    failures = _check_fleetbase_maps() + _check_canonical_paths() + _check_single_state_writer()
    if failures:
        print("Order transition guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(
        f"Order transition guard passed (§3.3.1 — {len(_CANONICAL_PATHS)} canonical paths, "
        "fleetbase maps aligned, single state writer)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
