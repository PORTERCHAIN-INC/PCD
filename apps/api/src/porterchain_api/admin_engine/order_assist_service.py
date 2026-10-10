"""Order 360 scoped assist — propose-only; writes require explicit Confirm.

Rules-based (no silent LLM writes). Uses existing assign / exception / invoice /
notification / claims APIs. Never advances Accept→Delivered (driver check-ins own that).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.dispatch_suggestions_service import DispatchSuggestionsService
from porterchain_api.admin_engine.order_assist_proposals import (
    assign_proposals,
    exception_proposals,
    late_and_money,
    playbooks,
    proposal_id as _pid,
)
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.invoice_service import InvoiceService
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState
from porterchain_api.booking_models import Customer, Order, OrderException


class OrderAssistService:
    def __init__(self) -> None:
        self._suggestions = DispatchSuggestionsService()
        self._invoices = InvoiceService()

    def assist(self, db: Session, settings: Settings, order_id: str) -> dict[str, Any]:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise LookupError("order_not_found")

        proposals: list[dict[str, Any]] = []
        proposals.extend(self._assign_proposals(db, order))
        proposals.extend(self._exception_proposals(db, order))
        proposals.extend(self._late_and_money(db, order))
        proposals.extend(self._message_drafts(db, order))

        return {
            "order_id": order.id,
            "tracking_number": order.tracking_number,
            "state": order.state,
            "contract": {
                "mode": "propose_confirm",
                "writes_require_confirm": True,
                "execution_blocked": True,
                "note": "Agent may propose assign/exception/message; Confirm runs existing APIs only.",
            },
            "proposals": proposals,
            "playbooks": self._playbooks(db, order),
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def decide(
        self,
        db: Session,
        settings: Settings,
        ctx: AdminContext,
        order_id: str,
        *,
        proposal_id: str,
        decision: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if decision not in ("accept", "reject"):
            raise ValueError("decision_must_be_accept_or_reject")
        assist = self.assist(db, settings, order_id)
        proposal = next((p for p in assist["proposals"] if p["id"] == proposal_id), None)
        if not proposal:
            raise LookupError("proposal_not_found")

        emit_event(
            db,
            event_type=f"ops.assist.{decision}",
            aggregate_type="order",
            aggregate_id=order_id,
            correlation_id=order_id,
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={
                "proposal_id": proposal_id,
                "kind": proposal.get("kind"),
                "title": proposal.get("title"),
                "decision": decision,
            },
        )

        if decision == "reject":
            db.commit()
            return {"ok": True, "decision": "reject", "proposal_id": proposal_id}

        result = self._execute_proposal(db, settings, ctx, order_id, proposal, payload or {})
        db.commit()
        return {
            "ok": True,
            "decision": "accept",
            "proposal_id": proposal_id,
            "kind": proposal.get("kind"),
            "result": result,
        }

    def run_playbook(
        self,
        db: Session,
        settings: Settings,
        ctx: AdminContext,
        order_id: str,
        playbook_id: str,
        *,
        confirm: bool,
        note: str | None = None,
    ) -> dict[str, Any]:
        if not confirm:
            raise ValueError("playbook_requires_confirm")
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise LookupError("order_not_found")
        playbooks = {p["id"]: p for p in self._playbooks(db, order)}
        pb = playbooks.get(playbook_id)
        if not pb:
            raise LookupError("playbook_not_found")
        if not pb.get("enabled"):
            raise ValueError(pb.get("disabled_reason") or "playbook_disabled")

        emit_event(
            db,
            event_type="ops.playbook.ran",
            aggregate_type="order",
            aggregate_id=order_id,
            correlation_id=order_id,
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={"playbook_id": playbook_id, "note": note},
        )

        if playbook_id == "retry_dispatch":
            result = self._playbook_retry_dispatch(db, ctx, order)
        elif playbook_id == "notify_customer":
            result = self._playbook_notify_customer(db, order, note=note)
        elif playbook_id == "escalate_claim":
            result = self._playbook_escalate_claim(db, ctx, order, note=note)
        elif playbook_id == "generate_invoice":
            inv = self._invoices.manual_invoice(db, order.id)
            result = {"invoice_number": inv.invoice_number}
        elif playbook_id == "resend_receipt":
            result = self._invoices.resend_receipt(db, order.id)
        else:
            raise ValueError("unknown_playbook")

        db.commit()
        return {"ok": True, "playbook_id": playbook_id, "result": result}

    # --- proposals ---------------------------------------------------------

    def _assign_proposals(self, db: Session, order: Order) -> list[dict[str, Any]]:
        return assign_proposals(self, db, order)

    def _exception_proposals(self, db: Session, order: Order) -> list[dict[str, Any]]:
        return exception_proposals(order)

    def _late_and_money(self, db: Session, order: Order) -> list[dict[str, Any]]:
        return late_and_money(db, order)

    def _message_drafts(self, db: Session, order: Order) -> list[dict[str, Any]]:
        customer = (
            db.query(Customer).filter(Customer.id == order.customer_id).first()
            if order.customer_id
            else None
        )
        from porterchain_api.merchant_engine.lookups import get_merchant

        merchant = get_merchant(db, order.merchant_id)
        who = (customer.email if customer else None) or (merchant.email if merchant else None) or "recipient"
        sms = (
            f"PorterChain update: {order.tracking_number} is {order.state.replace('_', ' ').title()}. "
            f"Track: /track/{order.tracking_number}"
        )
        email_body = (
            f"Hello,\n\nYour shipment {order.tracking_number} is currently "
            f"{order.state.replace('_', ' ').title()}.\n"
            f"Track status anytime with your tracking number.\n\n"
            f"— PorterChain\nMoving commerce on chain"
        )
        from porterchain_api.config import get_settings
        from porterchain_api.intelligence_engine.enrichers import polish_message_draft

        polished = polish_message_draft(
            sms=sms,
            email_body=email_body,
            tracking_number=order.tracking_number,
            state=order.state,
            flags=get_settings().phase2_flags,
            db=db,
        )
        return [
            {
                "id": _pid("draft_message", order.id),
                "kind": "draft_message",
                "title": "Draft customer update",
                "summary": f"Preview for {who}. Confirm sends email via Notify customer playbook.",
                "confidence": "high",
                "preview": {
                    "sms": polished["sms"],
                    "email_body": polished["email_body"],
                    "recipient": who,
                },
                "requires_confirm": True,
                "payload": {"channel": "email", "message": polished["email_body"]},
                "draft_source": polished.get("draft_source") or "heuristic",
            }
        ]

    def _playbooks(self, db: Session, order: Order) -> list[dict[str, Any]]:
        return playbooks(db, order)

    # --- execute -----------------------------------------------------------

    def _execute_proposal(
        self,
        db: Session,
        settings: Settings,
        ctx: AdminContext,
        order_id: str,
        proposal: dict[str, Any],
        overrides: dict[str, Any],
    ) -> dict[str, Any]:
        kind = proposal.get("kind")
        payload = {**(proposal.get("payload") or {}), **overrides}

        if kind in ("assign", "reassign"):
            driver_id = payload.get("driver_id")
            if not driver_id:
                raise ValueError("driver_id_required")
            from porterchain_api.admin_engine.operations_service import AdminOperationsService

            AdminOperationsService().assign_driver(db, settings, ctx, order_id, driver_id)
            return {"assigned_driver_id": driver_id}

        if kind == "draft_message":
            # Accepting a draft = send notify playbook
            order = db.query(Order).filter(Order.id == order_id).first()
            assert order
            return self._playbook_notify_customer(
                db, order, note=payload.get("message")
            )

        if kind == "exception_coach":
            # Propose only — UI should open exception modal; we just audit intent.
            return {
                "opened": "exception_modal",
                "suggested_state": payload.get("suggested_state"),
                "note": "Mark exception still requires human reason + confirm in UI.",
            }

        if kind in ("explain_late", "money_health", "exception_review"):
            return {"acknowledged": True}

        raise ValueError(f"proposal_kind_not_executable:{kind}")

    def _playbook_retry_dispatch(
        self, db: Session, ctx: AdminContext, order: Order
    ) -> dict[str, Any]:
        exc = (
            db.query(OrderException)
            .filter(OrderException.order_id == order.id, OrderException.status != "resolved")
            .order_by(OrderException.created_at.desc())
            .first()
        )
        if not exc:
            raise ValueError("no_open_exception")
        from porterchain_api.admin_engine.control_tower.service import ControlTowerService

        return ControlTowerService().retry_exception_dispatch(db, ctx, exc.id)

    def _playbook_notify_customer(
        self, db: Session, order: Order, *, note: str | None = None
    ) -> dict[str, Any]:
        from porterchain_api.domain.sandbox import order_is_sandbox
        from porterchain_api.notification_engine.engine import get_notification_engine

        if order_is_sandbox(order):
            raise ValueError("sandbox_orders_block_ops_customer_notify")

        customer = (
            db.query(Customer).filter(Customer.id == order.customer_id).first()
            if order.customer_id
            else None
        )
        from porterchain_api.merchant_engine.lookups import get_merchant

        merchant = get_merchant(db, order.merchant_id)
        message = note or (
            f"Your shipment {order.tracking_number} is "
            f"{order.state.replace('_', ' ').title()}. Track with this number anytime."
        )
        engine = get_notification_engine()
        sent: list[str] = []
        ctx = {
            "message": message,
            "order_id": order.id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "order_state": order.state,
            "is_sandbox": False,
        }
        tags = {"order_id": order.id}
        if customer and customer.email:
            engine.dispatch(
                db,
                event_type="ops.playbook.notify_customer",
                template_key="tracking_update",
                channel="email",
                recipient_type="customer",
                recipient_id=customer.id,
                recipient_address=customer.email,
                context=ctx,
                search_tags=tags,
                correlation_id=order.id,
            )
            sent.append(customer.email)
        elif merchant and merchant.email:
            engine.dispatch(
                db,
                event_type="ops.playbook.notify_customer",
                template_key="tracking_update",
                channel="email",
                recipient_type="merchant",
                recipient_id=merchant.id,
                recipient_address=merchant.email,
                context=ctx,
                search_tags=tags,
                correlation_id=order.id,
            )
            sent.append(merchant.email)
        else:
            raise ValueError("no_recipient_email")
        return {"sent_to": sent, "template": "tracking_update"}

    def _playbook_escalate_claim(
        self,
        db: Session,
        ctx: AdminContext,
        order: Order,
        *,
        note: str | None = None,
    ) -> dict[str, Any]:
        from porterchain_api.admin_engine.claims_service import AdminClaimsService

        claim_type = (
            "damaged_parcel"
            if order.state == OrderState.DAMAGED.value
            else "lost_parcel"
            if order.state == OrderState.LOST.value
            else "late_delivery"
        )
        c = AdminClaimsService().open_claim(
            db,
            ctx,
            order_id=order.id,
            claim_type=claim_type,
            description=note
            or f"Escalated from Order 360 playbook for {order.tracking_number} ({order.state})",
            priority="high" if order.state in {OrderState.LOST.value, OrderState.DAMAGED.value} else "normal",
        )
        return {"claim_id": c.id, "claim_type": claim_type}
