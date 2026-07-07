"""Order state transitions per ORDER_LIFECYCLE.md."""

from sqlalchemy.orm import Session

from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine._core import publish_recorded_event, record_domain_event, _event_fields
from porterchain_api.domain.states import OrderState, can_transition_order
from porterchain_api.booking_engine.row_locks import lock_order
from porterchain_api.models import Order, OrderEvent


def transition_to_dispatch_ready(
    db: Session,
    order: Order,
    *,
    event_type: str = E.ORDER_DISPATCH_READY,
    actor_type: str = "system",
    actor_id: str | None = None,
    payload: dict | None = None,
) -> Order:
    """Emit dispatch requested, then transition to DISPATCH_READY (Fleetbase sync follows)."""
    requested = _event_fields(
        event_type=E.ORDER_DISPATCH_REQUESTED,
        aggregate_type="order",
        aggregate_id=order.id,
        correlation_id=order.quote_id,
        actor_type=actor_type,
        actor_id=actor_id,
        payload=payload or {},
    )
    record_domain_event(db, **requested)
    db.commit()
    publish_recorded_event(**requested)
    return transition_order_state(
        db,
        order,
        OrderState.DISPATCH_READY,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        payload=payload,
    )


def transition_order_state(
    db: Session,
    order: Order,
    to_state: OrderState,
    *,
    event_type: str,
    actor_type: str = "system",
    actor_id: str | None = None,
    payload: dict | None = None,
) -> Order:
    locked = lock_order(db, order.id)
    if not locked:
        raise LookupError("order_not_found")
    order = locked
    from_state = OrderState(order.state)
    if not can_transition_order(from_state, to_state):
        raise ValueError(f"Invalid order transition {from_state} -> {to_state}")
    order.state = to_state.value
    db.add(
        OrderEvent(
            order_id=order.id,
            event_type=event_type,
            from_state=from_state.value,
            to_state=to_state.value,
            actor_type=actor_type,
            actor_id=actor_id,
            correlation_id=order.quote_id,
            payload=payload or {},
        )
    )
    event = _event_fields(
        event_type=event_type,
        aggregate_type="order",
        aggregate_id=order.id,
        correlation_id=order.quote_id,
        actor_type=actor_type,
        actor_id=actor_id,
        payload=payload,
    )
    record_domain_event(db, **event)
    db.commit()
    publish_recorded_event(**event)
    db.refresh(order)
    return order
