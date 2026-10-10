"""Propose which invoice an Interac transfer pays. Proposals only — an admin approves."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from porterchain_api.billing_engine.invoice_numbering import normalize_reference

_SUFFIXES = re.compile(
    r"\b(inc|incorporated|ltd|limited|ltee|ltée|corp|corporation|co|company|llc|lp|ulc|the)\b\.?", re.I
)


def normalize_name(name: str | None) -> str:
    text = _SUFFIXES.sub(" ", (name or "").lower())
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class MatchProposal:
    invoice_id: str | None = None
    merchant_id: str | None = None
    method: str | None = None  # reference | sender_amount
    note: str = "unmatched"  # exact | partial | over | unmatched | ambiguous | merchant_only | settled
    candidates: list[str] = field(default_factory=list)


def _open_invoice_rows(db: Session, merchant_id: str | None = None):
    from porterchain_api.billing_engine.merchant_service import invoice_status, outstanding_cents
    from porterchain_api.booking_models import Invoice, Order

    q = db.query(Invoice).filter(Invoice.merchant_id.isnot(None), Invoice.customer_id.is_(None))
    if merchant_id:
        q = q.filter(Invoice.merchant_id == merchant_id)
    rows = []
    for inv in q.order_by(Invoice.created_at.asc()).all():
        order = db.get(Order, inv.order_id) if inv.order_id else None
        st = invoice_status(inv, order, None, terms=(order.payment_terms if order else None))
        if st in ("paid", "void", "cancelled"):
            continue
        out = outstanding_cents(inv, st)
        if out > 0:
            rows.append((inv, out))
    return rows


def _note_for(amount: int, outstanding: int) -> str:
    if outstanding <= 0:
        return "settled"
    if amount == outstanding:
        return "exact"
    return "partial" if amount < outstanding else "over"


def _billing_emails(merchant) -> set[str]:
    """Company email + AP contacts (profile.settings.billing_contacts)."""
    out = {str(getattr(merchant, "email", "") or "").lower()}
    profile = merchant.profile if isinstance(getattr(merchant, "profile", None), dict) else {}
    for c in ((profile.get("settings") or {}).get("billing_contacts") or []):
        if isinstance(c, dict) and c.get("email"):
            out.add(str(c["email"]).lower())
    out.discard("")
    return out


def _merchants_matching(db: Session, sender_name: str | None, sender_email: str | None) -> list[str]:
    from porterchain_api.merchant_models import Merchant

    target = normalize_name(sender_name)
    email = (sender_email or "").lower()
    ids: list[str] = []
    for m in db.query(Merchant).all():
        names = {normalize_name(getattr(m, "company_name", None)), normalize_name(getattr(m, "legal_name", None))}
        names.discard("")
        emails = _billing_emails(m)
        if (target and target in names) or (email and email in emails):
            ids.append(m.id)
    return ids


def propose_match(
    db: Session,
    *,
    amount_cents: int,
    memo: str | None,
    sender_name: str | None,
    sender_email: str | None,
) -> MatchProposal:
    from porterchain_api.booking_models import Invoice

    # 1) Reference code typed in the e-Transfer message.
    code = normalize_reference(memo)
    if code:
        inv = db.query(Invoice).filter(Invoice.payment_reference == code).first()
        if inv is not None:
            outstanding = next((o for i, o in _open_invoice_rows(db, inv.merchant_id) if i.id == inv.id), 0)
            return MatchProposal(
                invoice_id=inv.id,
                merchant_id=inv.merchant_id,
                method="reference",
                note=_note_for(amount_cents, outstanding),
            )

    # 2) Known sender + exact open amount.
    merchant_ids = _merchants_matching(db, sender_name, sender_email)
    if len(merchant_ids) == 1:
        mid = merchant_ids[0]
        open_rows = _open_invoice_rows(db, mid)
        exact = [inv for inv, out in open_rows if out == amount_cents]
        if len(exact) == 1:
            return MatchProposal(invoice_id=exact[0].id, merchant_id=mid, method="sender_amount", note="exact")
        if len(exact) > 1:
            return MatchProposal(
                merchant_id=mid, method="sender_amount", note="ambiguous", candidates=[i.id for i in exact]
            )
        return MatchProposal(
            merchant_id=mid, note="merchant_only", candidates=[inv.id for inv, _ in open_rows][:10]
        )
    return MatchProposal(note="unmatched" if not merchant_ids else "ambiguous_sender")
