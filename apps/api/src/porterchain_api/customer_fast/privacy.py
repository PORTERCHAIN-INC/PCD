"""PIPEDA / GDPR erasure as a reviewable job.

request → automatic plan (what is erased, what is kept and why) → staff approve or reject
→ execution (anonymise in place, keep tax records) → result stored on the job.
Nothing is erased without a named reviewer.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_models import (
    Customer,
    CustomerAddress,
    CustomerConsent,
    CustomerNote,
    Order,
    OrderRating,
    PrivacyDeletionJob,
    Quote,
)

SLA_DAYS = 30
RETAIN_YEARS = 6  # CRA books-and-records retention for invoices / payments
_PII_KEYS = ("contact_name", "name", "phone", "email", "notes", "instructions", "unit", "buzzer")


def _now() -> datetime:
    return datetime.now(UTC)


def _job_out(job: PrivacyDeletionJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "reference": job.reference,
        "customer_id": job.customer_id,
        "status": job.status,
        "source": job.source,
        "plan": job.plan,
        "result": job.result,
        "reviewer": job.reviewer,
        "review_note": job.review_note,
        "due_at": job.due_at.isoformat() if job.due_at else None,
        "reviewed_at": job.reviewed_at.isoformat() if job.reviewed_at else None,
        "executed_at": job.executed_at.isoformat() if job.executed_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


def build_plan(db: Session, customer: Customer) -> dict[str, Any]:
    orders = db.query(Order).filter(Order.customer_id == customer.id).all()
    active = [o.tracking_number for o in orders if o.state not in ("DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED", "CANCELLED", "REFUNDED", "FAILED", "RETURN_TO_SENDER")]
    return {
        "erase": {
            "profile": ["name", "email", "phone", "sign-in link"],
            "addresses": db.query(CustomerAddress).filter(CustomerAddress.customer_id == customer.id).count(),
            "staff_notes": db.query(CustomerNote).filter(CustomerNote.customer_id == customer.id).count(),
            "rating_comments": db.query(OrderRating).join(Order, Order.id == OrderRating.order_id)
            .filter(Order.customer_id == customer.id, OrderRating.comment.isnot(None)).count(),
            "order_contact_details": len(orders),
        },
        "keep": {
            "orders_and_invoices": len(orders),
            "why": f"Tax law requires invoices and payments for {RETAIN_YEARS} years. "
            "They are kept without name, email, phone or street address (postal area only).",
            "consent_log": "Kept without IP to prove what was consented to (CASL).",
            "do_not_contact": "Email is added to the hashed do-not-contact list so we never email it again.",
        },
        "blockers": {"active_deliveries": active},
        "stripe_customer": bool(customer.stripe_customer_id),
    }


def open_job(db: Session, customer: Customer, *, reference: str, source: str) -> PrivacyDeletionJob:
    existing = (
        db.query(PrivacyDeletionJob)
        .filter(PrivacyDeletionJob.customer_id == customer.id, PrivacyDeletionJob.status == "pending_review")
        .first()
    )
    if existing:
        return existing
    job = PrivacyDeletionJob(
        customer_id=customer.id,
        reference=reference,
        status="pending_review",
        source=source[:64],
        plan=build_plan(db, customer),
        due_at=_now() + timedelta(days=SLA_DAYS),
    )
    db.add(job)
    db.flush()
    return job


def list_jobs(db: Session, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    q = db.query(PrivacyDeletionJob)
    if status:
        q = q.filter(PrivacyDeletionJob.status == status)
    return [_job_out(j) for j in q.order_by(PrivacyDeletionJob.created_at.desc()).limit(limit).all()]


def jobs_for_customer(db: Session, customer_id: str) -> list[dict[str, Any]]:
    rows = (
        db.query(PrivacyDeletionJob)
        .filter(PrivacyDeletionJob.customer_id == customer_id)
        .order_by(PrivacyDeletionJob.created_at.desc())
        .all()
    )
    return [_job_out(j) for j in rows]


def _get(db: Session, job_id: str) -> PrivacyDeletionJob:
    job = db.get(PrivacyDeletionJob, job_id)
    if job is None:
        raise LookupError("job_not_found")
    return job


def _strip(addr: Any) -> Any:
    if not isinstance(addr, dict):
        return addr
    from porterchain_api.customer_fast.geo import postal_of

    postal = postal_of(addr)
    return {"formatted": (postal or "")[:3] or "redacted", "postal": (postal or "")[:3] or None, "redacted": True}


def reject(db: Session, job_id: str, *, reviewer: str, note: str) -> dict[str, Any]:
    job = _get(db, job_id)
    if job.status != "pending_review":
        raise ValueError("job_not_pending")
    if len((note or "").strip()) < 5:
        raise ValueError("note_required")
    job.status = "rejected"
    job.reviewer = reviewer
    job.review_note = note.strip()[:1000]
    job.reviewed_at = _now()
    customer = db.get(Customer, job.customer_id) if job.customer_id else None
    if customer is not None and customer.privacy_status == "deletion_hold":
        customer.privacy_status = None
    db.commit()
    return _job_out(job)


def approve_and_execute(db: Session, job_id: str, *, reviewer: str, note: str | None = None) -> dict[str, Any]:
    job = _get(db, job_id)
    if job.status != "pending_review":
        raise ValueError("job_not_pending")
    customer = db.get(Customer, job.customer_id) if job.customer_id else None
    if customer is None:
        raise LookupError("customer_not_found")
    plan = build_plan(db, customer)
    if plan["blockers"]["active_deliveries"]:
        raise ValueError("active_deliveries")

    from porterchain_api.crm_models import CrmSuppression
    from porterchain_api.crm_suppression import hash_contact, normalize_email

    counts: dict[str, int] = {}
    email_n = normalize_email(customer.email)
    if email_n:
        h = hash_contact("email", email_n)
        if not db.query(CrmSuppression.id).filter(CrmSuppression.hash_kind == "email", CrmSuppression.value_hash == h).first():
            db.add(CrmSuppression(hash_kind="email", value_hash=h, source="privacy_erasure"))
    counts["addresses"] = db.query(CustomerAddress).filter(CustomerAddress.customer_id == customer.id).delete()
    counts["staff_notes"] = db.query(CustomerNote).filter(CustomerNote.customer_id == customer.id).delete()
    for c in db.query(CustomerConsent).filter(CustomerConsent.customer_id == customer.id).all():
        c.ip_hash = None
    orders = db.query(Order).filter(Order.customer_id == customer.id).all()
    for o in orders:
        o.pickup = _strip(o.pickup)
        o.dropoff = _strip(o.dropoff)
        o.special_instructions = None
        r = db.query(OrderRating).filter(OrderRating.order_id == o.id).first()
        if r is not None:
            r.comment = None
    counts["orders_redacted"] = len(orders)
    for q in db.query(Quote).filter(Quote.customer_id == customer.id).all():
        q.email = None
        q.phone = None
        q.pickup = _strip(q.pickup)
        q.dropoff = _strip(q.dropoff)
        q.additional_stops = [_strip(s) for s in (q.additional_stops or [])] or None
    short = customer.id[:8]
    customer.email = f"erased+{short}@invalid.porterchain.local"
    customer.full_name = None
    customer.phone = None
    customer.visitor_session_id = None
    customer.clerk_user_id = f"erased:{customer.id}"
    customer.privacy_status = "erased"
    now = _now()
    job.status = "executed"
    job.reviewer = reviewer
    job.review_note = (note or "").strip()[:1000] or None
    job.reviewed_at = now
    job.executed_at = now
    job.result = {**counts, "stripe_customer": "delete in Stripe dashboard" if plan["stripe_customer"] else "none"}
    db.commit()
    return _job_out(job)
