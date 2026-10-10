"""Credit limit and hold. Merchants pay by Interac e-Transfer, so the only lever is
"no new bookings until the overdue invoice is paid". Rules:

* manual hold: set by admin / super admin / finance with a reason.
* auto hold: any invoice overdue more than ``grace_days`` (policy, default 7).
  Lifts itself once the overdue invoices are marked paid.
* limit: outstanding >= credit_limit_cents blocks (existing behaviour).
* override: a money editor may allow bookings until a time (max 14 days).
Every change writes the merchant audit log (resource_type="credit").
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.merchant_models import Merchant

POLICY_KEY = "merchant_credit_policy"
DEFAULT_POLICY: dict[str, Any] = {"auto_hold": True, "grace_days": 7}
MAX_OVERRIDE_DAYS = 14


def credit_policy(db: Session) -> dict[str, Any]:
    try:
        from porterchain_api.merchant_engine.account_ops.lookups import system_config

        value = system_config(db, POLICY_KEY)
        raw = value if isinstance(value, dict) else {}
    except Exception:  # noqa: BLE001 — policy read must never block booking on its own
        raw = {}
    policy = {**DEFAULT_POLICY, **{k: v for k, v in raw.items() if k in DEFAULT_POLICY}}
    try:
        policy["grace_days"] = max(0, min(90, int(policy["grace_days"])))
    except (TypeError, ValueError):
        policy["grace_days"] = DEFAULT_POLICY["grace_days"]
    policy["auto_hold"] = bool(policy["auto_hold"])
    return policy


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def overdue_invoices(db: Session, merchant: Merchant, *, now: datetime | None = None) -> list[dict[str, Any]]:
    from porterchain_api.merchant_engine.billing_views import overdue_invoice_rows

    return overdue_invoice_rows(db, merchant, now=now or datetime.now(UTC))


def credit_state(db: Session, merchant: Merchant, *, now: datetime | None = None) -> dict[str, Any]:
    """Pure read: what would happen if this merchant booked now, and why."""
    from porterchain_api.merchant_engine.billing_views import ar_snapshot

    now = now or datetime.now(UTC)
    policy = credit_policy(db)
    ar = ar_snapshot(db, merchant)
    overdue = overdue_invoices(db, merchant, now=now)
    oldest = overdue[0]["days_overdue"] if overdue else 0
    limit = merchant.credit_limit_cents if (merchant.credit_limit_cents or 0) > 0 else None
    override_until = _aware(merchant.credit_override_until)
    override_active = bool(override_until and override_until > now)

    reasons: list[str] = []
    mode = merchant.credit_hold_mode or "none"
    if mode == "manual":
        reasons.append(merchant.credit_hold_reason or "Manual credit hold")
    auto_due = policy["auto_hold"] and bool(overdue) and oldest > policy["grace_days"]
    if auto_due:
        reasons.append(f"Invoice overdue {oldest} days (grace {policy['grace_days']})")
    over_limit = limit is not None and ar.outstanding_cents >= limit
    if over_limit:
        reasons.append("At credit limit")

    blocked = bool(reasons) and not override_active
    return {
        "mode": mode,
        "blocked": blocked,
        "reasons": reasons,
        "auto_hold_due": auto_due,
        "limit_cents": limit,
        "outstanding_cents": ar.outstanding_cents,
        "overdue_cents": ar.overdue_cents,
        "headroom_cents": (limit - ar.outstanding_cents) if limit is not None else None,
        "oldest_overdue_days": oldest,
        "overdue_invoices": overdue[:10],
        "override_until": override_until.isoformat() if override_active else None,
        "hold_since": merchant.credit_hold_at.isoformat() if merchant.credit_hold_at else None,
        "policy": policy,
        "payment_method": "interac_etransfer",
    }


def sync_auto_hold(db: Session, merchant: Merchant, *, now: datetime | None = None) -> str | None:
    """Apply or lift the automatic hold. Returns 'applied' / 'lifted' / None. Never touches manual."""
    from porterchain_api.merchant_models import MerchantAuditLog

    now = now or datetime.now(UTC)
    if merchant.credit_hold_mode == "manual":
        return None
    state = credit_state(db, merchant, now=now)
    change: str | None = None
    if state["auto_hold_due"] and merchant.credit_hold_mode != "auto":
        merchant.credit_hold_mode = "auto"
        merchant.credit_hold_reason = state["reasons"][0] if state["reasons"] else "Overdue invoice"
        merchant.credit_hold_at = now
        change = "applied"
    elif not state["auto_hold_due"] and merchant.credit_hold_mode == "auto":
        merchant.credit_hold_mode = "none"
        merchant.credit_hold_reason = None
        merchant.credit_hold_at = None
        change = "lifted"
    if change:
        db.add(
            MerchantAuditLog(
                merchant_id=merchant.id,
                actor_user_id="system:credit_guard",
                action=f"credit.auto_hold_{change}",
                resource_type="credit",
                resource_id=merchant.id,
                payload={
                    "changes": {"credit_hold_mode": {"old": "none" if change == "applied" else "auto",
                                                     "new": merchant.credit_hold_mode}},
                    "oldest_overdue_days": state["oldest_overdue_days"],
                    "overdue_cents": state["overdue_cents"],
                },
            )
        )
        db.flush()
    return change


def assert_can_book(db: Session, merchant: Merchant) -> None:
    """Booking gate. Raises ValueError('credit_hold:<reason>') when blocked."""
    sync_auto_hold(db, merchant)
    state = credit_state(db, merchant)
    if state["blocked"]:
        raise ValueError("credit_hold:" + "; ".join(state["reasons"]))


def set_credit(
    db: Session,
    ctx: Any,
    merchant: Merchant,
    *,
    action: str,
    reason: str | None = None,
    limit_cents: int | None = None,
    override_days: int | None = None,
) -> dict[str, Any]:
    """action: hold | release | limit | override | clear_override."""
    from porterchain_api.merchant_engine.account_ops import staff_audit

    # Role gate (admin / super admin / finance) is enforced by the admin router.
    now = datetime.now(UTC)
    note = (reason or "").strip()
    before = {
        "credit_hold_mode": merchant.credit_hold_mode,
        "credit_limit_cents": merchant.credit_limit_cents,
        "credit_override_until": merchant.credit_override_until.isoformat()
        if merchant.credit_override_until else None,
    }
    if action == "hold":
        if not note:
            raise ValueError("reason_required")
        merchant.credit_hold_mode = "manual"
        merchant.credit_hold_reason = note[:255]
        merchant.credit_hold_at = now
    elif action == "release":
        if not note:
            raise ValueError("reason_required")
        merchant.credit_hold_mode = "none"
        merchant.credit_hold_reason = None
        merchant.credit_hold_at = None
    elif action == "limit":
        if limit_cents is not None and limit_cents < 0:
            raise ValueError("credit_limit_invalid")
        merchant.credit_limit_cents = limit_cents or None
    elif action == "override":
        if not note:
            raise ValueError("reason_required")
        days = int(override_days or 1)
        if days < 1 or days > MAX_OVERRIDE_DAYS:
            raise ValueError("override_days_invalid")
        merchant.credit_override_until = now + timedelta(days=days)
    elif action == "clear_override":
        merchant.credit_override_until = None
    else:
        raise ValueError("credit_action_invalid")
    after = {
        "credit_hold_mode": merchant.credit_hold_mode,
        "credit_limit_cents": merchant.credit_limit_cents,
        "credit_override_until": merchant.credit_override_until.isoformat()
        if merchant.credit_override_until else None,
    }
    staff_audit(
        db,
        ctx,
        merchant.id,
        action=f"credit.{action}",
        resource_type="credit",
        resource_id=merchant.id,
        payload={
            "reason": note or None,
            "changes": {k: {"old": before[k], "new": after[k]} for k in before if before[k] != after[k]},
        },
    )
    db.refresh(merchant)
    return credit_state(db, merchant)
