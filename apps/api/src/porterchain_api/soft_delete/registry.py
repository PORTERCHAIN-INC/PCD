"""Soft-delete registry: what admins can delete, guards (with plain reasons), cascades, purges.

Rules
- Delete is soft: the row and its cascade children get ``deleted_at`` and one batch id.
- Restore brings back the whole batch.
- Purge (super_admin, typed confirm) hard-deletes, or anonymises where the law says keep.
- Finance and audit tables are not in the registry, so they can never be deleted here.
- Every action writes ``admin_audit_logs`` (mirrored into the forensic hash chain) plus an
  explicit forensic event for purges.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import (
    Claim,
    Driver,
    PricingTariff,
    PricingZone,
    Promotion,
    SupportTicket,
    Vehicle,
)
from porterchain_api.billing_engine.models import InvoiceLine
from porterchain_api.booking_draft_models import BookingDraft
from porterchain_api.booking_models import (
    Customer,
    CustomerAddress,
    CustomerNote,
    Invoice,
    Order,
    Package,
    Payment,
)
from porterchain_api.crm_models import CrmCompany, CrmContact, CrmDeal, CrmLead, CrmQuotation
from porterchain_api.dispatch_engine.models import DispatchPlan, DispatchRoute
from porterchain_api.driver_models import DriverShift
from porterchain_api.merchant_models import (
    Merchant,
    MerchantApiKey,
    MerchantBookingTemplate,
    MerchantRecipient,
    MerchantWebhook,
    StandingOrder,
)
from porterchain_api.platform.soft_delete import including_deleted
from porterchain_api.website_content_models import BlogPost

RETENTION_KEY = "deleted_items"
DEFAULT_RETENTION_DAYS = 30

ON_ROAD = {"DRIVER_ASSIGNED", "DRIVER_ACCEPTED", "DRIVER_EN_ROUTE", "AT_PICKUP", "PICKED_UP", "IN_TRANSIT",
           "AT_DESTINATION"}
DELIVERED = {"DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED"}
LIVE_ROUTE = {"committed", "accepted", "in_progress", "active", "dispatched"}

# Tables that must never be deletable from the admin (CRA 6-year retention, PIPEDA trail).
NEVER_DELETE = frozenset({
    "invoices", "invoice_lines", "credit_notes", "payments", "billing_ledger_entries", "driver_payouts",
    "driver_payout_runs", "stripe_payouts", "interac_transfers", "crm_invoices", "customer_credits",
    "driver_wallet_transactions", "admin_audit_logs", "merchant_audit_logs", "access_audit_logs",
    "booking_draft_audits", "forensic_audit_chain", "forensic_checkpoints", "domain_events",
    "privacy_deletion_jobs", "invoice_number_sequences",
})


class Blocked(Exception):
    """A guard said no. ``reason`` is shown to the admin as-is."""

    def __init__(self, reason: str, code: str = "blocked") -> None:
        super().__init__(reason)
        self.reason = reason
        self.code = code


Guard = Callable[[Session, Any], str | None]


@dataclass(frozen=True)
class Entity:
    key: str
    model: type
    label: Callable[[Any], str]
    title: str
    guard_delete: Guard | None = None
    guard_purge: Guard | None = None
    children: Callable[[Session, Any], list[Any]] | None = None
    parent: Callable[[Session, Any], tuple[str, Any] | None] | None = None
    purge: Callable[[Session, Any, AdminContext], dict[str, Any]] | None = None
    side_effects: Callable[[Session, Any], dict[str, Any]] | None = None
    restore_side_effects: Callable[[Session, dict[str, Any]], None] | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)


# ── helpers ─────────────────────────────────────────────────────────────────────


def _first(*vals: Any) -> str:
    for v in vals:
        if v:
            return str(v)
    return ""


def _rows(db: Session, model: type, *where: Any) -> list[Any]:
    return list(db.scalars(select(model).where(*where)))


def _exists(db: Session, model: type, *where: Any) -> bool:
    with including_deleted(db):
        return db.scalar(select(model.id).where(*where).limit(1)) is not None


def _count(db: Session, model: type, *where: Any) -> int:
    return len(_rows(db, model, *where))


def _get_any(db: Session, model: type, row_id: str) -> Any:
    with including_deleted(db):
        return db.scalar(select(model).where(model.id == row_id).execution_options(include_deleted=True))


def _on_shift(db: Session, driver_id: str | None) -> bool:
    if not driver_id:
        return False
    return db.scalar(select(DriverShift.id).where(
        DriverShift.driver_id == driver_id, DriverShift.ended_at.is_(None),
        DriverShift.status.in_(("active", "on_break", "online"))).limit(1)) is not None


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


# ── guards ──────────────────────────────────────────────────────────────────────


def _order_delete(db: Session, o: Order) -> str | None:
    if o.state in ON_ROAD:
        return f"Order {o.order_number} is on the road ({o.state.replace('_', ' ').lower()}). Cancel or finish it first."
    return None


def _order_finance(db: Session, o: Order) -> str | None:
    if o.state in DELIVERED:
        return f"Order {o.order_number} was delivered with proof of delivery. It stays archived for records."
    if _exists(db, Invoice, Invoice.order_id == o.id) or _exists(db, InvoiceLine, InvoiceLine.order_id == o.id):
        return f"Order {o.order_number} is on an invoice. Tax law keeps it 6 years, so it stays archived."
    if _exists(db, Payment, Payment.order_id == o.id):
        return f"Order {o.order_number} has a payment. Tax law keeps it 6 years, so it stays archived."
    return None


def _merchant_delete(db: Session, m: Merchant) -> str | None:
    n = _count(db, Order, Order.merchant_id == m.id, Order.state.in_(ON_ROAD))
    if n:
        return f"{m.company_name} has {_plural(n, 'order')} on the road. Finish or cancel them first."
    return None


def _merchant_purge(db: Session, m: Merchant) -> str | None:
    if _exists(db, Invoice, Invoice.merchant_id == m.id):
        return f"{m.company_name} has invoices. Tax law keeps them 6 years, so the merchant stays archived."
    with including_deleted(db):
        orders = _rows(db, Order, Order.merchant_id == m.id)
    for o in orders:
        why = _order_finance(db, o)
        if why:
            return f"{m.company_name} has billed or delivered orders. It stays archived. ({why})"
    return None


def _customer_delete(db: Session, c: Customer) -> str | None:
    n = _count(db, Order, Order.customer_id == c.id, Order.state.in_(ON_ROAD))
    if n:
        return f"This customer has {_plural(n, 'delivery')} on the road. Wait until they are delivered."
    if c.privacy_status == "deletion_hold":
        return "This customer has an open privacy request. Handle it in Privacy requests."
    return None


def _driver_delete(db: Session, d: Driver) -> str | None:
    if _on_shift(db, d.id):
        return f"{d.full_name} is on shift right now. End the shift first."
    n = _count(db, Order, Order.assigned_driver_id == d.id, Order.state.in_(ON_ROAD))
    if n:
        return f"{d.full_name} has {_plural(n, 'order')} on the road. Reassign or finish them first."
    if _count(db, DispatchRoute, DispatchRoute.driver_id == d.id, DispatchRoute.status.in_(LIVE_ROUTE)):
        return f"{d.full_name} is assigned to a live route. Reassign the route first."
    return None


def _route_delete(db: Session, r: DispatchRoute) -> str | None:
    if r.status in LIVE_ROUTE and r.driver_id and _on_shift(db, r.driver_id):
        return "A driver is on the road with this route. Wait until the route is finished."
    return None


def _plan_delete(db: Session, p: DispatchPlan) -> str | None:
    for r in _rows(db, DispatchRoute, DispatchRoute.plan_id == p.id):
        why = _route_delete(db, r)
        if why:
            return f"This plan has a live route. {why}"
    return None


def _draft_purge(db: Session, d: BookingDraft) -> str | None:
    if d.order_id:
        return "This draft became an order. It stays archived with the order."
    return None


# ── cascades ────────────────────────────────────────────────────────────────────


def _merchant_children(db: Session, m: Merchant) -> list[Any]:
    out: list[Any] = []
    out += _rows(db, Order, Order.merchant_id == m.id, Order.state.notin_(ON_ROAD))
    for model in (StandingOrder, MerchantBookingTemplate, MerchantRecipient, Promotion,
                  PricingTariff):
        out += _rows(db, model, model.merchant_id == m.id)
    out += [p for o in out if isinstance(o, Order) for p in _rows(db, Package, Package.order_id == o.id)]
    return out


def _merchant_side_effects(db: Session, m: Merchant) -> dict[str, Any]:
    keys = _rows(db, MerchantApiKey, MerchantApiKey.merchant_id == m.id, MerchantApiKey.is_active.is_(True))
    hooks = _rows(db, MerchantWebhook, MerchantWebhook.merchant_id == m.id, MerchantWebhook.is_active.is_(True))
    for r in (*keys, *hooks):
        r.is_active = False
    return {"api_keys_paused": [k.id for k in keys], "webhooks_paused": [h.id for h in hooks]}


def _merchant_restore_side_effects(db: Session, fx: dict[str, Any]) -> None:
    for model, ids in ((MerchantApiKey, fx.get("api_keys_paused")), (MerchantWebhook, fx.get("webhooks_paused"))):
        for row in _rows(db, model, model.id.in_(ids or [])):
            row.is_active = True


def _parent_merchant(db: Session, row: Any) -> tuple[str, Any] | None:
    mid = getattr(row, "merchant_id", None)
    m = _get_any(db, Merchant, mid) if mid else None
    return ("merchant", m) if m is not None else None


def _parent_customer(db: Session, row: Any) -> tuple[str, Any] | None:
    cid = getattr(row, "customer_id", None)
    c = _get_any(db, Customer, cid) if cid else None
    return ("customer", c) if c is not None else None


def _order_parent(db: Session, o: Order) -> tuple[str, Any] | None:
    return _parent_merchant(db, o) or _parent_customer(db, o)


# ── purges ──────────────────────────────────────────────────────────────────────


def _hard_delete(db: Session, root: Any, children: list[Any], ctx: AdminContext) -> dict[str, Any]:
    nested = db.begin_nested()
    try:
        for c in reversed(children):
            db.delete(c)
        db.delete(root)
        db.flush()
    except IntegrityError as exc:
        nested.rollback()
        table = getattr(getattr(exc.orig, "diag", None), "table_name", None) or "other records"
        raise Blocked(f"Other records ({table}) still point to it, so it stays archived.", "linked_records") from exc
    nested.commit()
    return {"mode": "hard_delete", "rows": len(children) + 1}


def _purge_customer(db: Session, c: Customer, ctx: AdminContext) -> dict[str, Any]:
    """PIPEDA erasure: anonymise personal data in place, keep orders/invoices/payments for tax."""
    from porterchain_api.customer_fast import privacy

    reviewer = ctx.user.email or ctx.user.id or "admin"
    job = privacy.open_job(db, c, reference=f"admin-purge-{c.id[:8]}", source="admin_deleted_items")
    db.flush()
    try:
        result = privacy.approve_and_execute(db, job.id, reviewer=reviewer, note="Permanent delete from Deleted items")
    except ValueError as exc:
        raise Blocked(f"Privacy erasure was refused: {exc}.", "privacy_blocked") from exc
    return {"mode": "anonymized", "privacy_job_id": job.id, "result": result.get("result", result)}


def _purge_driver(db: Session, d: Driver, ctx: AdminContext) -> dict[str, Any]:
    try:
        return _hard_delete(db, d, [], ctx)
    except Blocked:
        short = d.id[:8]
        d.full_name = "Erased driver"
        d.email = f"erased+{short}@invalid.porterchain.local"
        d.phone = None
        return {"mode": "anonymized", "reason": "payouts and shifts are kept for tax records"}


# ── registry ────────────────────────────────────────────────────────────────────


def _e(key: str, model: type, title: str, label: Callable[[Any], str], **kw: Any) -> Entity:
    return Entity(key=key, model=model, title=title, label=label, **kw)


REGISTRY: dict[str, Entity] = {e.key: e for e in (
    _e("booking_draft", BookingDraft, "Booking draft", lambda r: _first(getattr(r, "reference", None), f"Draft {r.id[:8]}"),
       guard_purge=_draft_purge, parent=_parent_customer),
    _e("lead", CrmLead, "Lead", lambda r: _first(r.company_name, r.email, f"Lead {r.id[:8]}")),
    _e("order", Order, "Order", lambda r: r.order_number, guard_delete=_order_delete, guard_purge=_order_finance,
       children=lambda db, o: _rows(db, Package, Package.order_id == o.id), parent=_order_parent),
    _e("parcel", Package, "Parcel", lambda r: r.tracking_suffix,
       guard_delete=lambda db, p: _order_delete(db, p.order) if p.order else None,
       guard_purge=lambda db, p: _order_finance(db, p.order) if p.order else None,
       parent=lambda db, p: ("order", _get_any(db, Order, p.order_id))),
    _e("merchant", Merchant, "Merchant", lambda r: r.company_name, guard_delete=_merchant_delete,
       guard_purge=_merchant_purge, children=_merchant_children, side_effects=_merchant_side_effects,
       restore_side_effects=_merchant_restore_side_effects),
    _e("customer", Customer, "Customer", lambda r: _first(r.full_name, r.email), guard_delete=_customer_delete,
       children=lambda db, c: _rows(db, CustomerAddress, CustomerAddress.customer_id == c.id)
       + _rows(db, CustomerNote, CustomerNote.customer_id == c.id),
       purge=_purge_customer),
    _e("driver", Driver, "Driver", lambda r: _first(r.full_name, r.email), guard_delete=_driver_delete,
       purge=_purge_driver),
    _e("vehicle", Vehicle, "Vehicle", lambda r: _first(getattr(r, "plate_number", None), getattr(r, "make", None), f"Vehicle {r.id[:8]}"),
       guard_delete=lambda db, v: "This vehicle is out on a shift right now." if _on_shift(db, v.driver_id) else None),
    _e("route", DispatchRoute, "Route", lambda r: f"Route {r.vehicle_id} · {len(r.stops or [])} stops",
       guard_delete=_route_delete, guard_purge=_route_delete),
    _e("dispatch_plan", DispatchPlan, "Dispatch plan", lambda r: _first(getattr(r, "name", None), f"Plan {r.id[:8]}"),
       guard_delete=_plan_delete, guard_purge=_plan_delete,
       children=lambda db, p: _rows(db, DispatchRoute, DispatchRoute.plan_id == p.id)),
    _e("claim", Claim, "Claim", lambda r: _first(getattr(r, "claim_number", None), f"Claim {r.id[:8]}")),
    _e("support_ticket", SupportTicket, "Support ticket", lambda r: _first(r.subject, f"Ticket {r.id[:8]}")),
    _e("crm_company", CrmCompany, "Company", lambda r: _first(getattr(r, "name", None), r.email, r.id[:8]),
       children=lambda db, c: _rows(db, CrmContact, CrmContact.company_id == c.id)),
    _e("crm_contact", CrmContact, "Contact", lambda r: _first(getattr(r, "full_name", None), r.email, r.id[:8])),
    _e("crm_deal", CrmDeal, "Deal", lambda r: _first(r.name, r.id[:8]),
       children=lambda db, d: _rows(db, CrmQuotation, CrmQuotation.deal_id == d.id)),
    _e("crm_quotation", CrmQuotation, "Quotation", lambda r: _first(getattr(r, "number", None), r.id[:8])),
    _e("promotion", Promotion, "Promotion", lambda r: r.code),
    _e("pricing_zone", PricingZone, "Pricing zone", lambda r: _first(r.name, r.code)),
    _e("pricing_tariff", PricingTariff, "Pricing tariff", lambda r: r.name),
    _e("standing_order", StandingOrder, "Standing order", lambda r: _first(getattr(r, "name", None), f"Weekly {r.id[:8]}"),
       parent=_parent_merchant),
    _e("booking_template", MerchantBookingTemplate, "Booking template", lambda r: r.name, parent=_parent_merchant),
    _e("recipient", MerchantRecipient, "Recipient", lambda r: _first(r.name, r.email), parent=_parent_merchant),
    _e("blog_post", BlogPost, "Blog post", lambda r: r.title),
)}

TABLE_TO_KEY = {e.model.__tablename__: k for k, e in REGISTRY.items()}
assert not (set(TABLE_TO_KEY) & NEVER_DELETE), "finance/audit tables must never be deletable"


