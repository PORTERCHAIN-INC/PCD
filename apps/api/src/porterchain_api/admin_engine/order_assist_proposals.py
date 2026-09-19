"""Order-assist propose-only catalog — assign, exception, late/money, playbooks."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import Claim
from porterchain_api.booking_models import Invoice, Order, OrderException
from porterchain_api.domain.states import OrderState

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


def proposal_id(*parts: str) -> str:
    raw = ":".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def assign_proposals(svc: Any, db: Session, order: Order) -> list[dict[str, Any]]:
    if order.state not in WAITING_ASSIGN and not (
        order.state == OrderState.DRIVER_ASSIGNED.value
    ):
        return []
    try:
        ranked = svc._suggestions.suggest(db, order.id)
    except Exception:  # noqa: BLE001
        return []
    drivers = ranked.get("drivers") or []
    if not drivers:
        return []
    best = drivers[0]
    kind = "reassign" if order.assigned_driver_id else "assign"
    eta_min = best.get("eta_minutes")
    eta_src = best.get("eta_source") or ""
    if eta_min is None:
        eta_bit = ""
    elif eta_src in {"valhalla", "osrm", "matrix", "routing"}:
        eta_bit = f" · {round(float(eta_min))}m road"
    elif eta_src == "haversine":  # fleetbase-first:ok — label only, no distance math
        eta_bit = " · no road ETA"
    else:
        eta_bit = f" · ~{eta_min} min"
    return [
        {
            "id": proposal_id(kind, order.id, best["id"]),
            "kind": kind,
            "title": f"{'Reassign' if kind == 'reassign' else 'Assign'} → {best.get('name')}",
            "summary": f"Ranked suggestion for {order.tracking_number}{eta_bit}",
            "confidence": "high" if (best.get("score") or 0) >= 70 else "medium",
            "preview": {
                "driver_id": best["id"],
                "driver_name": best.get("name"),
                "score": best.get("score"),
                "eta_minutes": eta_min,
                "eta_source": eta_src or None,
                "reasons": best.get("reasons") or [],
            },
            "requires_confirm": True,
            "payload": {"driver_id": best["id"]},
        }
    ]


def exception_proposals(order: Order) -> list[dict[str, Any]]:
    if order.state in EXCEPTION_STATES:
        return [
            {
                "id": proposal_id("exception_review", order.id, order.state),
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
            "id": proposal_id("exception_coach", order.id, suggestion),
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


def late_and_money(db: Session, order: Order) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
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
            "id": proposal_id("explain_late", order.id),
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
    inv = db.query(Invoice).filter(Invoice.order_id == order.id).first() if order.id else None
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
            "id": proposal_id("money_health", order.id),
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


def playbooks(db: Session, order: Order) -> list[dict[str, Any]]:
    open_exc = (
        db.query(OrderException)
        .filter(OrderException.order_id == order.id, OrderException.status != "resolved")
        .order_by(OrderException.created_at.desc())
        .first()
    )
    has_invoice = db.query(Invoice.id).filter(Invoice.order_id == order.id).first() is not None
    try:
        has_claim = db.query(Claim.id).filter(Claim.order_id == order.id).first() is not None
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
            "disabled_reason": None if retry_ok else "Needs FAILED order with an open exception",
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
            "disabled_reason": None if invoice_ok else "Requires POD_COMPLETED or already INVOICED",
        },
        {
            "id": "resend_receipt",
            "label": "Resend receipt",
            "description": "Re-send HTML receipt email",
            "enabled": resend_ok,
            "disabled_reason": None if resend_ok else "No invoice on order",
        },
    ]
