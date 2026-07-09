"""Feature store interface — Phase 2 scaffold (§4.1.4)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.intelligence_engine import phase2_intelligence_enabled


def get_order_features(db: Session, order_id: str, *, flags: dict[str, bool]) -> dict[str, Any]:
    """Return derived features for batch models; empty when Phase 2 off."""
    if not phase2_intelligence_enabled(flags):
        return {"order_id": order_id, "features": {}, "status": "phase2_disabled"}

    from porterchain_api.models import AnalyticsStopLeg

    legs = (
        db.query(AnalyticsStopLeg)
        .filter(AnalyticsStopLeg.order_id == order_id)
        .order_by(AnalyticsStopLeg.leg_index)
        .all()
    )
    return {
        "order_id": order_id,
        "features": {
            "stop_leg_count": len(legs),
            "last_lat": legs[-1].lat if legs else None,
            "last_lng": legs[-1].lng if legs else None,
        },
        "status": "ok",
    }
