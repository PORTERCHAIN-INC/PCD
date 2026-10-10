"""Merchant health v2: a 0-100 score with the reasons that produced it, plus
churn / expansion signals, the "needs action" flags and one next best action.

Pure rules over data already in Postgres, computed in batch for the board.
No model, no paid API. Each reason carries its points so the score is auditable.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.merchant_models import Merchant

WEEKS = 8
DELIVERED_STATES = ("DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED")
SEGMENTS: dict[str, str] = {
    "pharmacy_lab": "Pharmacy & lab",
    "shopify": "Shopify stores",
    "trades": "Construction & trades",
    "warehouse_3pl": "Warehouse & 3PL",
    "trader": "Traders & wholesale",
    "food": "Food & beverage",
    "other": "Other",
}
_SEGMENT_WORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("pharmacy_lab", ("pharma", "medical", "lab", "clinic", "health", "dental")),
    ("trades", ("construct", "plumb", "electric", "hvac", "build", "industrial", "hardware", "trade")),
    ("warehouse_3pl", ("warehouse", "3pl", "fulfil", "logistic", "distribution")),
    ("trader", ("wholesale", "trader", "trading", "import", "export", "distributor")),
    ("food", ("food", "coffee", "bever", "bakery", "restaurant", "grocery")),
)


@dataclass
class Facts:
    weekly: list[int] = field(default_factory=lambda: [0] * WEEKS)  # oldest → newest
    last_order_at: datetime | None = None
    order_dates: list[datetime] = field(default_factory=list)
    sla_total: int = 0
    sla_on_time: int = 0
    failed_30d: int = 0
    open_exceptions: int = 0
    open_claims: int = 0
    open_tickets: int = 0
    outstanding_cents: int = 0
    overdue_cents: int = 0
    dlq_open: int = 0
    webhook_failures_24h: int = 0
    shop_connected: bool = False
    shop_reauth: bool = False
    carrier_missing: bool = False
    quotes_7d: int = 0
    active_contract: bool = False


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def segment_of(merchant: Merchant, *, shop_connected: bool = False) -> str:
    tags = [str(t) for t in (merchant.segment_tags or []) if t]
    for tag in tags:
        if tag in SEGMENTS:
            return tag
    from porterchain_api.merchant_engine.organization_sync import industry_of

    text = (industry_of(merchant) or "").lower()
    for seg, words in _SEGMENT_WORDS:
        if any(w in text for w in words):
            return seg
    if shop_connected:
        return "shopify"
    return "other"


def collect_facts(db: Session, merchants: list[Merchant], *, now: datetime | None = None) -> dict[str, Facts]:
    """All inputs for every merchant in a fixed number of queries."""
    from porterchain_api.admin_models import Claim, SupportTicket
    from porterchain_api.booking_models import Order, OrderEvent, OrderException
    from porterchain_api.crm_models import CrmCompany, CrmContract
    from porterchain_api.merchant_models import (
        MerchantWebhookDelivery,
        ShopifyIngressDlq,
        ShopifyRateQuote,
        ShopifyShop,
    )

    now = now or datetime.now(UTC)
    ids = [m.id for m in merchants]
    facts: dict[str, Facts] = {mid: Facts() for mid in ids}
    if not ids:
        return facts
    start = now - timedelta(weeks=WEEKS)
    window_90 = now - timedelta(days=90)

    rows = (
        db.query(Order.id, Order.merchant_id, Order.created_at, Order.state, Order.sla_deadline_at)
        .filter(Order.merchant_id.in_(ids), Order.is_sandbox.is_(False), Order.created_at >= window_90)
        .all()
    )
    sla_orders: dict[str, tuple[str, datetime]] = {}
    for oid, mid, created, state, deadline in rows:
        f = facts[mid]
        created = _aware(created)
        if created is None:
            continue
        f.order_dates.append(created)
        if created >= start:
            idx = min(WEEKS - 1, int((created - start).total_seconds() // (7 * 86400)))
            f.weekly[idx] += 1
        if state == "FAILED" and created >= now - timedelta(days=30):
            f.failed_30d += 1
        if deadline is not None and created >= now - timedelta(days=30):
            sla_orders[oid] = (mid, _aware(deadline))
    last = (
        db.query(Order.merchant_id, func.max(Order.created_at))
        .filter(Order.merchant_id.in_(ids), Order.is_sandbox.is_(False))
        .group_by(Order.merchant_id)
        .all()
    )
    for mid, at in last:
        facts[mid].last_order_at = _aware(at)

    if sla_orders:
        delivered = (
            db.query(OrderEvent.order_id, func.min(OrderEvent.occurred_at))
            .filter(OrderEvent.order_id.in_(list(sla_orders)), OrderEvent.to_state.in_(DELIVERED_STATES))
            .group_by(OrderEvent.order_id)
            .all()
        )
        done = {oid: _aware(at) for oid, at in delivered}
        for oid, (mid, deadline) in sla_orders.items():
            at = done.get(oid)
            if at is None:
                if deadline and deadline < now:
                    facts[mid].sla_total += 1  # past deadline, not delivered → late
                continue
            facts[mid].sla_total += 1
            if deadline is None or at <= deadline:
                facts[mid].sla_on_time += 1

    for mid, n in (
        db.query(Order.merchant_id, func.count(OrderException.id))
        .join(Order, Order.id == OrderException.order_id)
        .filter(Order.merchant_id.in_(ids), OrderException.status == "open")
        .group_by(Order.merchant_id)
        .all()
    ):
        facts[mid].open_exceptions = int(n)
    for mid, n in (
        db.query(Claim.merchant_id, func.count(Claim.id))
        .filter(Claim.merchant_id.in_(ids), Claim.status.notin_(("resolved", "closed", "rejected", "denied")))
        .group_by(Claim.merchant_id)
        .all()
    ):
        facts[mid].open_claims = int(n)
    for mid, n in (
        db.query(SupportTicket.merchant_id, func.count(SupportTicket.id))
        .filter(SupportTicket.merchant_id.in_(ids), SupportTicket.status.notin_(("resolved", "closed")))
        .group_by(SupportTicket.merchant_id)
        .all()
    ):
        facts[mid].open_tickets = int(n)

    from porterchain_api.merchant_engine.billing_views import ar_index

    for mid, ar in ar_index(db, ids).items():
        if mid in facts:
            facts[mid].outstanding_cents = ar.outstanding_cents
            facts[mid].overdue_cents = ar.overdue_cents

    for mid, n in (
        db.query(ShopifyIngressDlq.merchant_id, func.count(ShopifyIngressDlq.id))
        .filter(ShopifyIngressDlq.merchant_id.in_(ids), ShopifyIngressDlq.status == "open")
        .group_by(ShopifyIngressDlq.merchant_id)
        .all()
    ):
        facts[mid].dlq_open = int(n)
    for mid, n in (
        db.query(MerchantWebhookDelivery.merchant_id, func.count(MerchantWebhookDelivery.id))
        .filter(
            MerchantWebhookDelivery.merchant_id.in_(ids),
            MerchantWebhookDelivery.success.is_(False),
            MerchantWebhookDelivery.created_at >= now - timedelta(hours=24),
        )
        .group_by(MerchantWebhookDelivery.merchant_id)
        .all()
    ):
        facts[mid].webhook_failures_24h = int(n)
    for shop in db.query(ShopifyShop).filter(ShopifyShop.merchant_id.in_(ids)).all():
        if shop.uninstalled_at is not None:
            continue
        f = facts[shop.merchant_id]
        f.shop_connected = True
        if shop.token_status == "token_reauth_required":
            f.shop_reauth = True
        if not shop.carrier_service_gid:
            f.carrier_missing = True
    for mid, n in (
        db.query(ShopifyRateQuote.merchant_id, func.count(ShopifyRateQuote.id))
        .filter(ShopifyRateQuote.merchant_id.in_(ids), ShopifyRateQuote.created_at >= now - timedelta(days=7))
        .group_by(ShopifyRateQuote.merchant_id)
        .all()
    ):
        facts[mid].quotes_7d = int(n)

    companies = db.query(CrmCompany.id, CrmCompany.merchant_id).filter(CrmCompany.merchant_id.in_(ids)).all()
    by_company = {cid: mid for cid, mid in companies}
    if by_company:
        for (cid,) in (
            db.query(CrmContract.company_id)
            .filter(CrmContract.company_id.in_(list(by_company)), CrmContract.status == "active")
            .distinct()
            .all()
        ):
            facts[by_company[cid]].active_contract = True
    return facts


def _median_gap_days(dates: list[datetime]) -> float | None:
    days = sorted({d.date() for d in dates})
    if len(days) < 3:
        return None
    gaps = [(b - a).days for a, b in zip(days, days[1:])]
    return float(statistics.median(gaps)) if gaps else None


def _pct(new: int, old: int) -> int | None:
    if old <= 0:
        return None
    return int(round((new - old) * 100 / old))


def evaluate(merchant: Merchant, f: Facts, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    reasons: list[dict[str, Any]] = []

    def add(points: int, label: str) -> None:
        if points:
            reasons.append({"points": points, "label": label})

    status = merchant.status
    if status == "ACTIVE":
        add(10, "Active account")
    elif status == "SUSPENDED":
        add(-30, "Suspended")
    elif status == "CLOSED":
        add(-50, "Closed")

    recent = sum(f.weekly[-4:])
    prior = sum(f.weekly[:4])
    change = _pct(recent, prior)
    add(min(15, recent), f"{recent} orders in the last 4 weeks")
    if change is not None:
        if change >= 20:
            add(10, f"Volume up {change}% vs prior 4 weeks")
        elif change <= -40:
            add(-20, f"Volume down {abs(change)}% vs prior 4 weeks")
        elif change <= -15:
            add(-10, f"Volume down {abs(change)}% vs prior 4 weeks")

    gap = _median_gap_days(f.order_dates)
    days_since = (now - f.last_order_at).days if f.last_order_at else None
    if days_since is None:
        if status == "ACTIVE":
            add(-15, "No orders yet")
    elif gap is not None and days_since > max(2 * gap, 3):
        add(-20, f"No orders for {days_since} days (usually every {gap:g})")

    on_time = int(round(f.sla_on_time * 100 / f.sla_total)) if f.sla_total else None
    if on_time is not None and f.sla_total >= 3:
        if on_time < 90:
            add(-10, f"On-time {on_time}% (30 days)")
        elif on_time >= 97:
            add(5, f"On-time {on_time}% (30 days)")
    if f.failed_30d:
        add(-min(15, 5 * f.failed_30d), f"{f.failed_30d} failed deliveries (30 days)")
    if f.open_exceptions:
        add(-min(15, 5 * f.open_exceptions), f"{f.open_exceptions} open delivery exceptions")
    if f.open_claims:
        add(-min(10, 5 * f.open_claims), f"{f.open_claims} open claims")

    if f.overdue_cents > 0:
        add(-20, f"Overdue ${f.overdue_cents / 100:,.2f}")
    if merchant.credit_hold_mode in ("manual", "auto"):
        add(-10, "On credit hold")
    if f.dlq_open:
        add(-10, f"{f.dlq_open} Shopify orders failed to import")
    if f.shop_reauth:
        add(-10, "Shopify needs re-authorization")
    if f.shop_connected and f.carrier_missing:
        add(-5, "Shopify checkout rates not registered")
    if f.webhook_failures_24h > 3:
        add(-5, f"{f.webhook_failures_24h} webhook failures (24h)")
    if f.active_contract:
        add(5, "Active contract")

    score = max(0, min(100, 50 + sum(r["points"] for r in reasons)))
    band = "healthy" if score >= 70 else "watch" if score >= 40 else "at_risk"

    signals: list[str] = []
    churn = status == "ACTIVE" and (
        (gap is not None and days_since is not None and days_since > max(2 * gap, 3))
        or (prior >= 4 and change is not None and change <= -40)
    )
    if churn:
        signals.append("churn_risk")
    expansion = status == "ACTIVE" and (
        (change is not None and change >= 30 and recent >= 4)
        or (f.quotes_7d >= 10 and f.quotes_7d > 3 * max(1, f.weekly[-1]))
    )
    if expansion:
        signals.append("expansion")

    integration_broken = bool(f.dlq_open or f.shop_reauth or (f.shop_connected and f.carrier_missing)
                              or f.webhook_failures_24h > 3)
    created = _aware(merchant.created_at)
    onboarding_stuck = status in ("PENDING", "ONBOARDING") and bool(created and now - created > timedelta(days=7))
    needs: list[str] = []
    if merchant.credit_hold_mode in ("manual", "auto"):
        needs.append("credit_hold")
    if f.overdue_cents > 0:
        needs.append("overdue")
    if integration_broken:
        needs.append("integration")
    if churn:
        needs.append("churn_risk")
    if onboarding_stuck:
        needs.append("onboarding_stuck")
    if f.open_exceptions or f.open_claims:
        needs.append("exceptions")
    if score < 40 and status == "ACTIVE":
        needs.append("at_risk")

    return {
        "score": score,
        "band": band,
        "reasons": sorted(reasons, key=lambda r: abs(r["points"]), reverse=True),
        "signals": signals,
        "needs_action": needs,
        "next_action": next_action(needs, signals, f),
        "trend": {"weekly": list(f.weekly), "change_pct": change, "last_4w": recent, "prior_4w": prior},
        "days_since_last_order": days_since,
        "usual_gap_days": gap,
        "on_time_pct": on_time,
        "connections": "red" if integration_broken else ("green" if f.shop_connected else "none"),
        "open_tickets": f.open_tickets,
        "open_claims": f.open_claims,
        "open_exceptions": f.open_exceptions,
        "outstanding_cents": f.outstanding_cents,
        "overdue_cents": f.overdue_cents,
    }


_ACTIONS: dict[str, str] = {
    "credit_hold": "Collect the overdue Interac e-Transfer, then release the hold",
    "overdue": "Send a payment reminder for the overdue invoice",
    "integration": "Fix their store or API connection — orders may be missing",
    "churn_risk": "Call the account: orders have stopped",
    "onboarding_stuck": "Finish onboarding: invite the owner and set pricing",
    "exceptions": "Resolve the open exceptions and claims",
    "at_risk": "Review the account with the owner this week",
}


def next_action(needs: list[str], signals: list[str], f: Facts) -> str:
    for key in ("credit_hold", "integration", "overdue", "churn_risk", "exceptions", "onboarding_stuck", "at_risk"):
        if key in needs:
            return _ACTIONS[key]
    if "expansion" in signals:
        return "Volume is growing: offer a contract or volume rate"
    return "No action needed"
