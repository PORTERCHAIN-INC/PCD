"""Partners (warehouse, FTL/LTL, 3PL), order legs and GPS/POD retention — admin side."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

#: Doc 75 Network → Partners: couriers and customs house agents (CHA) join the leg partners.
KINDS = ("warehouse", "ftl", "ltl", "3pl", "courier", "cha")
LEG_FLOW: dict[str, set[str]] = {
    "planned": {"requested", "cancelled"},
    "requested": {"accepted", "cancelled"},
    "accepted": {"picked_up", "cancelled"},
    "picked_up": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
}


def _partner_dict(p: Any) -> dict[str, Any]:
    return {
        "id": p.id, "name": p.name, "kind": p.kind, "lat": p.lat, "lng": p.lng,
        "fsa_coverage": p.fsa_coverage or [], "rate_per_kg_cents": p.rate_per_kg_cents,
        "min_charge_cents": p.min_charge_cents, "transit_days": p.transit_days,
        "cutoff_local": p.cutoff_local, "active": p.active, "contact_email": p.contact_email,
    }


def _clean(body: dict[str, Any]) -> dict[str, Any]:
    name = str(body.get("name") or "").strip()
    kind = str(body.get("kind") or "").strip().lower()
    if not name or len(name) > 128:
        raise ValueError("partner_name_required")
    if kind not in KINDS:
        raise ValueError("partner_kind_invalid")
    out: dict[str, Any] = {"name": name, "kind": kind, "active": bool(body.get("active", True))}
    for key in ("lat", "lng"):
        v = body.get(key)
        out[key] = float(v) if v not in (None, "") else None
    if kind == "warehouse" and (out["lat"] is None or out["lng"] is None):
        raise ValueError("warehouse_needs_coordinates")
    for key in ("rate_per_kg_cents", "min_charge_cents", "transit_days"):
        v = int(body.get(key) or 0)
        if v < 0:
            raise ValueError(f"{key}_negative")
        out[key] = v
    cov = body.get("fsa_coverage") or []
    if isinstance(cov, str):
        cov = [c for c in cov.replace(",", " ").split() if c]
    out["fsa_coverage"] = [str(c).upper()[:3] for c in cov][:200]
    email = str(body.get("contact_email") or "").strip()
    if email and ("@" not in email or len(email) > 255):
        raise ValueError("partner_contact_email_invalid")
    out["contact_email"] = email or None
    cut = body.get("cutoff_local")
    out["cutoff_local"] = str(cut)[:5] if cut else None
    return out


def _audit(db: Session, ctx: Any, action: str, rid: str, payload: dict[str, Any]) -> None:
    from porterchain_api.admin_models import AdminAuditLog

    db.add(AdminAuditLog(actor_user_id=ctx.user.id, action=action, resource_type="dispatch",
                         resource_id=rid, payload=payload))


class LogisticsPartnersService:
    def list(self, db: Session) -> list[dict[str, Any]]:
        from porterchain_api.dispatch_engine.models import LogisticsPartner

        return [_partner_dict(p) for p in db.query(LogisticsPartner).order_by(LogisticsPartner.kind, LogisticsPartner.name)]

    def stats(self, db: Session, *, days: int = 30) -> dict[str, Any]:
        """Per-partner workload in one grouped query (no N+1): open legs, delivered and cost in ``days``."""
        from datetime import UTC, datetime, timedelta

        from sqlalchemy import case, func

        from porterchain_api.dispatch_engine.models import OrderLeg

        since = datetime.now(UTC) - timedelta(days=max(1, min(int(days), 365)))
        open_states = ("planned", "requested", "accepted", "picked_up")
        recent = OrderLeg.created_at >= since
        rows = (
            db.query(
                OrderLeg.partner_id,
                func.sum(case((OrderLeg.status.in_(open_states), 1), else_=0)),
                func.sum(case(((OrderLeg.status == "delivered") & recent, 1), else_=0)),
                func.sum(case(((OrderLeg.status != "cancelled") & recent, OrderLeg.est_cost_cents), else_=0)),
                func.max(OrderLeg.created_at),
            )
            .filter(OrderLeg.partner_id.isnot(None))
            .group_by(OrderLeg.partner_id)
            .all()
        )
        items = {
            pid: {
                "open_legs": int(o or 0),
                "delivered_recent": int(d or 0),
                "cost_recent_cents": int(c or 0),
                "last_leg_at": last.isoformat() if last else None,
            }
            for pid, o, d, c, last in rows
        }
        return {"days": days, "items": items}

    def bulk_active(self, db: Session, ctx: Any, ids: list[str], active: bool) -> dict[str, Any]:
        from porterchain_api.dispatch_engine.models import LogisticsPartner

        clean = [str(i) for i in (ids or []) if i][:200]
        if not clean:
            raise ValueError("ids_required")
        rows = db.query(LogisticsPartner).filter(LogisticsPartner.id.in_(clean)).all()
        for p in rows:
            p.active = bool(active)
            _audit(db, ctx, "dispatch.partner.saved", p.id, {"active": bool(active), "bulk": True})
        db.commit()
        return {"updated": len(rows), "active": bool(active)}

    def upsert(self, db: Session, ctx: Any, body: dict[str, Any], partner_id: str | None = None) -> dict[str, Any]:
        from porterchain_api.dispatch_engine.models import LogisticsPartner

        data = _clean(body)
        if partner_id:
            p = db.get(LogisticsPartner, partner_id)
            if p is None:
                raise LookupError("partner_not_found")
            for k, v in data.items():
                setattr(p, k, v)
        else:
            p = LogisticsPartner(**data)
            db.add(p)
        db.flush()
        _audit(db, ctx, "dispatch.partner.saved", p.id, data)
        db.commit()
        return _partner_dict(p)

    # ---------------- legs
    def plan_legs(self, db: Session, ctx: Any, order_id: str, *, save: bool) -> dict[str, Any]:
        from porterchain_api.booking_models import Order
        from porterchain_api.dispatch_engine.fleet_capacity import order_load
        from porterchain_api.dispatch_engine.legs import plan_legs
        from porterchain_api.dispatch_engine.models import OrderLeg
        from porterchain_api.dispatch_engine.recommend import coords
        from porterchain_api.dispatch_engine.stop_shapes import _postal, fsa

        o = db.get(Order, order_id)
        if o is None:
            raise LookupError("order_not_found")
        pu, do = coords(o.pickup), coords(o.dropoff)
        if not pu or not do:
            raise ValueError("order_not_geocoded")
        meta = o.compliance_metadata or {}
        plan = plan_legs({
            "pickup": pu, "drop": do, "kg": order_load(o).kg,
            "pickup_fsa": fsa(_postal(o.pickup or {})), "drop_fsa": fsa(_postal(o.dropoff or {})),
            "warehouse_hold": bool(meta.get("warehouse_hold")),
        }, self.list(db))
        if save:
            db.query(OrderLeg).filter(OrderLeg.order_id == o.id, OrderLeg.status == "planned").delete(
                synchronize_session=False)
            for leg in plan["legs"]:
                db.add(OrderLeg(order_id=o.id, **leg))
            _audit(db, ctx, "dispatch.order_legs.planned", o.id, {"mode": plan["mode"], "legs": len(plan["legs"])})
            db.commit()
        return {**plan, "order_id": o.id, "saved": save, "current": self.legs(db, o.id)}

    def legs(self, db: Session, order_id: str) -> list[dict[str, Any]]:
        from porterchain_api.dispatch_engine.models import OrderLeg

        rows = db.query(OrderLeg).filter(OrderLeg.order_id == order_id).order_by(OrderLeg.seq).all()
        return [{"id": r.id, "seq": r.seq, "mode": r.mode, "partner_id": r.partner_id, "from_label": r.from_label,
                 "to_label": r.to_label, "status": r.status, "est_cost_cents": r.est_cost_cents} for r in rows]

    # ---------------- L97: assign an order to a courier / contractor fleet partner
    COURIER_KINDS = ("courier", "3pl")
    _CLOSED_ORDER_STATES = frozenset({
        "DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED", "CANCELLED", "FAILED",
        "RETURN_TO_SENDER", "LOST", "DAMAGED", "REFUNDED",
    })

    def assign_partner_leg(self, db: Session, ctx: Any, order_id: str, partner_id: str,
                           note: str | None = None) -> dict[str, Any]:
        """Give the whole order (pickup → drop) to a courier partner as one ``courier`` leg.

        The leg then follows the partner-jobs flow (requested → accepted → picked_up → delivered)
        and, once delivered, shows on the partner's payable statement.
        """
        from datetime import UTC, datetime

        from porterchain_api.booking_models import Order, Package
        from porterchain_api.dispatch_engine.fleet_capacity import order_load
        from porterchain_api.dispatch_engine.legs import _price
        from porterchain_api.dispatch_engine.models import LogisticsPartner, OrderLeg
        from porterchain_api.dispatch_engine.stop_shapes import _postal, fsa

        o = db.get(Order, order_id)
        if o is None:
            raise LookupError("order_not_found")
        p = db.get(LogisticsPartner, str(partner_id or ""))
        if p is None:
            raise LookupError("partner_not_found")
        if not p.active:
            raise ValueError("partner_inactive")
        if p.kind not in self.COURIER_KINDS:
            raise ValueError("partner_not_courier")
        if str(o.state or "").upper() in self._CLOSED_ORDER_STATES:
            raise ValueError("order_not_open")
        if o.assigned_driver_id:
            raise ValueError("order_has_driver")
        open_leg = (db.query(OrderLeg)
                    .filter(OrderLeg.order_id == o.id, OrderLeg.mode == "courier",
                            OrderLeg.status.notin_(("delivered", "cancelled")))
                    .first())
        if open_leg is not None:
            raise ValueError("order_already_with_partner")
        seqs = [r.seq for r in db.query(OrderLeg.seq).filter(OrderLeg.order_id == o.id)]
        parcels = db.query(Package).filter(Package.order_id == o.id).count() or 1
        try:
            kg = float(order_load(o).kg)
        except Exception:  # noqa: BLE001 - a missing weight must not block the assignment
            kg = 0.0
        now = datetime.now(UTC).isoformat()
        by = getattr(getattr(ctx, "user", None), "id", None)
        # L103: estimate with the fleet contract in force today (Toronto), else the partner rate card.
        from porterchain_api.admin_engine.fleet_contracts_service import TORONTO, FleetContractsService

        c = FleetContractsService.contract_on(db, p.id, datetime.now(TORONTO).date())
        if c is not None:
            est, src = FleetContractsService.charge_for(db, c, {"stops": 2, "parcels": parcels}, o.id)[2], "contract"
        else:
            est = _price({"min_charge_cents": p.min_charge_cents, "rate_per_kg_cents": p.rate_per_kg_cents}, kg)
            src = "rate_card"
        leg = OrderLeg(
            order_id=o.id, seq=(max(seqs) + 1) if seqs else 0, mode="courier", partner_id=p.id,
            from_label=(fsa(_postal(o.pickup or {})) or "pickup")[:64],
            to_label=(fsa(_postal(o.dropoff or {})) or "drop")[:64],
            status="planned",
            est_cost_cents=est,
            meta={"stops": 2, "parcels": parcels, "assigned_by": by, "est_source": src,
                  "history": [{"from": None, "to": "planned", "at": now, "by": by,
                               "note": (note or "")[:300] or None}]},
        )
        db.add(leg)
        db.flush()
        _audit(db, ctx, "dispatch.partner_leg.assigned", leg.id,
               {"order_id": o.id, "partner_id": p.id, "note": note})
        db.commit()
        return next(x for x in self.partner_legs(db) if x["id"] == leg.id)

    # ---------------- partner booking workflow
    def partner_legs(self, db: Session, *, status: str | None = None) -> list[dict[str, Any]]:
        from porterchain_api.booking_models import Order
        from porterchain_api.dispatch_engine.models import LogisticsPartner, OrderLeg

        q = db.query(OrderLeg).filter(OrderLeg.mode != "local")
        if status:
            q = q.filter(OrderLeg.status == status)
        rows = q.order_by(OrderLeg.created_at.desc()).limit(200).all()
        orders = {o.id: o for o in db.query(Order).filter(Order.id.in_({r.order_id for r in rows}))} if rows else {}
        pids = {r.partner_id for r in rows if r.partner_id}
        partners = {p.id: p for p in db.query(LogisticsPartner).filter(LogisticsPartner.id.in_(pids))} if pids else {}
        return [{
            "id": r.id, "order_id": r.order_id, "order_number": getattr(orders.get(r.order_id), "order_number", None),
            "seq": r.seq, "mode": r.mode, "status": r.status, "partner_id": r.partner_id,
            "partner_name": getattr(partners.get(r.partner_id or ""), "name", None),
            "from_label": r.from_label, "to_label": r.to_label, "est_cost_cents": r.est_cost_cents,
            "next": sorted(LEG_FLOW.get(r.status, set())), "history": (r.meta or {}).get("history", []),
            "has_draft": bool((r.meta or {}).get("email_draft")),
            "order_state": str(getattr(getattr(orders.get(r.order_id), "state", None), "value",
                                       getattr(orders.get(r.order_id), "state", "")) or ""),
            # L140 backfill: final leg delivered before the fix, order never moved.
            "order_needs_sync": bool(
                r.status == "delivered" and orders.get(r.order_id) is not None
                and str(getattr(getattr(orders[r.order_id], "state", None), "value", getattr(orders[r.order_id], "state", "")))
                not in {"DELIVERED", "POD_COMPLETED", "CANCELLED", "INVOICED", "CLOSED", "COMPLETED"}
                and self._is_final_leg(db, r)
            ),
        } for r in rows]

    def _leg(self, db: Session, leg_id: str) -> tuple[Any, Any, Any]:
        from porterchain_api.booking_models import Order
        from porterchain_api.dispatch_engine.models import LogisticsPartner, OrderLeg

        leg = db.get(OrderLeg, leg_id)
        if leg is None:
            raise LookupError("leg_not_found")
        order = db.get(Order, leg.order_id)
        partner = db.get(LogisticsPartner, leg.partner_id) if leg.partner_id else None
        return leg, order, partner

    def job_sheet_pdf(self, db: Session, leg_id: str) -> tuple[bytes, str]:
        from porterchain_api.admin_engine.partner_job_sheet import render_pdf, sheet_facts

        leg, order, partner = self._leg(db, leg_id)
        return render_pdf(sheet_facts(order, leg, partner)), f"job-sheet-{order.order_number}.pdf"

    def draft_request(self, db: Session, ctx: Any, leg_id: str) -> dict[str, Any]:
        """Build (never send) the partner email; stored on the leg for the admin to copy."""
        from porterchain_api.admin_engine.partner_job_sheet import email_draft, sheet_facts

        leg, order, partner = self._leg(db, leg_id)
        draft = email_draft(sheet_facts(order, leg, partner), partner.contact_email if partner else None)
        leg.meta = {**(leg.meta or {}), "email_draft": draft}
        _audit(db, ctx, "dispatch.partner_leg.drafted", leg.id, {"to": draft["to"], "subject": draft["subject"]})
        db.commit()
        return draft

    def set_leg_status(self, db: Session, ctx: Any, leg_id: str, status: str, note: str | None = None) -> dict[str, Any]:
        from datetime import UTC, datetime

        leg, order, _ = self._leg(db, leg_id)
        if status not in LEG_FLOW.get(leg.status, set()):
            raise ValueError(f"leg_cannot_go_{leg.status}_to_{status}")
        hist = list((leg.meta or {}).get("history", []))
        hist.append({"from": leg.status, "to": status, "at": datetime.now(UTC).isoformat(),
                     "by": getattr(getattr(ctx, "user", None), "id", None), "note": (note or "")[:300] or None})
        before = leg.status
        leg.status = status
        extra = {"delivered_at": hist[-1]["at"]} if status == "delivered" else {}
        leg.meta = {**(leg.meta or {}), "history": hist, **extra}
        _audit(db, ctx, "dispatch.partner_leg.status", leg.id, {"from": before, "to": status, "note": note})
        db.commit()
        if status == "delivered" and order is not None and self._is_final_leg(db, leg):
            self._deliver_order(db, ctx, order, leg)
        return next(x for x in self.partner_legs(db) if x["id"] == leg.id)

    def sync_order_from_leg(self, db: Session, ctx: Any, leg_id: str) -> dict[str, Any]:
        """L140 backfill (admin UI): a final leg already delivered moves its order to DELIVERED."""
        leg, order, _ = self._leg(db, leg_id)
        if leg.status != "delivered":
            raise ValueError("leg_not_delivered")
        if order is None or not self._is_final_leg(db, leg):
            raise ValueError("leg_not_final")
        _audit(db, ctx, "dispatch.partner_leg.sync_order", leg.id, {"order_id": order.id})
        db.commit()
        self._deliver_order(db, ctx, order, leg)
        return next(x for x in self.partner_legs(db) if x["id"] == leg.id)

    @staticmethod
    def _is_final_leg(db: Session, leg: Any) -> bool:
        """L140: a leg is final when no later, non-cancelled leg exists for the order."""
        from porterchain_api.dispatch_engine.models import OrderLeg

        later = (
            db.query(OrderLeg)
            .filter(OrderLeg.order_id == leg.order_id, OrderLeg.id != leg.id,
                    OrderLeg.seq > (leg.seq or 0), OrderLeg.status != "cancelled")
            .count()
        )
        return later == 0

    @staticmethod
    def _deliver_order(db: Session, ctx: Any, order: Any, leg: Any) -> None:
        """L140: final/only partner leg delivered -> order DELIVERED (order events + domain event
        feed tracking and billing). Walks the allowed state path, like the dispatch board move."""
        from porterchain_api.admin_engine.control_tower._helpers import transition_path
        from porterchain_api.booking_engine.order_transitions import transition_order_state
        from porterchain_api.domain.states import OrderState

        try:
            from_state = OrderState(order.state)
        except ValueError:
            return
        if from_state in (OrderState.DELIVERED, OrderState.POD_COMPLETED):
            return
        path = transition_path(from_state, OrderState.DELIVERED)
        if not path:
            return
        actor = getattr(getattr(ctx, "user", None), "id", None)
        payload = {"source": "partner_leg", "leg_id": leg.id, "partner_id": leg.partner_id,
                   "partner_name": getattr(leg, "partner_name", None)}
        for step in path:
            transition_order_state(
                db, order, step,
                event_type="order.delivered" if step == OrderState.DELIVERED else "order.partner_progress",
                actor_type="admin", actor_id=actor, payload={**payload, "target_state": step.value},
            )

    # ---------------- retention
    def retention_get(self, db: Session) -> dict[str, Any]:
        from porterchain_api.dispatch_engine.retention import load_retention

        return load_retention(db)

    def retention_put(self, db: Session, ctx: Any, raw: dict[str, Any]) -> dict[str, Any]:
        from porterchain_api.admin_models import SystemConfig
        from porterchain_api.dispatch_engine.retention import STORAGE_KEY, normalize_retention

        role = getattr(getattr(ctx, "role", None), "value", str(getattr(ctx, "role", "")))
        if role not in {"super_admin", "admin"}:
            raise PermissionError("retention_admin_only")
        value = normalize_retention(raw)
        row = db.get(SystemConfig, STORAGE_KEY)
        before = row.value if row is not None else None
        if row is None:
            db.add(SystemConfig(key=STORAGE_KEY, value=value))
        else:
            row.value = value
        _audit(db, ctx, "settings.dispatch_retention.updated", STORAGE_KEY, {"before": before, "after": value})
        db.commit()
        return value

    def retention_run(self, db: Session, ctx: Any, *, dry_run: bool) -> dict[str, Any]:
        from porterchain_api.dispatch_engine.retention import load_retention
        from porterchain_api.driver_engine.retention_purge import purge

        res = purge(db, load_retention(db), dry_run=dry_run)
        if not dry_run:
            _audit(db, ctx, "dispatch.retention.purged", "dispatch_retention", res)
            db.commit()
        return res


# ---------------------------------------------------------------- split at warehouse
# Before pickup (any driver state) or picked up but not yet out for delivery.
SPLITTABLE = frozenset({
    "BOOKED", "DISPATCH_READY", "DRIVER_REJECTED", "DRIVER_ASSIGNED", "DRIVER_ACCEPTED",
    "DRIVER_EN_ROUTE", "AT_PICKUP", "PICKED_UP",
})


class HubSplitService:
    def split(
        self,
        db: Session,
        settings: Any,
        ctx: Any,
        order_id: str,
        *,
        hub_partner_id: str,
        pickup_driver_id: str | None = None,
        delivery_driver_id: str | None = None,
    ) -> dict[str, Any]:
        from porterchain_api.admin_engine.operations_service import AdminOperationsService
        from porterchain_api.admin_models import AdminAuditLog
        from porterchain_api.booking_models import Order, OrderEvent
        from porterchain_api.dispatch_engine.hub_legs import hub_leg
        from porterchain_api.dispatch_engine.models import LogisticsPartner, OrderLeg
        from porterchain_api.domain.sandbox import order_is_sandbox

        order = db.get(Order, order_id)
        if order is None:
            raise LookupError("order_not_found")
        if order_is_sandbox(order):
            raise ValueError("sandbox_orders_block_live_assign")
        if order.state not in SPLITTABLE:
            raise ValueError("split_not_allowed_in_state")
        if hub_leg(db, order.id) is not None:
            raise ValueError("already_split")
        hub = db.get(LogisticsPartner, hub_partner_id)
        if hub is None or hub.kind != "warehouse" or not hub.active:
            raise LookupError("hub_not_found")
        if hub.lat is None or hub.lng is None:
            raise ValueError("hub_not_geocoded")

        # Replace any still-planned local legs (rules planner output) with the split.
        db.query(OrderLeg).filter(
            OrderLeg.order_id == order.id, OrderLeg.status == "planned", OrderLeg.mode == "local"
        ).delete(synchronize_session=False)
        picked = order.state == "PICKED_UP"
        first_driver = pickup_driver_id or (order.assigned_driver_id if picked else None)
        db.add(OrderLeg(
            order_id=order.id, seq=0, mode="local", partner_id=hub.id, from_label="pickup",
            to_label=hub.name[:64], status="picked_up" if picked else "planned",
            meta={"hub_split": True, "stop_kind": "hub", "to_lat": hub.lat, "to_lng": hub.lng,
                  "hub_formatted": hub.name, "driver_id": first_driver},
        ))
        db.add(OrderLeg(
            order_id=order.id, seq=1, mode="local", partner_id=hub.id, from_label=hub.name[:64],
            to_label="customer", status="planned",
            meta={"hub_split": True, "from_lat": hub.lat, "from_lng": hub.lng,
                  "driver_id": delivery_driver_id},
        ))
        db.add(OrderEvent(order_id=order.id, event_type="order.hub_split", from_state=order.state,
                          to_state=order.state, actor_type="admin", actor_id=ctx.user.id,
                          payload={"hub_partner_id": hub.id, "pickup_driver_id": first_driver,
                                   "delivery_driver_id": delivery_driver_id}))
        db.add(AdminAuditLog(actor_user_id=ctx.user.id, action="dispatch.hub_split", resource_type="order",
                             resource_id=order.id,
                             payload={"hub_partner_id": hub.id, "state": order.state,
                                      "pickup_driver_id": first_driver,
                                      "delivery_driver_id": delivery_driver_id}))
        db.commit()
        if pickup_driver_id and pickup_driver_id != order.assigned_driver_id:
            AdminOperationsService().assign_driver(db, settings, ctx, order.id, pickup_driver_id)
        return self.view(db, order.id)

    def release_delivery_leg(self, db: Session, settings: Any, ctx: Any, order_id: str, *,
                             driver_id: str | None = None) -> dict[str, Any]:
        """Collect-only / warehouse parcel: create (unhold) the delivery leg so Plan the day sees it.

        With ``driver_id`` the van is assigned now (parcel at the hub) or booked for after the drop.
        """
        import copy

        from porterchain_api.admin_engine.operations_service import AdminOperationsService
        from porterchain_api.admin_models import AdminAuditLog
        from porterchain_api.booking_models import Order, OrderEvent
        from porterchain_api.dispatch_engine.hub_legs import hub_leg, set_delivery_driver
        from porterchain_api.services import collect_only as co

        order = db.get(Order, order_id)
        if order is None:
            raise LookupError("order_not_found")
        leg = co.delivery_leg(db, order_id)
        if leg is None or not (leg.meta or {}).get("hub_split"):
            raise ValueError("not_a_warehouse_order")
        if leg.status not in ("planned", "requested", "accepted"):
            raise ValueError("delivery_leg_closed")
        meta = copy.deepcopy(leg.meta or {})
        was_held = bool(meta.pop("held", False))
        leg.meta = meta
        db.add(OrderEvent(order_id=order.id, event_type="order.delivery_leg_released", from_state=order.state,
                          to_state=order.state, actor_type="admin", actor_id=ctx.user.id,
                          payload={"driver_id": driver_id, "was_held": was_held}))
        db.add(AdminAuditLog(actor_user_id=ctx.user.id, action="dispatch.delivery_leg_release",
                             resource_type="order", resource_id=order.id,
                             payload={"driver_id": driver_id, "state": order.state}))
        db.commit()
        if driver_id and co.awaiting_delivery(db, order):
            AdminOperationsService().assign_driver(db, settings, ctx, order.id, driver_id)
        elif driver_id and (hl := hub_leg(db, order.id)) is not None:
            set_delivery_driver(hl, driver_id)  # still on the way to the hub
            db.commit()
        return {"order_id": order.id, "released": True, "held": False}

    def view(self, db: Session, order_id: str) -> dict[str, Any]:
        from porterchain_api.dispatch_engine.hub_legs import hub_leg

        leg = hub_leg(db, order_id)
        if leg is None:
            return {"order_id": order_id, "split": False}
        from porterchain_api.booking_models import Order
        from porterchain_api.services import collect_only as co

        order = db.get(Order, order_id)
        held = co.is_held(db, order_id)
        waiting = order is not None and co.awaiting_delivery(db, order)
        return {
            "order_id": order_id,
            "split": True,
            "collect_only": bool(order is not None and co.is_collect_only(order)),
            "delivery_held": held,
            "awaiting_delivery": waiting,
            "status_label": co.AWAITING_LABEL if waiting else None,
            "stage": leg.stage,
            "hub": leg.hub,
            "pickup_driver_id": (leg.first.meta or {}).get("driver_id"),
            "delivery_driver_id": leg.delivery_driver_id,
            "arrived_at_hub": leg.arrived_at_hub,
        }
