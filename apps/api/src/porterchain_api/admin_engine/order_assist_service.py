"""Order 360 scoped assist — propose-only; writes require explicit Confirm.

Rules-based (no silent LLM writes). Uses existing assign / exception / invoice /
notification / claims APIs. Never advances Accept→Delivered (Fleetbase-owned).
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.dispatch_suggestions_service import DispatchSuggestionsService
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.invoice_service import InvoiceService
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_models import Merchant
from porterchain_api.models import Customer, Order, OrderException

logger = logging.getLogger(__name__)

WAITING_ASSIGN = {
    OrderState.BOOKED.value,
    OrderState.DISPATCH_READY.value,
    OrderState.DRIVER_REJECTED.value,
}
IN_FLIGHT = {
    OrderState.DRIVER_ASSIGNED.value,
    OrderState.DRIVER_ACCEPTED.value,
    OrderState.DRIVER_EN_ROUTE.value,
    OrderState.AT_PICKUP.value,
    OrderState.PICKED_UP.value,
    OrderState.IN_TRANSIT.value,
    OrderState.AT_DESTINATION.value,
}
EXCEPTION_STATES = {
    OrderState.FAILED.value,
    OrderState.RETURN_TO_SENDER.value,
    OrderState.LOST.value,
    OrderState.DAMAGED.value,
}


def _pid(*parts: str) -> str:
    raw = ":".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


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
                "fleetbase_execution_blocked": True,
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
            db.flush()
            return {"ok": True, "decision": "reject", "proposal_id": proposal_id}

        result = self._execute_proposal(db, settings, ctx, order_id, proposal, payload or {})
        db.flush()
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

        db.flush()
        return {"ok": True, "playbook_id": playbook_id, "result": result}

    # --- proposals ---------------------------------------------------------

    def _assign_proposals(self, db: Session, order: Order) -> list[dict[str, Any]]:
        if order.state not in WAITING_ASSIGN and not (
            order.state == OrderState.DRIVER_ASSIGNED.value
        ):
            return []
        try:
            ranked = self._suggestions.suggest(db, order.id)
        except Exception:  # noqa: BLE001
            return []
        drivers = ranked.get("drivers") or []
        if not drivers:
            return []
        best = drivers[0]
        kind = "reassign" if order.assigned_driver_id else "assign"
        return [
            {
                "id": _pid(kind, order.id, best["id"]),
                "kind": kind,
                "title": f"{'Reassign' if kind == 'reassign' else 'Assign'} → {best.get('name')}",
                "summary": (
                    f"Ranked suggestion for {order.tracking_number}"
                    + (f" · ETA ~{best.get('eta_minutes')} min" if best.get("eta_minutes") is not None else "")
                ),
                "confidence": "high" if (best.get("score") or 0) >= 70 else "medium",
                "preview": {
                    "driver_id": best["id"],
                    "driver_name": best.get("name"),
                    "score": best.get("score"),
                    "eta_minutes": best.get("eta_minutes"),
                    "reasons": best.get("reasons") or [],
                },
                "requires_confirm": True,
                "payload": {"driver_id": best["id"]},
            }
        ]

    def _exception_proposals(self, db: Session, order: Order) -> list[dict[str, Any]]:
        if order.state in EXCEPTION_STATES:
            return [
                {
                    "id": _pid("exception_review", order.id, order.state),
                    "kind": "exception_review",
                    "title": f"Review {order.state.replace('_', ' ').title()}",
                    "summary": "Exception already set — use Retry dispatch playbook or open claim.",
                    "confidence": "high",
                    "preview": {"state": order.state},
                    "requires_confirm": False,
                    "payload": {},
                }
            ]
        if order.state not in {
            OrderState.AT_PICKUP.value,
            OrderState.IN_TRANSIT.value,
            OrderState.AT_DESTINATION.value,
            OrderState.DELIVERED.value,
            OrderState.DRIVER_EN_ROUTE.value,
        }:
            return []
        # Coach: prefer Failed for mid-flight, Return after pickup, Lost/Damaged after delivered.
        if order.state == OrderState.DELIVERED.value:
            suggestion = "DAMAGED"
            why = "Delivered but issue reported → Damaged (or Lost if missing)."
        elif order.state in {OrderState.PICKED_UP.value, OrderState.IN_TRANSIT.value, OrderState.AT_DESTINATION.value}:
            suggestion = "FAILED"
            why = "In execution with a stop problem → Failed first; return path after FAILED."
        else:
            suggestion = "FAILED"
            why = "Cannot complete pickup → Failed; then retry dispatch if recoverable."
        return [
            {
                "id": _pid("exception_coach", order.id, suggestion),
                "kind": "exception_coach",
                "title": f"If exception needed → {suggestion.replace('_', ' ').title()}",
                "summary": why,
                "confidence": "medium",
                "preview": {
                    "suggested_state": suggestion,
                    "note": "Confirm opens Mark exception — does not auto-transition.",
                },
                "requires_confirm": True,
                "payload": {"suggested_state": suggestion},
            }
        ]

    def _late_and_money(self, db: Session, order: Order) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        # Late / risk from SLA-ish heuristics on scheduled_at
        late_bits: list[str] = []
        if order.scheduled_at and order.state in IN_FLIGHT | WAITING_ASSIGN:
            age_h = (datetime.now(UTC) - order.scheduled_at.astimezone(UTC)).total_seconds() / 3600
            if age_h > 4:
                late_bits.append(f"Scheduled {age_h:.1f}h ago — likely at risk.")
            elif age_h > 2:
                late_bits.append(f"Scheduled {age_h:.1f}h ago — monitor ETA.")
        if order.fleetbase_order_id:
            late_bits.append(f"Execution truth is Fleetbase `{order.fleetbase_order_id}`.")
        else:
            late_bits.append("No Fleetbase order id yet — sync/assign may be incomplete.")
        if not order.assigned_driver_id and order.state in WAITING_ASSIGN:
            late_bits.append("Unassigned — primary delay cause is waiting dispatch.")
        out.append(
            {
                "id": _pid("explain_late", order.id),
                "kind": "explain_late",
                "title": "Why might this be late?",
                "summary": " ".join(late_bits) if late_bits else "No delay signals from PC state.",
                "confidence": "medium",
                "preview": {"bullets": late_bits},
                "requires_confirm": False,
                "payload": {},
            }
        )

        money_bits: list[str] = []
        inv = None
        if order.id:
            from porterchain_api.booking_models import Invoice

            inv = db.query(Invoice).filter(Invoice.order_id == order.id).first()
        if inv:
            money_bits.append(f"Invoice {inv.invoice_number} on file.")
            if not inv.stripe_receipt_url and not inv.pdf_url:
                money_bits.append("No hosted receipt URL — use Resend receipt (HTML email) or Invoice PDF.")
        elif order.state == OrderState.POD_COMPLETED.value:
            money_bits.append("POD complete — Generate invoice is ready.")
        elif order.state in {OrderState.DELIVERED.value}:
            money_bits.append("Delivered — wait for POD then invoice, or check Fleetbase POD.")
        else:
            money_bits.append("No invoice yet (expected until POD_COMPLETED).")
        out.append(
            {
                "id": _pid("money_health", order.id),
                "kind": "money_health",
                "title": "Money health",
                "summary": " ".join(money_bits),
                "confidence": "high",
                "preview": {"bullets": money_bits, "invoice_number": inv.invoice_number if inv else None},
                "requires_confirm": False,
                "payload": {},
            }
        )
        return out

    def _message_drafts(self, db: Session, order: Order) -> list[dict[str, Any]]:
        customer = (
            db.query(Customer).filter(Customer.id == order.customer_id).first()
            if order.customer_id
            else None
        )
        merchant = (
            db.query(Merchant).filter(Merchant.id == order.merchant_id).first()
            if order.merchant_id
            else None
        )
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
        return [
            {
                "id": _pid("draft_message", order.id),
                "kind": "draft_message",
                "title": "Draft customer update",
                "summary": f"Preview for {who}. Confirm sends email via Notify customer playbook.",
                "confidence": "high",
                "preview": {"sms": sms, "email_body": email_body, "recipient": who},
                "requires_confirm": True,
                "payload": {"channel": "email", "message": email_body},
            }
        ]

    def _playbooks(self, db: Session, order: Order) -> list[dict[str, Any]]:
        open_exc = (
            db.query(OrderException)
            .filter(OrderException.order_id == order.id, OrderException.status != "resolved")
            .order_by(OrderException.created_at.desc())
            .first()
        )
        has_invoice = False
        from porterchain_api.booking_models import Invoice

        has_invoice = (
            db.query(Invoice.id).filter(Invoice.order_id == order.id).first() is not None
        )
        has_claim = False
        try:
            from porterchain_api.admin_models import Claim

            has_claim = (
                db.query(Claim.id).filter(Claim.order_id == order.id).first() is not None
            )
        except Exception:  # noqa: BLE001
            has_claim = False

        retry_ok = order.state == OrderState.FAILED.value and open_exc is not None
        notify_ok = bool(order.customer_id or order.merchant_id)
        claim_ok = order.state in EXCEPTION_STATES | {
            OrderState.DELIVERED.value,
            OrderState.POD_COMPLETED.value,
            OrderState.DAMAGED.value,
            OrderState.LOST.value,
        }
        invoice_ok = order.state in {
            OrderState.POD_COMPLETED.value,
            OrderState.INVOICED.value,
        }
        resend_ok = has_invoice

        return [
            {
                "id": "retry_dispatch",
                "label": "Retry dispatch",
                "description": "FAILED → DISPATCH_READY and resolve open exception",
                "enabled": retry_ok,
                "disabled_reason": None
                if retry_ok
                else "Needs FAILED order with an open exception",
            },
            {
                "id": "notify_customer",
                "label": "Notify customer",
                "description": "Send tracking_update email (HTML) to customer/merchant",
                "enabled": notify_ok,
                "disabled_reason": None if notify_ok else "No customer/merchant on order",
            },
            {
                "id": "escalate_claim",
                "label": "Escalate claim",
                "description": "Open a claim on this order for investigation",
                "enabled": claim_ok and not has_claim,
                "disabled_reason": (
                    "Claim already exists"
                    if has_claim
                    else None
                    if claim_ok
                    else "Order state not claim-eligible"
                ),
            },
            {
                "id": "generate_invoice",
                "label": "Generate invoice",
                "description": "POD_COMPLETED → INVOICED (idempotent)",
                "enabled": invoice_ok,
                "disabled_reason": None
                if invoice_ok
                else "Requires POD_COMPLETED or already INVOICED",
            },
            {
                "id": "resend_receipt",
                "label": "Resend receipt",
                "description": "Re-send HTML receipt email",
                "enabled": resend_ok,
                "disabled_reason": None if resend_ok else "No invoice on order",
            },
        ]

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
        from porterchain_api.notification_engine.engine import get_notification_engine

        customer = (
            db.query(Customer).filter(Customer.id == order.customer_id).first()
            if order.customer_id
            else None
        )
        merchant = (
            db.query(Merchant).filter(Merchant.id == order.merchant_id).first()
            if order.merchant_id
            else None
        )
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
