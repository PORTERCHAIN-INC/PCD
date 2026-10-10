"""Admin Customers 360: overview numbers, timeline, notes, money (credit/refund), consent,
bounce, churn, risk, 'send booking link' drafts and approval-gated reorder nudges."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.booking_models import (
    Customer,
    CustomerConsent,
    CustomerCredit,
    CustomerNote,
    Order,
    OrderRating,
    ReorderNudge,
)
from porterchain_api.config import Settings
from porterchain_api.customer_fast import privacy, rules, service

MAX_CREDIT_CENTS = 50_000
NUDGE_SETTING = "reorder_nudges_enabled"


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _customer(db: Session, customer_id: str) -> Customer:
    c = db.get(Customer, customer_id)
    if c is None:
        raise LookupError("customer_not_found")
    return c


def credit_balance(db: Session, customer_id: str) -> int:
    return int(
        db.query(func.coalesce(func.sum(CustomerCredit.amount_cents), 0))
        .filter(CustomerCredit.customer_id == customer_id)
        .scalar()
        or 0
    )


def consent_status(db: Session, customer: Customer) -> dict[str, Any]:
    from porterchain_api.crm_suppression import is_suppressed
    from porterchain_api.notification_engine.bounce import address_is_bounced

    out: dict[str, Any] = {}
    for kind in ("marketing", "reorder"):
        row = service.latest_consent(db, customer.id, kind)
        out[kind] = {
            "granted": bool(row.granted) if row else (kind == "reorder"),
            "basis": ("express" if row and row.granted and kind == "marketing" else
                      "implied (purchase)" if kind == "reorder" and (row is None or row.granted) else "withdrawn"
                      if row else "none"),
            "at": _iso(row.created_at) if row else None,
            "source": row.source if row else None,
        }
    out["suppressed"] = bool(customer.email and is_suppressed(db, email=customer.email))
    out["bounced"] = bool(customer.email and address_is_bounced(db, customer.email))
    out["deliverable"] = not (out["suppressed"] or out["bounced"])
    return out


def overview(db: Session, settings: Settings, customer_id: str) -> dict[str, Any]:
    c = _customer(db, customer_id)
    orders = (
        db.query(Order)
        .filter(Order.customer_id == c.id, Order.is_sandbox.is_(False))
        .order_by(Order.created_at.desc())
        .all()
    )
    paid = [o for o in orders if o.state not in ("CANCELLED", "REFUNDED")]
    ids = [o.id for o in orders]
    ratings = [r.score for r in db.query(OrderRating).filter(OrderRating.order_id.in_(ids)).all()] if ids else []
    delivered = [o for o in orders if o.state in ("DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED")]
    failed = [o for o in orders if o.state in rules.FAILED_STATES]
    risky = [{"tracking_number": o.tracking_number, "reasons": rules.order_risk(o)} for o in orders[:20] if rules.order_risk(o)]
    ltv = sum(int(o.amount_cents or 0) for o in paid)
    return {
        "customer_id": c.id,
        "name": c.full_name or (c.email or "").split("@")[0],
        "email": c.email,
        "phone": c.phone,
        "since": _iso(c.created_at),
        "account": "guest (no sign-in yet)" if str(c.clerk_user_id or "").startswith("pending") else "signed in",
        "numbers": {
            "orders": len(orders),
            "lifetime_value_cents": ltv,
            "avg_order_cents": int(ltv / len(paid)) if paid else 0,
            "credit_balance_cents": credit_balance(db, c.id),
            "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
            "low_ratings": sum(1 for s in ratings if s <= 3),
            "first_attempt_rate": round(len(delivered) / (len(delivered) + len(failed)), 3) if (delivered or failed) else None,
        },
        "last_order_at": _iso(orders[0].created_at) if orders else None,
        "churn": rules.churn(db, c.id),
        "risk": risky,
        "consent": consent_status(db, c),
        "privacy": {"status": c.privacy_status or "active", "jobs": privacy.jobs_for_customer(db, c.id)},
    }


def timeline(db: Session, customer_id: str, limit: int = 60) -> list[dict[str, Any]]:
    """One merged, newest-first feed: orders, ratings, notes, credits, consents, tickets."""
    from porterchain_api.admin_models import SupportTicket

    c = _customer(db, customer_id)
    items: list[dict[str, Any]] = []
    for o in db.query(Order).filter(Order.customer_id == c.id).order_by(Order.created_at.desc()).limit(limit):
        items.append({"at": _iso(o.created_at), "kind": "order", "title": f"Order {o.tracking_number}",
                      "detail": f"{o.state.replace('_', ' ').title()} · ${int(o.amount_cents or 0) / 100:.2f}",
                      "ref": o.tracking_number})
        r = db.query(OrderRating).filter(OrderRating.order_id == o.id).first()
        if r is not None:
            items.append({"at": _iso(r.created_at), "kind": "rating", "title": f"Rated {r.score}/5",
                          "detail": r.comment or "", "ref": o.tracking_number})
    for n in db.query(CustomerNote).filter(CustomerNote.customer_id == c.id).order_by(CustomerNote.created_at.desc()).limit(limit):
        items.append({"at": _iso(n.created_at), "kind": "note", "title": f"Note by {n.author}", "detail": n.body, "ref": n.id})
    for cr in db.query(CustomerCredit).filter(CustomerCredit.customer_id == c.id).order_by(CustomerCredit.created_at.desc()).limit(limit):
        items.append({"at": _iso(cr.created_at), "kind": "credit",
                      "title": f"Credit {'+' if cr.amount_cents >= 0 else ''}${cr.amount_cents / 100:.2f}",
                      "detail": f"{cr.reason} · {cr.actor}", "ref": cr.id})
    for cs in db.query(CustomerConsent).filter(CustomerConsent.customer_id == c.id).order_by(CustomerConsent.created_at.desc()).limit(limit):
        items.append({"at": _iso(cs.created_at), "kind": "consent",
                      "title": f"{cs.kind.title()} email {'on' if cs.granted else 'off'}", "detail": cs.source, "ref": cs.id})
    for t in db.query(SupportTicket).filter(SupportTicket.customer_id == c.id).order_by(SupportTicket.created_at.desc()).limit(limit):
        items.append({"at": _iso(t.created_at), "kind": "ticket", "title": t.subject, "detail": t.status, "ref": t.id})
    items.sort(key=lambda x: x["at"] or "", reverse=True)
    return items[:limit]


def add_note(db: Session, customer_id: str, *, author: str, body: str) -> dict[str, Any]:
    _customer(db, customer_id)
    text = (body or "").strip()
    if len(text) < 2:
        raise ValueError("note_empty")
    n = CustomerNote(customer_id=customer_id, author=author[:255], body=text[:2000])
    db.add(n)
    db.commit()
    return {"id": n.id, "author": n.author, "body": n.body, "created_at": _iso(n.created_at)}


def add_credit(db: Session, customer_id: str, *, amount_cents: int, reason: str, actor: str, order_id: str | None = None) -> dict[str, Any]:
    _customer(db, customer_id)
    if amount_cents == 0 or abs(amount_cents) > MAX_CREDIT_CENTS:
        raise ValueError("credit_amount_invalid")
    if len((reason or "").strip()) < 3:
        raise ValueError("reason_required")
    if amount_cents < 0 and credit_balance(db, customer_id) + amount_cents < 0:
        raise ValueError("credit_insufficient")
    db.add(CustomerCredit(customer_id=customer_id, amount_cents=int(amount_cents), reason=reason.strip()[:500],
                          actor=actor[:255], order_id=order_id))
    db.commit()
    return {"balance_cents": credit_balance(db, customer_id)}


def refund_order(db: Session, settings: Settings, customer_id: str, *, tracking_number: str,
                 amount_cents: int | None, reason: str, actor: str) -> dict[str, Any]:
    order = db.query(Order).filter(Order.tracking_number == tracking_number, Order.customer_id == customer_id).first()
    if order is None:
        raise LookupError("order_not_found")
    if len((reason or "").strip()) < 3:
        raise ValueError("reason_required")
    meta = dict(order.compliance_metadata or {}) if isinstance(order.compliance_metadata, dict) else {}
    refunds = list(meta.get("admin_refunds") or [])
    already = sum(int(r.get("amount_cents") or 0) for r in refunds if r.get("status") != "failed")
    amount = int(amount_cents if amount_cents is not None else (order.amount_cents or 0) - already)
    if amount <= 0 or already + amount > int(order.amount_cents or 0):
        raise ValueError("refund_amount_invalid")
    entry: dict[str, Any] = {"amount_cents": amount, "reason": reason.strip()[:500], "actor": actor,
                             "at": _now().isoformat(), "status": "pending_manual"}
    try:
        from porterchain_api.services.stripe_service import create_refund

        rid = create_refund(settings, order, amount, idempotency_key=f"admin-refund:{order.id}:{len(refunds)}")
        if rid:
            entry.update({"status": "refunded", "stripe_refund_id": rid})
    except Exception as exc:  # noqa: BLE001 - surfaced to staff, never swallowed silently
        entry.update({"status": "failed", "error": str(exc)[:200]})
    refunds.append(entry)
    meta["admin_refunds"] = refunds
    order.compliance_metadata = meta
    db.commit()
    return {"refund": entry, "refunded_total_cents": already + (amount if entry["status"] != "failed" else 0)}


def booking_link_draft(db: Session, settings: Settings, customer_id: str) -> dict[str, Any]:
    """A ready-to-send email *draft*. Never sends: staff copy it or send it themselves."""
    c = _customer(db, customer_id)
    last = (
        db.query(Order)
        .filter(Order.customer_id == c.id, Order.merchant_id.is_(None), Order.is_sandbox.is_(False))
        .order_by(Order.created_at.desc())
        .first()
    )
    link = service.send_again_url(settings, last) if last else f"{service._website(settings)}/en/book"
    first = (c.full_name or "").split(" ")[0] or "there"
    route = ""
    if last is not None:
        p = (last.pickup or {}).get("formatted") if isinstance(last.pickup, dict) else ""
        d = (last.dropoff or {}).get("formatted") if isinstance(last.dropoff, dict) else ""
        route = f" ({p} to {d})" if p and d else ""
    body = (
        f"Hi {first},\n\n"
        f"Here is your booking link{route}. The price shows before you pay, and there is no account to create:\n"
        f"{link}\n\n"
        "Reply to this email if anything changes.\n\nPorterChain"
    )
    return {
        "sent": False,
        "to": c.email,
        "subject": "Your PorterChain booking link",
        "body": body,
        "link": link,
        "note": "Draft only. Nothing was sent.",
    }


# --------------------------------------------------------------------------- reorder nudges


def nudges_enabled(db: Session) -> bool:
    from porterchain_api.admin_engine.platform_settings import customer_settings

    return bool(customer_settings(db).get(NUDGE_SETTING, False))


def draft_nudges(db: Session, *, now: datetime | None = None, limit: int = 200) -> dict[str, Any]:
    """Scan retail customers and draft one nudge per due customer (idempotent per last order)."""
    from porterchain_api.crm_suppression import is_suppressed

    now = now or _now()
    created = 0
    from datetime import timedelta

    # Candidates: retail customers whose latest order is 7–90 days old (newest first).
    latest = (
        db.query(Order.customer_id, func.max(Order.created_at).label("last_at"))
        .filter(Order.merchant_id.is_(None), Order.is_sandbox.is_(False), Order.customer_id.isnot(None))
        .group_by(Order.customer_id)
        .subquery()
    )
    customers = (
        db.query(Customer)
        .join(latest, latest.c.customer_id == Customer.id)
        .filter(latest.c.last_at <= now - timedelta(days=7), latest.c.last_at >= now - timedelta(days=90))
        .order_by(latest.c.last_at.desc())
        .limit(limit)
        .all()
    )
    for c in customers:
        if c.privacy_status in ("deletion_hold", "erased") or not c.email or is_suppressed(db, email=c.email):
            continue
        consent = service.latest_consent(db, c.id, "reorder")
        if consent is not None and not consent.granted:
            continue
        due, reason = rules.reorder_due(db, c.id, now=now)
        if not due:
            continue
        last = (
            db.query(Order)
            .filter(Order.customer_id == c.id, Order.merchant_id.is_(None), Order.state != "CANCELLED")
            .order_by(Order.created_at.desc())
            .first()
        )
        if last is None:
            continue
        if db.query(ReorderNudge.id).filter(ReorderNudge.customer_id == c.id, ReorderNudge.order_id == last.id).first():
            continue
        db.add(ReorderNudge(customer_id=c.id, order_id=last.id, status="draft", reason=reason[:255]))
        created += 1
    db.commit()
    return {"drafted": created, "enabled": nudges_enabled(db)}


def list_nudges(db: Session, status: str = "draft") -> dict[str, Any]:
    rows = db.query(ReorderNudge).filter(ReorderNudge.status == status).order_by(ReorderNudge.created_at.desc()).limit(200).all()
    out = []
    for n in rows:
        c = db.get(Customer, n.customer_id)
        o = db.get(Order, n.order_id)
        out.append({"id": n.id, "customer_id": n.customer_id, "email": c.email if c else None,
                    "name": c.full_name if c else None, "last_tracking": o.tracking_number if o else None,
                    "reason": n.reason, "status": n.status, "created_at": _iso(n.created_at)})
    return {"enabled": nudges_enabled(db), "nudges": out}


def decide_nudges(db: Session, settings: Settings, ids: list[str], *, approve: bool, actor: str) -> dict[str, Any]:
    """Approve → queue through the notification router (customer.reorder_nudge). Skip → closed."""
    if approve and not nudges_enabled(db):
        raise PermissionError("reorder_nudges_disabled")
    from porterchain_shared.events.catalog import DomainEventType

    from porterchain_api.booking_engine._core import emit_event

    done = 0
    for n in db.query(ReorderNudge).filter(ReorderNudge.id.in_(ids), ReorderNudge.status == "draft").all():
        n.decided_at = _now()
        n.approved_by = actor[:255]
        if not approve:
            n.status = "skipped"
            done += 1
            continue
        c = db.get(Customer, n.customer_id)
        o = db.get(Order, n.order_id)
        if c is None or o is None:
            n.status = "skipped"
            continue
        n.status = "queued"
        emit_event(
            db,
            event_type=DomainEventType.CUSTOMER_REORDER_NUDGE,
            aggregate_type="customer",
            aggregate_id=c.id,
            actor_type="admin",
            actor_id=actor,
            payload={
                "customer_id": c.id,
                "order_id": o.id,
                "tracking_number": o.tracking_number,
                "send_again_email": c.email,
                "send_again_url": service.send_again_url(settings, o),
                "unsubscribe_url": service.preferences_url(settings, c),
                "nudge": True,
                "locale": rules.order_locale(o),
            },
        )
        done += 1
    db.commit()
    return {"decided": done}
