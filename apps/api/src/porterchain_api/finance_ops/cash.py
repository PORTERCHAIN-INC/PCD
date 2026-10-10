"""The Cash page: who owes what, how late, what is waiting to be approved.

One row per merchant (AR by age), the open Interac queue, queued reminder drafts and the
credit-hold view. Credit hold *logic* lives in the merchant-admin module
(``merchant_engine.account_ops.credit``); this page only reads it.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.billing_engine.ar import AGING_LADDER, AGING_OLDEST
from porterchain_api.billing_engine.models import FinanceReminderDraft, InteracTransfer

BUCKETS = [label for _, label in AGING_LADDER] + [AGING_OLDEST]


def ar_by_merchant(db: Session) -> list[dict[str, Any]]:
    from porterchain_api.admin_engine.finance_service import AdminFinanceService

    rows = AdminFinanceService().collections(db)
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        mid = r.get("merchant_id")
        if not mid:
            continue  # retail invoices are paid by Stripe at checkout; not chased here
        m = out.setdefault(
            mid,
            {
                "merchant_id": mid,
                "merchant_name": r.get("merchant_name") or "Merchant",
                "outstanding_cents": 0,
                "overdue_cents": 0,
                "invoice_count": 0,
                "oldest_days": 0,
                "buckets": defaultdict(int),
                "ap_contact": r.get("ap_contact"),
                "invoice_ids": [],
                "references": [],
            },
        )
        cents = int(r.get("outstanding_cents") or 0)
        days = int(r.get("days_overdue") or 0)
        m["outstanding_cents"] += cents
        if days > 0:
            m["overdue_cents"] += cents
        m["invoice_count"] += 1
        m["oldest_days"] = max(m["oldest_days"], days)
        m["buckets"][r.get("aging_bucket") or BUCKETS[0]] += cents
        m["invoice_ids"].append(r.get("invoice_id"))
        if r.get("payment_reference"):
            m["references"].append(r["payment_reference"])
    result = []
    for m in out.values():
        m["buckets"] = {b: int(m["buckets"].get(b, 0)) for b in BUCKETS}
        result.append(m)
    result.sort(key=lambda m: (-m["oldest_days"], -m["outstanding_cents"]))
    return result


def credit_holds(db: Session, merchant_ids: list[str]) -> dict[str, Any]:
    """Read-only view of credit holds from the merchant-admin module, when present."""
    try:
        from porterchain_api.merchant_engine.account_ops import credit as credit_mod  # type: ignore[attr-defined]
    except ImportError:
        credit_mod = None
    from porterchain_api.merchant_models import Merchant

    if credit_mod is None:
        return {"available": False, "source": "feat/merchant-admin (not merged)", "items": []}
    items = []
    for m in db.query(Merchant).filter(Merchant.id.in_(merchant_ids[:200])).all() if merchant_ids else []:
        try:
            state = credit_mod.credit_state(db, m)
        except Exception:  # noqa: BLE001 - a hold read must never break the Cash page
            continue
        if state.get("blocked") or state.get("reasons"):
            items.append({"merchant_id": m.id, "merchant_name": m.company_name, **state})
    return {"available": True, "source": "merchant_engine.account_ops.credit", "items": items}


def cash_board(db: Session) -> dict[str, Any]:
    merchants = ar_by_merchant(db)
    totals = {b: sum(m["buckets"][b] for m in merchants) for b in BUCKETS}
    open_q = db.query(func.count(InteracTransfer.id), func.coalesce(func.sum(InteracTransfer.amount_cents), 0)).filter(
        InteracTransfer.status.in_(("proposed", "needs_review", "suspicious"))
    )
    q_count, q_cents = open_q.one()
    drafts = db.query(func.count(FinanceReminderDraft.id)).filter(FinanceReminderDraft.status == "draft").scalar()
    from porterchain_api.platform.merchant_billing import merchant_credit_total_cents

    return {
        "owed_cents": sum(m["outstanding_cents"] for m in merchants),
        "overdue_cents": sum(m["overdue_cents"] for m in merchants),
        "merchant_count": len(merchants),
        "buckets": totals,
        "bucket_order": BUCKETS,
        "merchant_credit_cents": merchant_credit_total_cents(db),
        "interac_open_count": int(q_count or 0),
        "interac_open_cents": int(q_cents or 0),
        "draft_count": int(drafts or 0),
        "merchants": merchants,
        "credit_holds": credit_holds(db, [m["merchant_id"] for m in merchants]),
    }
