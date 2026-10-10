"""Reminder emails queued as drafts; an admin approves them in bulk. Nothing sends on
its own: ``queue_drafts`` only writes rows, ``approve`` is the single send path and it
goes through the existing, audited invoice reminder."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.billing_engine.models import FinanceReminderDraft
from porterchain_api.booking_models import Invoice

RECENTLY_REMINDED = timedelta(days=3)


def _aware(dt: datetime | None) -> datetime | None:
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=UTC)


def _preview(db: Session, invoice: Invoice) -> tuple[str, str]:
    """Exactly what the reminder email will say (same template, same payload)."""
    from porterchain_api.booking_engine.invoice_service import InvoiceService
    from porterchain_api.booking_models import Order
    from porterchain_api.notification_engine.templates import render_email

    order = db.get(Order, invoice.order_id) if invoice.order_id else None
    payload = InvoiceService()._invoice_event_payload(db, order, invoice)
    payload["reminder"] = True
    subject, text, _html = render_email("merchant_invoice_ready", payload)
    return subject, text


def queue_drafts(db: Session, *, now: datetime | None = None) -> dict[str, int]:
    """One draft per merchant with overdue invoices not reminded in the last 3 days."""
    from porterchain_api.finance_ops.cash import ar_by_merchant
    from porterchain_api.merchant_engine.lookups import get_merchant
    from porterchain_api.merchant_engine.invoice_reminder import primary_billing_email

    now = now or datetime.now(UTC)
    created = updated = 0
    for m in ar_by_merchant(db):
        if m["oldest_days"] <= 0:
            continue
        invoices = [db.get(Invoice, i) for i in m["invoice_ids"] if i]
        due = [
            inv for inv in invoices
            if inv is not None and not (_aware(inv.last_reminded_at) and now - _aware(inv.last_reminded_at) < RECENTLY_REMINDED)
        ]
        if not due:
            continue
        merchant = get_merchant(db, m["merchant_id"])
        subject, body = _preview(db, due[0])
        if len(due) > 1:
            body += f"\n\n(+{len(due) - 1} more invoice email(s), one per invoice: " + ", ".join(
                i.invoice_number for i in due[1:]
            ) + ")"
        draft = (
            db.query(FinanceReminderDraft)
            .filter(FinanceReminderDraft.merchant_id == m["merchant_id"], FinanceReminderDraft.status == "draft")
            .first()
        )
        if draft is None:
            draft = FinanceReminderDraft(merchant_id=m["merchant_id"], subject=subject, body=body)
            db.add(draft)
            created += 1
        else:
            updated += 1
        draft.invoice_ids = [i.id for i in due]
        draft.to_email = primary_billing_email(merchant) if merchant else None
        draft.subject, draft.body = subject[:255], body
        draft.amount_cents = m["outstanding_cents"]
        draft.oldest_days = m["oldest_days"]
    db.commit()
    return {"created": created, "updated": updated}


def list_drafts(db: Session, *, status: str = "draft") -> list[dict[str, Any]]:
    from porterchain_api.platform.merchant_billing import merchant_display_name

    rows = (
        db.query(FinanceReminderDraft)
        .filter(FinanceReminderDraft.status == status)
        .order_by(FinanceReminderDraft.oldest_days.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": d.id,
            "merchant_id": d.merchant_id,
            "merchant_name": merchant_display_name(db, d.merchant_id),
            "to_email": d.to_email,
            "subject": d.subject,
            "body": d.body,
            "invoice_count": len(d.invoice_ids or []),
            "amount_cents": d.amount_cents,
            "oldest_days": d.oldest_days,
            "status": d.status,
            "created_at": d.created_at,
        }
        for d in rows
    ]


def decide(db: Session, ctx: Any, ids: list[str], *, approve: bool) -> dict[str, Any]:
    """Approve (send via the audited reminder path) or discard drafts, in bulk."""
    from porterchain_api.merchant_engine.invoice_reminder import remind_invoice
    from porterchain_api.merchant_engine.lookups import get_merchant
    from porterchain_api.platform.admin_audit import log_admin_audit

    done = skipped = sent = 0
    errors: list[str] = []
    for d in db.query(FinanceReminderDraft).filter(FinanceReminderDraft.id.in_(ids[:200])).with_for_update().all():
        if d.status != "draft":
            skipped += 1
            continue
        d.decided_by = ctx.user.id
        d.decided_at = datetime.now(UTC)
        if not approve:
            d.status = "discarded"
            done += 1
            continue
        merchant = get_merchant(db, d.merchant_id)
        if not merchant or not d.to_email:
            d.status = "failed"
            errors.append(f"{d.id}:billing_contact_missing")
            continue
        for inv_id in d.invoice_ids or []:
            inv = db.get(Invoice, inv_id)
            if inv is None:
                continue
            try:
                remind_invoice(db, inv, merchant, actor_type="admin", actor_id=ctx.user.id)
                sent += 1
            except (LookupError, ValueError) as exc:
                errors.append(f"{inv_id}:{exc}")
        d.status = "sent"
        done += 1
    log_admin_audit(
        db, ctx, action="finance.reminders.approve" if approve else "finance.reminders.discard",
        resource_type="finance_reminder_draft", resource_id=",".join(ids[:20]),
        payload={"drafts": done, "emails": sent, "skipped": skipped, "errors": errors[:20]},
    )
    db.commit()
    return {"decided": done, "emails_sent": sent, "skipped": skipped, "errors": errors}
