"""Order state transitions per ORDER_LIFECYCLE.md."""

from sqlalchemy.orm import Session

from porterchain_api.booking_engine._core import emit_event
from porterchain_api.domain.states import OrderState, can_transition_order
from porterchain_api.models import Order, OrderEvent


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
    emit_event(
        db,
        event_type=event_type,
        aggregate_type="order",
        aggregate_id=order.id,
        correlation_id=order.quote_id,
        actor_type=actor_type,
        actor_id=actor_id,
        payload=payload,
    )
    db.commit()
    db.refresh(order)
    return order
