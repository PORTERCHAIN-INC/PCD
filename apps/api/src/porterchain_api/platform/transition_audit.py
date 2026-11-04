"""Audit rows for rejected state transitions.

Written to ``order_events`` in an independent short transaction so the record survives
the caller rolling back the failed request.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

log = logging.getLogger(__name__)


def log_rejected_transition(
    db: Session,
    *,
    order_id: str,
    event_type: str,
    from_state: str,
    to_state: str,
    actor_type: str = "system",
    actor_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    from porterchain_api.booking_models import OrderEvent

    try:
        own = sessionmaker(bind=db.get_bind(), expire_on_commit=False)()
        try:
            # Never wait on the caller's own locks; losing one audit row beats a hung request.
            own.execute(text("SET LOCAL lock_timeout = '2s'"))
            own.add(
                OrderEvent(
                    order_id=order_id,
                    event_type=event_type,
                    from_state=from_state,
                    to_state=to_state,
                    actor_type=actor_type,
                    actor_id=actor_id,
                    payload=payload or {},
                )
            )
            own.commit()
        finally:
            own.close()
    except Exception:  # pragma: no cover - the audit must never mask the real error
        log.warning("transition_rejection_not_logged", exc_info=True)
