"""Claim mutations — open, status, evidence, compensation, insurance."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import Claim
from porterchain_api.booking_engine._core import emit_event, publish_recorded_event, _event_fields
from porterchain_api.booking_models import Customer, Order
from porterchain_api.domain.claims import CLAIM_TYPES, claim_number
from porterchain_api.support_engine.claim_terms import claim_terms_meta
from porterchain_api.support_engine.claims_constants import CLAIM_STATUSES, set_claim_meta
from porterchain_api.support_engine.support_helpers import SupportActor
from porterchain_shared.events.catalog import DomainEventType


class ClaimsMutationsMixin:
    def open_claim(
        self,
        db: Session,
        ctx: SupportActor,
        *,
        order_id: str,
        claim_type: str,
        description: str | None = None,
        priority: str = "normal",
    ) -> Claim:
        normalized_type = claim_type if claim_type in CLAIM_TYPES else "other"
        claim = Claim(
            order_id=order_id,
            claim_type=normalized_type,
            description=description,
            assigned_to=ctx.user.id,
            status="new",
        )
        db.add(claim)
        db.flush()
        order = db.query(Order).filter(Order.id == order_id).first()
        from porterchain_api.admin_engine.platform_settings import investigation_sla_hours

        due_at = datetime.now(UTC) + timedelta(hours=investigation_sla_hours(db))
        # D-31: snapshot assignee at open so reassignment doesn't drop care history.
        set_claim_meta(
            claim,
            priority=priority,
            driver_id=order.assigned_driver_id if order else None,
            investigation_due_at=due_at.isoformat(),
            **claim_terms_meta(db, order),
        )
        customer = (
            db.query(Customer).filter(Customer.id == order.customer_id).first()
            if order and order.customer_id
            else None
        )
        self._append_timeline(
            db, claim, label="Claim Created", actor_type="admin", actor_id=ctx.user.id,
            payload={"claim_type": normalized_type, "order_id": order_id},
        )
        claim_event = _event_fields(
            event_type=DomainEventType.CLAIM_OPENED,
            aggregate_type="claim",
            aggregate_id=claim.id,
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={
                "order_id": order_id,
                "claim_type": normalized_type,
                "claim_number": claim_number(claim.id),
                "order_number": order.order_number if order else "",
                "email": customer.email if customer else None,
            },
        )
        emit_event(db, publish=False, **claim_event)
        if normalized_type in ("payment_dispute", "chargeback"):
            emit_event(
                db,
                publish=False,
                event_type=DomainEventType.REFUND_REQUESTED,
                aggregate_type="claim",
                aggregate_id=claim.id,
                actor_type="admin",
                actor_id=ctx.user.id,
                correlation_id=order_id,
                payload={
                    "claim_id": claim.id,
                    "order_id": order_id,
                    "claim_type": normalized_type,
                },
            )
        db.commit()
        publish_recorded_event(**claim_event)
        db.refresh(claim)
        return claim

    def open_actor_claim(
        self,
        db: Session,
        *,
        order_id: str,
        claim_type: str,
        description: str | None = None,
        status: str = "new",
        actor_type: str = "system",
        actor_id: str | None = None,
        skip_if_open: bool = False,
        commit: bool = True,
    ) -> Claim | None:
        if skip_if_open:
            existing = (
                db.query(Claim)
                .filter(Claim.order_id == order_id, Claim.status == "open")
                .first()
            )
            if existing:
                return existing
        normalized_type = claim_type if claim_type in CLAIM_TYPES else "other"
        claim = Claim(
            order_id=order_id,
            claim_type=normalized_type,
            description=description,
            status=status,
        )
        db.add(claim)
        db.flush()
        self._append_timeline(
            db,
            claim,
            label=f"Claim filed by {actor_type}",
            actor_type=actor_type,
            actor_id=actor_id,
            payload={"claim_type": normalized_type, "order_id": order_id},
        )
        order = db.query(Order).filter(Order.id == order_id).first()
        set_claim_meta(claim, **claim_terms_meta(db, order))
        emit_event(
            db,
            event_type=DomainEventType.CLAIM_OPENED,
            aggregate_type="claim",
            aggregate_id=claim.id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "order_id": order_id,
                "claim_type": normalized_type,
                "claim_number": claim_number(claim.id),
                "order_number": order.order_number if order else "",
            },
        )
        if commit:
            db.commit()
            db.refresh(claim)
        return claim

    def update_status(self, db: Session, ctx: SupportActor, claim_id: str, status: str) -> Claim:
        claim = self.get_claim(db, claim_id)
        if not claim:
            raise LookupError("claim_not_found")
        if status not in CLAIM_STATUSES:
            raise ValueError("invalid_status")
        previous = claim.status
        claim.status = status
        if status in ("compensated", "closed", "archived", "resolved", "rejected"):
            claim.resolved_at = datetime.now(UTC)
            emit_event(
                db,
                event_type=DomainEventType.CLAIM_RESOLVED,
                aggregate_type="claim",
                aggregate_id=claim_id,
                actor_type="admin",
                actor_id=ctx.user.id,
                payload={
                    "from_status": previous,
                    "to_status": status,
                    "order_id": claim.order_id,
                    "status": status,
                },
            )
        self._append_timeline(
            db, claim, label="Decision Made", actor_type="admin", actor_id=ctx.user.id,
            payload={"from_status": previous, "to_status": status},
        )
        db.commit()
        db.refresh(claim)
        return claim

    def assign_investigator(
        self, db: Session, ctx: SupportActor, claim_id: str, investigator_id: str
    ) -> Claim:
        claim = self.get_claim(db, claim_id)
        if not claim:
            raise LookupError("claim_not_found")
        claim.assigned_to = investigator_id
        if claim.status in ("new", "open"):
            claim.status = "assigned"
        self._append_timeline(
            db, claim, label="Investigator Assigned", actor_type="admin", actor_id=ctx.user.id,
            payload={"investigator_id": investigator_id},
        )
        db.commit()
        db.refresh(claim)
        return claim

    def add_evidence(
        self,
        db: Session,
        ctx: SupportActor,
        claim_id: str,
        *,
        file_type: str,
        name: str,
        url: str | None = None,
        meta: dict | None = None,
    ) -> Claim:
        claim = self.get_claim(db, claim_id)
        if not claim:
            raise LookupError("claim_not_found")
        ev = dict(claim.evidence or {})
        files = list(ev.get("files") or [])
        version = len([f for f in files if f.get("name") == name]) + 1
        files.append(
            {
                "id": str(uuid.uuid4()),
                "type": file_type,
                "name": name,
                "url": url,
                "version": version,
                "uploaded_at": datetime.now(UTC).isoformat(),
                "uploaded_by": ctx.user.id,
                "meta": meta or {},
            }
        )
        ev["files"] = files
        claim.evidence = ev
        self._append_timeline(
            db, claim, label="Evidence Uploaded", actor_type="admin", actor_id=ctx.user.id,
            payload={"file_type": file_type, "name": name},
        )
        db.commit()
        db.refresh(claim)
        return claim

    def add_note(
        self,
        db: Session,
        ctx: SupportActor,
        claim_id: str,
        *,
        body: str,
        internal: bool = True,
        channel: str = "internal",
    ) -> Claim:
        claim = self.get_claim(db, claim_id)
        if not claim:
            raise LookupError("claim_not_found")
        ev = dict(claim.evidence or {})
        notes = list(ev.get("notes") or [])
        notes.append(
            {
                "id": str(uuid.uuid4()),
                "body": body,
                "internal": internal,
                "channel": channel,
                "author_id": ctx.user.id,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        ev["notes"] = notes
        if not internal:
            comms = list(ev.get("communications") or [])
            comms.append(
                {
                    "channel": channel,
                    "body": body,
                    "direction": "outbound",
                    "at": datetime.now(UTC).isoformat(),
                }
            )
            ev["communications"] = comms
        claim.evidence = ev
        self._append_timeline(
            db, claim, label="Note Added", actor_type="admin", actor_id=ctx.user.id,
            payload={"internal": internal},
        )
        db.commit()
        db.refresh(claim)
        return claim

    def update_investigation(
        self, db: Session, ctx: SupportActor, claim_id: str, investigation: dict[str, Any]
    ) -> Claim:
        claim = self.get_claim(db, claim_id)
        if not claim:
            raise LookupError("claim_not_found")
        ev = dict(claim.evidence or {})
        current = dict(ev.get("investigation") or {})
        current.update(investigation)
        ev["investigation"] = current
        claim.evidence = ev
        if claim.status in ("new", "open", "assigned"):
            claim.status = "under_investigation"
        self._append_timeline(
            db, claim, label="Investigation Updated", actor_type="admin", actor_id=ctx.user.id,
        )
        db.commit()
        db.refresh(claim)
        return claim

    def set_compensation(
        self, db: Session, ctx: SupportActor, claim_id: str, compensation: dict[str, Any]
    ) -> Claim:
        claim = self.get_claim(db, claim_id)
        if not claim:
            raise LookupError("claim_not_found")
        from porterchain_api.admin_engine.platform_settings import max_compensation_cents

        approved = compensation.get("approved_amount_cents")
        if approved is not None:
            try:
                amount = int(approved)
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid_compensation_amount") from exc
            cap = max_compensation_cents(db)
            if cap > 0 and amount > cap:
                raise ValueError("compensation_exceeds_policy_cap")
        res = dict(claim.resolution or {})
        res["compensation"] = compensation
        claim.resolution = res
        if compensation.get("approved_amount_cents"):
            claim.status = "compensated"
            claim.resolved_at = datetime.now(UTC)
            emit_event(
                db,
                event_type=DomainEventType.REFUND_ISSUED,
                aggregate_type="claim",
                aggregate_id=claim_id,
                actor_type="admin",
                actor_id=ctx.user.id,
                correlation_id=claim.order_id,
                payload={
                    "claim_id": claim_id,
                    "order_id": claim.order_id,
                    "amount_cents": compensation.get("approved_amount_cents"),
                },
            )
        self._append_timeline(
            db, claim, label="Compensation Paid", actor_type="admin", actor_id=ctx.user.id,
            payload=compensation,
        )
        db.commit()
        db.refresh(claim)
        return claim

    def set_insurance(
        self, db: Session, ctx: SupportActor, claim_id: str, insurance: dict[str, Any]
    ) -> Claim:
        claim = self.get_claim(db, claim_id)
        if not claim:
            raise LookupError("claim_not_found")
        res = dict(claim.resolution or {})
        res["insurance"] = insurance
        claim.resolution = res
        if claim.status not in ("compensated", "closed", "archived"):
            claim.status = "waiting_insurance"
        self._append_timeline(
            db, claim, label="Insurance Updated", actor_type="admin", actor_id=ctx.user.id,
            payload=insurance,
        )
        db.commit()
        db.refresh(claim)
        return claim

    def bulk_action(
        self,
        db: Session,
        ctx: SupportActor,
        *,
        claim_ids: list[str],
        action: str,
        investigator_id: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        results = []
        for cid in claim_ids:
            try:
                if action == "assign" and investigator_id:
                    self.assign_investigator(db, ctx, cid, investigator_id)
                elif action == "status" and status:
                    self.update_status(db, ctx, cid, status)
                else:
                    raise ValueError("invalid_bulk_action")
                results.append({"claim_id": cid, "status": "ok"})
            except Exception as exc:
                results.append({"claim_id": cid, "status": "error", "detail": str(exc)})
        return {"action": action, "results": results}
