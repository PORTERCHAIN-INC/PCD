"""Alerts, events, and insight overlays for the live operations map."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.control_tower_service import HIGH_PRIORITY_CENTS, IN_FLIGHT, WAITING
from porterchain_api.admin_engine.live_map_helpers import _coords, _haversine_km, _parse_iso_naive
from porterchain_api.admin_models import Claim, Driver, SupportTicket
from porterchain_api.domain.claims import claim_number
from porterchain_api.domain.support import ticket_number
from porterchain_api.models import DomainEvent, Order, OrderException


OPEN_TICKET_STATUSES = ("open", "in_progress", "escalated")
OPEN_CLAIM_STATUSES = ("open", "investigating")


class LiveMapOverlaysMixin:
    def _build_alerts(self, db: Session, now: datetime) -> list[dict]:
        alerts: list[dict] = []
        # Late deliveries
        late_orders = (
            db.query(Order)
            .filter(Order.state.in_(IN_FLIGHT), Order.scheduled_at < now)
            .limit(50)
            .all()
        )
        for o in late_orders:
            coords = _coords(o.dropoff) or _coords(o.pickup)
            alerts.append(
                {
                    "id": f"late-{o.id}",
                    "alert_type": "late_delivery",
                    "severity": "critical",
                    "title": "Late delivery",
                    "message": f"{o.tracking_number} is past scheduled ETA",
                    "entity_type": "order",
                    "entity_id": o.id,
                    "location": {"lat": coords[0], "lng": coords[1]} if coords else None,
                    "created_at": o.scheduled_at.isoformat() if o.scheduled_at else None,
                }
            )
        # Offline drivers with active orders — one alert per driver (not per order)
        active = db.query(Order).filter(Order.state.in_(IN_FLIGHT), Order.assigned_driver_id.isnot(None)).all()
        driver_ids = {o.assigned_driver_id for o in active if o.assigned_driver_id}
        drivers = (
            {d.id: d for d in db.query(Driver).filter(Driver.id.in_(driver_ids)).all()}
            if driver_ids
            else {}
        )
        offline_orders_by_driver: dict[str, tuple[Driver, list[Order]]] = {}
        for o in active:
            if not o.assigned_driver_id:
                continue
            drv = drivers.get(o.assigned_driver_id)
            if drv and not drv.is_online:
                entry = offline_orders_by_driver.get(drv.id)
                if entry is None:
                    offline_orders_by_driver[drv.id] = (drv, [o])
                else:
                    entry[1].append(o)
        for drv_id, (drv, orders) in offline_orders_by_driver.items():
            tracking = ", ".join(o.tracking_number for o in orders[:3] if o.tracking_number)
            if len(orders) > 3:
                tracking = f"{tracking} (+{len(orders) - 3} more)" if tracking else f"{len(orders)} active orders"
            alerts.append(
                {
                    "id": f"offline-driver-{drv_id}",
                    "alert_type": "driver_offline",
                    "severity": "warning",
                    "title": "Driver offline",
                    "message": (
                        f"{drv.full_name} is offline with active order {tracking}"
                        if len(orders) == 1
                        else f"{drv.full_name} is offline with active orders: {tracking}"
                    ),
                    "entity_type": "driver",
                    "entity_id": drv_id,
                    "location": None,
                    "created_at": now.isoformat(),
                }
            )
        # Open exceptions
        for e, order in (
            db.query(OrderException, Order)
            .join(Order, Order.id == OrderException.order_id)
            .filter(OrderException.status == "open")
            .limit(20)
            .all()
        ):
            coords = _coords(order.dropoff) or _coords(order.pickup)
            alerts.append(
                {
                    "id": f"exception-{e.id}",
                    "alert_type": "incident",
                    "severity": "warning",
                    "title": f"Exception: {e.type}",
                    "message": f"Order {order.tracking_number}",
                    "entity_type": "order",
                    "entity_id": order.id,
                    "location": {"lat": coords[0], "lng": coords[1]} if coords else None,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
            )
        # Open claims
        for c in db.query(Claim).filter(Claim.status.in_(OPEN_CLAIM_STATUSES)).limit(15).all():
            alerts.append(
                {
                    "id": f"claim-{c.id}",
                    "alert_type": "claim",
                    "severity": "info",
                    "title": f"Open claim: {c.claim_type}",
                    "message": c.description or "Claim requires review",
                    "entity_type": "claim",
                    "entity_id": c.id,
                    "location": None,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
            )
        # Open support tickets
        for t in (
            db.query(SupportTicket)
            .filter(SupportTicket.status.in_(OPEN_TICKET_STATUSES))
            .order_by(SupportTicket.updated_at.desc())
            .limit(20)
            .all()
        ):
            sev = "critical" if t.priority in ("urgent", "critical", "high") else "info"
            alerts.append(
                {
                    "id": f"support-{t.id}",
                    "alert_type": "support",
                    "severity": sev,
                    "title": ticket_number(t.id),
                    "message": t.subject,
                    "entity_type": "ticket",
                    "entity_id": t.id,
                    "location": None,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
            )
        # High priority in-flight
        for o in db.query(Order).filter(Order.state.in_(IN_FLIGHT), Order.amount_cents >= HIGH_PRIORITY_CENTS).limit(10).all():
            coords = _coords(o.pickup)
            alerts.append(
                {
                    "id": f"priority-{o.id}",
                    "alert_type": "high_priority",
                    "severity": "warning",
                    "title": "High priority order",
                    "message": o.tracking_number,
                    "entity_type": "order",
                    "entity_id": o.id,
                    "location": {"lat": coords[0], "lng": coords[1]} if coords else None,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                }
            )
        seen_ids: set[str] = set()
        unique_alerts: list[dict] = []
        for alert in alerts:
            aid = alert["id"]
            if aid in seen_ids:
                continue
            seen_ids.add(aid)
            unique_alerts.append(alert)
        return unique_alerts[:100]

    def _build_support_tickets(self, db: Session, *, limit: int = 40) -> list[dict]:
        rows = (
            db.query(SupportTicket)
            .filter(SupportTicket.status.in_(OPEN_TICKET_STATUSES))
            .order_by(SupportTicket.updated_at.desc())
            .limit(limit)
            .all()
        )
        out: list[dict] = []
        for t in rows:
            out.append(
                {
                    "id": t.id,
                    "ticket_number": ticket_number(t.id),
                    "subject": t.subject,
                    "status": t.status,
                    "priority": t.priority,
                    "category": t.category,
                    "order_id": t.order_id,
                    "merchant_id": t.merchant_id,
                    "customer_id": t.customer_id,
                    "driver_id": t.driver_id,
                    "assigned_to": t.assigned_to,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                }
            )
        return out

    def _build_claims_panel(self, db: Session, *, limit: int = 30) -> list[dict]:
        rows = (
            db.query(Claim)
            .filter(Claim.status.in_(OPEN_CLAIM_STATUSES))
            .order_by(Claim.created_at.desc())
            .limit(limit)
            .all()
        )
        out: list[dict] = []
        for c in rows:
            order = db.query(Order).filter(Order.id == c.order_id).first()
            out.append(
                {
                    "id": c.id,
                    "claim_number": claim_number(c.id),
                    "claim_type": c.claim_type,
                    "status": c.status,
                    "description": (c.description or "")[:160] or None,
                    "order_id": c.order_id,
                    "tracking_number": order.tracking_number if order else None,
                    "assigned_to": c.assigned_to,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
            )
        return out

    def _build_incidents_panel(self, db: Session, *, limit: int = 30) -> list[dict]:
        rows = (
            db.query(OrderException, Order)
            .join(Order, Order.id == OrderException.order_id)
            .filter(OrderException.status == "open")
            .order_by(OrderException.created_at.desc())
            .limit(limit)
            .all()
        )
        out: list[dict] = []
        for e, order in rows:
            coords = _coords(order.dropoff) or _coords(order.pickup)
            out.append(
                {
                    "id": e.id,
                    "type": e.type,
                    "status": e.status,
                    "order_id": order.id,
                    "tracking_number": order.tracking_number,
                    "message": f"Open {e.type.replace('_', ' ')}",
                    "location": {"lat": coords[0], "lng": coords[1]} if coords else None,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
            )
        return out

    def _build_events(self, db: Session, *, limit: int = 40) -> list[dict]:
        rows = db.query(DomainEvent).order_by(DomainEvent.occurred_at.desc()).limit(limit).all()
        events: list[dict] = []
        for e in rows:
            events.append(
                {
                    "id": e.id,
                    "event_type": e.event_type,
                    "source": "porterchain",
                    "title": e.event_type.replace(".", " ").replace("_", " ").title(),
                    "aggregate_type": e.aggregate_type,
                    "aggregate_id": e.aggregate_id,
                    "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
                }
            )
        return events

    def _command_center(self, db: Session) -> dict[str, int]:
        stats = self._tower.stats(db)
        delayed_drivers = (
            db.query(func.count(Driver.id))
            .filter(Driver.is_online.is_(False), Driver.availability == "busy")
            .scalar()
            or 0
        )
        return {
            "orders_today": stats["orders_today"],
            "drivers_online": stats["drivers_online"],
            "vehicles_active": stats["vehicles_active"],
            "orders_waiting": stats["waiting_dispatch"],
            "late_orders": stats["delayed_orders"],
            "delayed_drivers": int(delayed_drivers),
            "support_tickets": int(
                db.query(func.count(SupportTicket.id))
                .filter(SupportTicket.status.in_(OPEN_TICKET_STATUSES))
                .scalar()
                or 0
            ),
            "revenue_today_cents": stats["revenue_today_cents"],
            "open_claims": int(
                db.query(func.count(Claim.id)).filter(Claim.status.in_(OPEN_CLAIM_STATUSES)).scalar() or 0
            ),
            "open_exceptions": stats["open_exceptions"],
        }

    def _heat_maps(self, orders: list[dict], drivers: list[dict]) -> dict[str, list[dict]]:
        pickups = [o["location"] for o in orders if o["stop_type"] == "pickup"]
        deliveries = [o["location"] for o in orders if o["stop_type"] == "delivery"]
        driver_pts = [d["location"] for d in drivers if d.get("location")]
        return {
            "orders": [{**p, "weight": 1.0} for p in pickups + deliveries],
            "pickups": [{**p, "weight": 1.0} for p in pickups],
            "deliveries": [{**p, "weight": 1.0} for p in deliveries],
            "drivers": [{**p, "weight": 1.0} for p in driver_pts],
            "revenue": [
                {**o["location"], "weight": max(1.0, o.get("amount_cents", 0) / 10000)}
                for o in orders
                if o.get("amount_cents")
            ],
        }

    def _smart_insights(
        self, db: Session, drivers: list[dict], orders: list[dict], now: datetime
    ) -> dict[str, Any]:
        online_with_loc = [d for d in drivers if d.get("online") and d.get("location")]
        waiting = [o for o in orders if o["state"] in WAITING and o["stop_type"] == "pickup"]
        nearest: list[dict] = []
        if waiting and online_with_loc:
            target = waiting[0]["location"]
            ranked = sorted(
                online_with_loc,
                key=lambda d: _haversine_km(target["lat"], target["lng"], d["location"]["lat"], d["location"]["lng"]),
            )
            nearest = ranked[:5]

        ai = self._tower.ai_ops(db)
        suggested_ids = {d["id"] for d in ai["suggested_drivers"]}
        suggested = [d for d in drivers if d["id"] in suggested_ids]

        delay_predictions = []
        for o in orders:
            if o["state"] not in IN_FLIGHT or not o.get("eta"):
                continue
            try:
                eta = _parse_iso_naive(o["eta"])
                if eta < now:
                    delay_predictions.append(
                        {
                            "order_id": o["order_id"],
                            "tracking_number": o["tracking_number"],
                            "minutes_late": int((now - eta).total_seconds() / 60),
                        }
                    )
            except ValueError:
                pass

        return {
            "nearest_drivers": nearest,
            "suggested_drivers": suggested,
            "delay_predictions": delay_predictions[:25],
            "traffic_warnings": ["Monitor Gardiner Expressway — typical afternoon congestion"] if delay_predictions else [],
            "route_risks": ai["risk_orders"][:10],
            "merchant_health": [],
            "driver_health": [
                {"driver_id": d["id"], "name": d["name"], "status": "offline_with_job"}
                for d in drivers
                if not d["online"] and d.get("current_order_id")
            ][:10],
        }

    def _weather_stub(self) -> dict[str, Any]:
        return {
            "temperature_c": 18,
            "conditions": "partly_cloudy",
            "wind_kmh": 12,
            "visibility_km": 16,
            "precipitation": "none",
            "note": "Weather overlay uses Porterchain ops feed — connect external provider via adapter when enabled",
        }
