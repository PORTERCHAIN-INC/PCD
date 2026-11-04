"""Contractor fleet partner contracts (manual entry) and the payable statement they drive.

Fleets charge PorterChain fixed contract rates. Admin types the contract in (no import);
completed (``delivered``) order legs assigned to that partner are priced per job:

    units x rate_cents, floored at min_charge_cents

Units per basis: ``stop`` = leg.meta.stops (default 2: pickup + drop), ``parcel`` = packages
on the order (leg.meta.parcels overrides), ``route`` = 1 per job, ``hour`` = leg.meta.hours.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

TORONTO = ZoneInfo("America/Toronto")  # L103: statement days are Toronto business days

RATE_BASES = ("stop", "parcel", "route", "hour")


def _d(v: Any) -> date | None:
    if v in (None, ""):
        return None
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


def _contract_dict(c: Any) -> dict[str, Any]:
    return {
        "id": c.id, "partner_id": c.partner_id,
        "effective_from": c.effective_from.isoformat() if c.effective_from else None,
        "effective_to": c.effective_to.isoformat() if c.effective_to else None,
        "rate_basis": c.rate_basis, "rate_cents": int(c.rate_cents or 0),
        "min_charge_cents": int(c.min_charge_cents or 0), "currency": c.currency,
        "document_ref": c.document_ref, "notes": c.notes, "is_dummy": bool(c.is_dummy),
    }


def _clean(body: dict[str, Any]) -> dict[str, Any]:
    basis = str(body.get("rate_basis") or "").strip().lower()
    if basis not in RATE_BASES:
        raise ValueError("rate_basis must be one of: stop, parcel, route, hour")
    start = _d(body.get("effective_from"))
    if start is None:
        raise ValueError("effective_from is required")
    end = _d(body.get("effective_to"))
    if end is not None and end < start:
        raise ValueError("effective_to must be on or after effective_from")
    rate = int(body.get("rate_cents") or 0)
    minc = int(body.get("min_charge_cents") or 0)
    if rate < 0 or minc < 0:
        raise ValueError("amounts must not be negative")
    if rate == 0 and minc == 0:
        raise ValueError("rate_cents or min_charge_cents is required")
    return {
        "effective_from": start, "effective_to": end, "rate_basis": basis,
        "rate_cents": rate, "min_charge_cents": minc,
        "currency": str(body.get("currency") or "cad").lower()[:8],
        "document_ref": (str(body.get("document_ref") or "").strip() or None),
        "notes": (str(body.get("notes") or "").strip()[:2000] or None),
        "is_dummy": bool(body.get("is_dummy")),
    }


class FleetContractsService:
    def list(self, db: Session, partner_id: str | None = None) -> list[dict[str, Any]]:
        from porterchain_api.dispatch_engine.models import FleetPartnerContract as C
        from porterchain_api.dispatch_engine.models import LogisticsPartner

        q = db.query(C)
        if partner_id:
            q = q.filter(C.partner_id == partner_id)
        names = {p.id: p.name for p in db.query(LogisticsPartner).all()}
        out = []
        for c in q.order_by(C.partner_id, C.effective_from.desc()).all():
            row = _contract_dict(c)
            row["partner_name"] = names.get(c.partner_id)
            out.append(row)
        return out

    def upsert(self, db: Session, ctx: Any, body: dict[str, Any], contract_id: str | None = None) -> dict[str, Any]:
        from porterchain_api.admin_engine.logistics_partners_service import _audit
        from porterchain_api.dispatch_engine.models import FleetPartnerContract as C
        from porterchain_api.dispatch_engine.models import LogisticsPartner

        data = _clean(body)
        if contract_id:
            c = db.get(C, contract_id)
            if c is None:
                raise LookupError("contract_not_found")
        else:
            pid = str(body.get("partner_id") or "")
            if not pid or db.get(LogisticsPartner, pid) is None:
                raise LookupError("partner_not_found")
            c = C(partner_id=pid)
        with db.no_autoflush:
            self._no_overlap(db, c.partner_id, data["effective_from"], data["effective_to"], c.id)
        for k, v in data.items():
            setattr(c, k, v)
        if not contract_id:
            db.add(c)
        db.flush()
        _audit(db, ctx, "dispatch.fleet_contract.saved", c.id,
               {k: (v.isoformat() if isinstance(v, date) else v) for k, v in data.items()})
        db.commit()
        return _contract_dict(c)

    def delete(self, db: Session, ctx: Any, contract_id: str) -> dict[str, Any]:
        from porterchain_api.admin_engine.logistics_partners_service import _audit
        from porterchain_api.dispatch_engine.models import FleetPartnerContract as C

        c = db.get(C, contract_id)
        if c is None:
            raise LookupError("contract_not_found")
        _audit(db, ctx, "dispatch.fleet_contract.deleted", c.id, _contract_dict(c))
        db.delete(c)
        db.commit()
        return {"deleted": contract_id}

    @staticmethod
    def _no_overlap(db: Session, partner_id: str, start: date, end: date | None, self_id: str | None) -> None:
        from porterchain_api.dispatch_engine.models import FleetPartnerContract as C

        far = date(9999, 12, 31)
        for o in db.query(C).filter(C.partner_id == partner_id).all():
            if self_id and o.id == self_id:
                continue
            if start <= (o.effective_to or far) and o.effective_from <= (end or far):
                raise ValueError("These dates overlap an existing contract for this company. End the current contract first (Edit → Effective to), then add the new one.")

    @staticmethod
    def contract_on(db: Session, partner_id: str, day: date) -> Any:
        from porterchain_api.dispatch_engine.models import FleetPartnerContract as C

        for c in db.query(C).filter(C.partner_id == partner_id).all():
            if c.effective_from <= day and (c.effective_to is None or day <= c.effective_to):
                return c
        return None

    @staticmethod
    def charge_for(db: Session, c: Any, meta: dict[str, Any], order_id: str) -> tuple[Decimal, int, int]:
        """(units, raw, charge) for one job under contract c; min charge applied."""
        from porterchain_api.booking_models import Package

        if c.rate_basis == "stop":
            units = Decimal(str(meta.get("stops", 2)))
        elif c.rate_basis == "parcel":
            n = meta.get("parcels")
            if n is None:
                n = db.query(Package).filter(Package.order_id == order_id).count() or 1
            units = Decimal(str(n))
        elif c.rate_basis == "hour":
            units = Decimal(str(meta.get("hours", 0)))
        else:
            units = Decimal(1)
        raw = int((units * Decimal(int(c.rate_cents or 0))).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        return units, raw, max(raw, int(c.min_charge_cents or 0))

    def payable_statement(self, db: Session, partner_id: str, start: date, end: date) -> dict[str, Any]:
        """Per completed job: units, rate, charge (min applied); total for [start, end]."""
        from porterchain_api.booking_models import Order
        from porterchain_api.dispatch_engine.models import LogisticsPartner, OrderLeg

        partner = db.get(LogisticsPartner, partner_id)
        if partner is None:
            raise LookupError("partner_not_found")
        lo = datetime.combine(start, time.min, tzinfo=TORONTO)
        hi = datetime.combine(end, time.max, tzinfo=TORONTO)
        legs = db.query(OrderLeg).filter(OrderLeg.partner_id == partner_id, OrderLeg.status == "delivered").all()
        jobs: list[dict[str, Any]] = []
        unpriced: list[dict[str, Any]] = []
        total = 0
        for leg in legs:
            meta = leg.meta or {}
            when = meta.get("delivered_at")
            done = datetime.fromisoformat(str(when)) if when else leg.created_at
            if done is None:
                continue
            if done.tzinfo is None:
                done = done.replace(tzinfo=UTC)
            done = done.astimezone(TORONTO)
            if not (lo <= done <= hi):
                continue
            order = db.get(Order, leg.order_id)
            c = self.contract_on(db, partner_id, done.date())
            base = {"leg_id": leg.id, "order_id": leg.order_id,
                    "order_number": getattr(order, "order_number", None),
                    "completed_at": done.isoformat(), "from": leg.from_label, "to": leg.to_label}
            if c is None:
                unpriced.append({**base, "reason": "no_contract_on_date"})
                continue
            units, raw, charge = self.charge_for(db, c, meta, leg.order_id)
            total += charge
            jobs.append({**base, "contract_id": c.id, "rate_basis": c.rate_basis, "units": float(units),
                         "rate_cents": int(c.rate_cents or 0), "min_charge_cents": int(c.min_charge_cents or 0),
                         "charge_cents": charge, "min_applied": charge > raw, "is_dummy_contract": bool(c.is_dummy)})
        jobs.sort(key=lambda j: j["completed_at"])
        return {"partner_id": partner_id, "partner_name": partner.name, "period_start": start.isoformat(),
                "period_end": end.isoformat(), "currency": "cad", "jobs": jobs, "unpriced": unpriced,
                "total_cents": total}
