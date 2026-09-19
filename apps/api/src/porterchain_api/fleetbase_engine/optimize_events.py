"""Optimize lifecycle DomainEvents + driver-scoped contract helpers (Phase 5c)."""

from __future__ import annotations

import logging
from typing import Any, Iterable

from porterchain_shared.events.catalog import DomainEventType

logger = logging.getLogger(__name__)

DEFAULT_OPTIMIZE_ENGINE = "vroom"


def emit_optimize_event(
    event_type: str,
    *,
    run_id: str,
    payload: dict[str, Any] | None = None,
    actor_type: str = "system",
    actor_id: str | None = None,
) -> None:
    """Best-effort bus publish — never fail the optimize path."""
    try:
        from porterchain_api.platform.bus import publish_domain_event

        publish_domain_event(
            event_type=event_type,
            aggregate_type="optimize_run",
            aggregate_id=run_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={"run_id": run_id, **(payload or {})},
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("optimize event %s failed: %s", event_type, exc)


def emit_enqueued(run_id: str, **payload: Any) -> None:
    emit_optimize_event(DomainEventType.OPTIMIZE_ENQUEUED, run_id=run_id, payload=payload)


def emit_ready(run_id: str, **payload: Any) -> None:
    emit_optimize_event(DomainEventType.OPTIMIZE_READY, run_id=run_id, payload=payload)


def emit_applied(run_id: str, **payload: Any) -> None:
    emit_optimize_event(DomainEventType.OPTIMIZE_APPLIED, run_id=run_id, payload=payload)


def emit_rejected(run_id: str, **payload: Any) -> None:
    emit_optimize_event(DomainEventType.OPTIMIZE_REJECTED, run_id=run_id, payload=payload)


def emit_rolled_back(run_id: str, **payload: Any) -> None:
    emit_optimize_event(DomainEventType.OPTIMIZE_ROLLED_BACK, run_id=run_id, payload=payload)


def foreign_order_ids(owned: Iterable[str], plan_order_ids: Iterable[str]) -> set[str]:
    """Return plan order ids not in the driver's owned set (cross-driver leak)."""
    owned_set = {str(x) for x in owned if x}
    return {str(x) for x in plan_order_ids if x and str(x) not in owned_set}


def assert_driver_scoped(
    owned: Iterable[str],
    plan_order_ids: Iterable[str],
    *,
    engine: str | None = None,
    allow_sandbox: bool = False,
    sandbox_ids: Iterable[str] | None = None,
) -> None:
    """CI contract: driver optimize never includes foreign or (by default) sandbox orders."""
    plan = [str(x) for x in plan_order_ids if x]
    if not allow_sandbox and sandbox_ids:
        sand = {str(s) for s in sandbox_ids}
        leaked = {x for x in plan if x in sand}
        if leaked:
            raise AssertionError(f"sandbox_order_ids_in_live_optimize:{sorted(leaked)}")
    foreign = foreign_order_ids(owned, plan)
    if foreign:
        raise AssertionError(f"cross_driver_order_ids:{sorted(foreign)}")
    if engine is not None and str(engine).lower() != DEFAULT_OPTIMIZE_ENGINE:
        raise AssertionError(f"engine_not_vroom:{engine}")
