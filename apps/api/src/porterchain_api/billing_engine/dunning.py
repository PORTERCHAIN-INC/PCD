"""AR summary + dunning reminder DRAFTS. Nothing here sends mail — an admin
copies or sends each draft through the normal single-invoice reminder path."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.billing_engine.ar import merchant_ar_index
from porterchain_api.merchant_models import Merchant


def primary_billing_email(merchant: Merchant) -> str | None:
    """Primary billing contact email, else the merchant email (same rule as invoice reminders)."""
    profile = merchant.profile if isinstance(merchant.profile, dict) else {}
    contacts = list(((profile.get("settings") or {}).get("billing_contacts")) or [])
    ordered = sorted(contacts, key=lambda c: not c.get("is_primary"))
    for c in ordered:
        email = str(c.get("email") or "").strip()
        if email:
            return email
    return (merchant.email or "").strip() or None


def _tone(overdue_count: int, overdue_cents: int) -> str:
    if overdue_count >= 3 or overdue_cents >= 200_000:
        return "firm"
    if overdue_count >= 2:
        return "reminder"
    return "friendly"


def draft_for(
    merchant: Merchant, overdue_cents: int, overdue_count: int, outstanding_cents: int
) -> dict[str, Any]:
    tone = _tone(overdue_count, overdue_cents)
    opener = {
        "friendly": "Just a quick note:",
        "reminder": "A reminder that",
        "firm": "Your account needs attention:",
    }[tone]
    amount = f"${overdue_cents / 100:,.2f}"
    body = (
        f"Hi {merchant.company_name} team,\n\n"
        f"{opener} {overdue_count} PorterChain invoice(s) totalling {amount} are past due "
        f"(total balance ${outstanding_cents / 100:,.2f}).\n\n"
        "Please pay by Interac e-Transfer and put the invoice reference in the message so it "
        "matches automatically. If you've already paid, thank you, and you can ignore this note.\n\n"
        "PorterChain Billing"
    )
    return {
        "merchant_id": merchant.id,
        "to": primary_billing_email(merchant),
        "tone": tone,
        "subject": f"PorterChain: {amount} past due",
        "body": body,
    }


def ar_summary(db: Session, *, limit: int = 50) -> dict[str, Any]:
    index = merchant_ar_index(db)
    merchants = (
        {m.id: m for m in db.query(Merchant).filter(Merchant.id.in_(list(index))).all()}
        if index
        else {}
    )
    rows = sorted(
        index.values(), key=lambda a: (-a.overdue_cents, -a.outstanding_cents)
    )
    owed = sum(a.outstanding_cents for a in rows)
    overdue = sum(a.overdue_cents for a in rows)
    items, drafts = [], []
    for a in rows[:limit]:
        m = merchants.get(a.merchant_id)
        if m is None or a.outstanding_cents <= 0:
            continue
        action = (
            "send_reminder"
            if a.overdue_cents > 0
            else ("invoice_now" if a.uninvoiced_cents > 0 else "none")
        )
        items.append(
            {
                "merchant_id": a.merchant_id,
                "name": m.company_name,
                "outstanding_cents": a.outstanding_cents,
                "overdue_cents": a.overdue_cents,
                "uninvoiced_cents": a.uninvoiced_cents,
                "overdue_invoice_count": a.overdue_invoice_count,
                "action": action,
            }
        )
        if a.overdue_cents > 0:
            drafts.append(
                draft_for(
                    m, a.overdue_cents, a.overdue_invoice_count, a.outstanding_cents
                )
            )
    return {
        "owed_cents": owed,
        "overdue_cents": overdue,
        "items": items,
        "dunning_drafts": drafts,
    }
