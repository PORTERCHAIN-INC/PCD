"""SLA monitor + per-order SLA helpers."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from porterchain_api.booking_engine.order_sla import DEFAULT_INSTANT_SLA_HOURS, order_sla_status
from porterchain_api.models import Order
from porterchain_api.order_engine.buckets import IN_FLIGHT, WAITING

from porterchain_api.admin_engine.control_tower._helpers import now_utc


class SlaMixin:
    def _instant_sla_hours(self, db: Session) -> float:
        from porterchain_api.admin_engine.settings_service import AdminSettingsService

        cfg = AdminSettingsService().get_config_value(db, "settings_booking")
        if isinstance(cfg, dict) and cfg.get("instant_delivery_sla_hours") is not None:
            try:
                return max(float(cfg["instant_delivery_sla_hours"]), 0.25)
            except (TypeError, ValueError):
                pass
        return float(DEFAULT_INSTANT_SLA_HOURS)

    def _sla_status(
        self,
        order: Order,
        now: datetime,
        *,
        instant_sla_hours: float | None = None,
    ) -> str:
        return order_sla_status(
            order,
            now,
            instant_sla_hours=instant_sla_hours
            if instant_sla_hours is not None
            else DEFAULT_INSTANT_SLA_HOURS,
        )

    def sla_monitor(self, db: Session, *, limit: int = 200) -> dict:
        now = now_utc()
        merchants = self._merchant_names(db)
        drivers = self._driver_names(db)
        hours = self._instant_sla_hours(db)
        rows = db.query(Order).filter(Order.state.in_(WAITING + IN_FLIGHT)).all()
        at_risk: list[dict] = []
        breached: list[dict] = []
        for o in rows:
            status = self._sla_status(o, now, instant_sla_hours=hours)
            card = self._order_card(o, merchants, drivers, now, instant_sla_hours=hours)
            if status == "breached":
                breached.append(card)
            elif status == "at_risk":
                at_risk.append(card)
        breached.sort(key=lambda c: c["eta"] or "")
        at_risk.sort(key=lambda c: c["eta"] or "")
        return {
            "breached": breached[:limit],
            "at_risk": at_risk[:limit],
            "breached_count": len(breached),
            "at_risk_count": len(at_risk),
        }
