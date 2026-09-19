"""Permanent PorterChain↔Fleetbase bond handshake.

SSOT: ``docs/FLEETBASE_PERMANENT_BOND.md``.

Jeff Dean design:
- Fleetbase files stay upstream; PorterChain never forks/absorbs them.
- The bond is identity (company UUID + API key) + contract (adapter) +
  resilience (circuit + RetryQueue) + self-heal (`pnpm fleetbase:bond`).
- Boot and diagnostics call ``verify_bond`` so a broken wire is visible
  immediately and the shared circuit resets when auth recovers.
"""

from __future__ import annotations

import logging
from typing import Any

from porterchain_api.config import Settings
from porterchain_api.services.fleetbase_integration import get_fleetbase_integration

logger = logging.getLogger(__name__)


def verify_fleetbase_bond(settings: Settings, *, reset_circuit: bool = True) -> dict[str, Any]:
    """Return adapter ``verify_bond`` result (or skipped when bridge off)."""
    if not settings.fleetbase_dispatch_bridge:
        return {
            "ok": True,
            "bonded": False,
            "skipped": True,
            "error": "bridge_disabled",
        }
    adapter = get_fleetbase_integration(settings, max_retries=0)
    return adapter.verify_bond(reset_circuit=reset_circuit)


def run_boot_handshake(settings: Settings) -> dict[str, Any]:
    """Best-effort lifespan handshake — never blocks API boot."""
    try:
        result = verify_fleetbase_bond(settings, reset_circuit=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("fleetbase_boot_handshake_error: %s", exc)
        return {"ok": False, "bonded": False, "error": str(exc)[:200]}

    if result.get("skipped"):
        logger.info("fleetbase_boot_handshake skipped (bridge disabled)")
    elif result.get("bonded"):
        logger.info(
            "fleetbase_boot_handshake bonded latency_ms=%s",
            result.get("latency_ms"),
        )
    else:
        logger.warning(
            "fleetbase_boot_handshake NOT bonded error=%s status=%s — "
            "run: pnpm fleetbase:bond",
            result.get("error"),
            result.get("status_code"),
        )
    return result
