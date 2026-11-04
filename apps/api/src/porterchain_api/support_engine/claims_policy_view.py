"""Policy assessment, letters and broker notice for one claim (admin screen). Nothing is sent from here."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import Claim
from porterchain_api.booking_models import Order, Package
from porterchain_api.domain.claims import claim_number
from porterchain_api.support_engine import claims_policy as CP
from porterchain_api.support_engine import claims_templates as T
from porterchain_api.support_engine.support_helpers import SupportActor
from porterchain_pricing import insurance_policy as POLICY


def _parcels(db: Session, order: Order | None, inv: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(inv.get("parcels"), list) and inv["parcels"]:
        return [p for p in inv["parcels"] if isinstance(p, dict)]
    if order is None:
        return []
    rows = db.query(Package).filter(Package.order_id == order.id).all()
    return [{"weight_kg": float(r.weight_kg or 0), "covered": False, "category": inv.get("category")} for r in rows]


def assess(db: Session, claim: Claim) -> dict[str, Any]:
    ev = claim.evidence or {}
    inv = dict(ev.get("investigation") or {})
    res = claim.resolution or {}
    order = db.query(Order).filter(Order.id == claim.order_id).first()
    cargo = claim.claim_type in CP.LOSS_TYPES
    delivered = inv.get("delivered_on") or (
        order.updated_at if order is not None and order.state == "delivered" else None)
    shipped = inv.get("shipped_on") or (order.scheduled_at if order is not None else None)
    claimed = inv.get("claimed_cents") or (res.get("compensation") or {}).get("claim_amount_cents")
    liability = CP.liability_ceiling(_parcels(db, order, inv))
    return {
        "applies": cargo,
        "claim_reference": claim_number(claim.id),
        "order_number": order.order_number if order is not None else None,
        "investigated": bool(inv),
        "notice": CP.notice_window(claim_type=claim.claim_type, shipped_on=shipped, delivered_on=delivered,
                                   notice_on=inv.get("notice_received_on") or claim.created_at),
        "evidence": CP.evidence_status(ev.get("files") or [], inv.get("evidence_received")),
        "liability": liability,
        "claimed_cents": int(claimed) if claimed else None,
        "insurer": CP.insurer_step(int(claimed) if claimed else None, liability["cap_cents"]),
        "broker_notice": res.get("broker_notice") or None,
        "policy": {"insurer": POLICY.INSURER, "policy_ref": POLICY.POLICY_REF, "broker": POLICY.BROKER,
                   "in_force": POLICY.in_force(), "expires": POLICY.EXPIRES.isoformat(),
                   "target_commodities": list(POLICY.TARGET_COMMODITIES),
                   "target_commodities_verified": False},
        "denial_reasons": [{"key": k, "text": v} for k, v in CP.DENIAL_REASONS.items()],
    }


class ClaimsPolicyMixin:
    def policy_view(self, db: Session, claim_id: str) -> dict[str, Any]:
        claim = self.get_claim(db, claim_id)
        if not claim:
            raise LookupError("claim_not_found")
        return assess(db, claim)

    def draft_letter(self, db: Session, ctx: SupportActor, claim_id: str, kind: str,
                     amount_cents: int | None = None, reason: str | None = None,
                     details: str | None = None) -> dict[str, Any]:
        claim = self.get_claim(db, claim_id)
        if not claim:
            raise LookupError("claim_not_found")
        a = assess(db, claim)
        ref, num = a["claim_reference"], a["order_number"] or claim.order_id
        if kind == "acknowledgement":
            letter = T.acknowledgement(ref, num, a)
        elif kind == "approved":
            if not a["investigated"]:
                raise ValueError("investigation_required_before_decision")
            letter = T.decision_approved(ref, num, int(amount_cents or 0), a, details)
        elif kind == "denied":
            if not a["investigated"]:
                raise ValueError("investigation_required_before_decision")
            letter = T.decision_denied(ref, num, reason or "", details)
        else:
            raise ValueError("unknown_letter_kind")
        self._append_timeline(db, claim, label="Letter Drafted (not sent)", actor_type="admin",
                              actor_id=ctx.user.id, payload={"kind": kind, "subject": letter["subject"]})
        db.commit()
        return {"kind": kind, **letter, "sent": False}

    def prepare_broker_notice(self, db: Session, ctx: SupportActor, claim_id: str) -> dict[str, Any]:
        claim = self.get_claim(db, claim_id)
        if not claim:
            raise LookupError("claim_not_found")
        a = assess(db, claim)
        inv = (claim.evidence or {}).get("investigation") or {}
        draft = T.broker_notice(a["claim_reference"], a["order_number"] or claim.order_id, a,
                                claimed_cents=a["claimed_cents"], loss_date=inv.get("loss_date"),
                                description=claim.description)
        res = dict(claim.resolution or {})
        res["broker_notice"] = {**draft, "status": "draft_for_review", "sent": False,
                                "prepared_at": datetime.now(UTC).isoformat(), "prepared_by": ctx.user.id}
        claim.resolution = res
        self._append_timeline(db, claim, label="Broker Notice Drafted (not sent)", actor_type="admin",
                              actor_id=ctx.user.id, payload={"subject": draft["subject"]})
        db.commit()
        return res["broker_notice"]

    def record_broker_notified(self, db: Session, ctx: SupportActor, claim_id: str, *, sent_on: str,
                               method: str, broker_reference: str | None = None) -> dict[str, Any]:
        """Admin records that THEY sent the notice (email/phone). We never send it."""
        claim = self.get_claim(db, claim_id)
        if not claim:
            raise LookupError("claim_not_found")
        res = dict(claim.resolution or {})
        notice = dict(res.get("broker_notice") or {})
        notice.update({"status": "sent_by_admin", "sent": True, "sent_on": sent_on, "method": method,
                       "broker_reference": broker_reference, "recorded_by": ctx.user.id})
        res["broker_notice"] = notice
        claim.resolution = res
        self._append_timeline(db, claim, label="Broker Notified (recorded by admin)", actor_type="admin",
                              actor_id=ctx.user.id, payload={"sent_on": sent_on, "method": method,
                                                             "broker_reference": broker_reference})
        db.commit()
        return notice
