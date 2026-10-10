"""Staff emails for merchant risk: churn (orders stopped) and credit hold.

Email-first (PorterChain's real contact channel); the worker injects the
sender, so this module never imports the notification engine. Goes to the account owner,
falling back to active super admins. One email per merchant per kind per ISO
week (``merchant_alerts`` unique key), so a sweep can run every few minutes.
Content is internal ops data about a business account (no consignee PII).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

def _recipients(db: Session, owner_id: str | None) -> list[str]:
    from porterchain_api.merchant_engine.account_ops.lookups import (
        active_admin,
        first_super_admin_emails,
    )

    if owner_id:
        user = active_admin(db, owner_id)
        if user is not None and user.email:
            return [user.email]
    return first_super_admin_emails(db)


def _record(db: Session, merchant_id: str, kind: str, fingerprint: str, recipient: str,
            payload: dict[str, Any]) -> bool:
    """Claim the (merchant, kind, week) slot. False when already sent."""
    from porterchain_api.merchant_models import MerchantAlert

    try:
        with db.begin_nested():
            db.add(MerchantAlert(merchant_id=merchant_id, kind=kind, fingerprint=fingerprint,
                                 recipient=recipient, payload=payload))
            db.flush()
        return True
    except IntegrityError:
        return False


Sender = Callable[[str, str, dict[str, Any]], bool]


def sweep(
    db: Session,
    settings: Any,
    *,
    now: datetime | None = None,
    send: bool = True,
    sender: Sender | None = None,
) -> dict[str, int]:
    """Apply/lift auto credit holds, then email churn and new-hold alerts.

    ``sender(template, recipient, context) -> bool`` is injected by the worker
    (notification engine email); without one, nothing is emailed.
    """
    send = send and sender is not None
    from porterchain_api.merchant_engine.account_ops.credit import (
        credit_state,
        sync_auto_hold,
    )
    from porterchain_api.merchant_engine.account_ops.health import (
        collect_facts,
        evaluate,
    )
    from porterchain_api.merchant_models import Merchant

    now = now or datetime.now(UTC)
    week = now.strftime("%G-W%V")
    base = (getattr(settings, "admin_portal_url", None) or "http://localhost:3002").rstrip("/")
    merchants = db.query(Merchant).filter(Merchant.status == "ACTIVE").all()
    facts = collect_facts(db, merchants, now=now)
    out = {"holds_applied": 0, "holds_lifted": 0, "churn_emails": 0, "hold_emails": 0}
    for m in merchants:
        change = sync_auto_hold(db, m, now=now)
        if change == "applied":
            out["holds_applied"] += 1
        elif change == "lifted":
            out["holds_lifted"] += 1
        url = f"{base}/merchants/{m.id}"
        h = evaluate(m, facts[m.id], now=now)
        for rcpt in _recipients(db, m.owner_admin_id)[:1] if send else []:
            if "churn_risk" in h["signals"] and _record(db, m.id, "churn", week, rcpt, {"score": h["score"]}):
                ctx = {
                    "company_name": m.company_name,
                    "days_since": h["days_since_last_order"],
                    "usual_gap": f"{h['usual_gap_days']:g}" if h["usual_gap_days"] else "n/a",
                    "last_4w": h["trend"]["last_4w"],
                    "prior_4w": h["trend"]["prior_4w"],
                    "next_action": h["next_action"],
                    "merchant_url": url,
                }
                if sender and sender("merchant_churn_alert", rcpt, ctx):
                    out["churn_emails"] += 1
            if m.credit_hold_mode == "auto" and change == "applied":
                stamp = (m.credit_hold_at or now).strftime("%Y-%m-%d")
                if _record(db, m.id, "credit_hold", stamp, rcpt, {}):
                    st = credit_state(db, m, now=now)
                    ctx = {
                        "company_name": m.company_name,
                        "reason": m.credit_hold_reason or "overdue invoice",
                        "overdue": f"${st['overdue_cents'] / 100:,.2f}",
                        "merchant_url": url,
                    }
                    if sender and sender("merchant_credit_hold", rcpt, ctx):
                        out["hold_emails"] += 1
    db.commit()
    return out
