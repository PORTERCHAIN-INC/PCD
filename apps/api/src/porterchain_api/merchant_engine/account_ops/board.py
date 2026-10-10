"""Merchant board: one paged list with views (Needs action / All / segment),
account owners, segments and bulk actions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from porterchain_api.merchant_engine.account_ops.health import (
    SEGMENTS,
    collect_facts,
    evaluate,
    segment_of,
)
from porterchain_api.merchant_models import Merchant

OWNER_ROLES = ("super_admin", "admin", "sales", "sales_manager", "finance")
#: Lifecycle bulk (approve / suspend / activate) stays on the per-merchant routes so
#: each write keeps its identity side effects (after_admin_write).
BULK_ACTIONS = ("assign_owner", "set_segment", "credit_hold", "credit_release")
MAX_BULK = 200
NEEDS_LABELS = {
    "credit_hold": "Credit hold",
    "overdue": "Overdue invoice",
    "integration": "Connection broken",
    "churn_risk": "Orders stopped",
    "onboarding_stuck": "Onboarding stuck",
    "exceptions": "Open exceptions",
    "at_risk": "At risk",
}


def owners(db: Session, *, limit: int = 200) -> list[dict[str, Any]]:
    from porterchain_api.merchant_engine.account_ops.lookups import (
        active_admins_with_roles,
    )

    rows = active_admins_with_roles(db, OWNER_ROLES, limit=limit)
    return [{"id": u.id, "name": u.name or u.email.split("@")[0], "email": u.email, "role": u.role} for u in rows]


def _owner_names(db: Session, ids: set[str]) -> dict[str, str]:
    from porterchain_api.merchant_engine.account_ops.lookups import admin_names

    return admin_names(db, ids)


def _crm_owner_ids(db: Session, merchant_ids: list[str]) -> dict[str, str]:
    from porterchain_api.crm_models import CrmCompany

    if not merchant_ids:
        return {}
    rows = (
        db.query(CrmCompany.merchant_id, CrmCompany.owner_id)
        .filter(CrmCompany.merchant_id.in_(merchant_ids), CrmCompany.owner_id.isnot(None))
        .all()
    )
    return {mid: oid for mid, oid in rows if mid and oid}


def board(
    db: Session,
    *,
    view: str = "needs_action",
    segment: str | None = None,
    status: str | None = None,
    owner_id: str | None = None,
    search: str | None = None,
    sort: str = "priority",
    page: int = 1,
    page_size: int = 25,
) -> dict[str, Any]:
    """Score every merchant (tens to low hundreds today), then filter and page.

    Health needs cross-merchant facts, so the page is cut after scoring; the
    queries are batched (fixed count, not per merchant).
    """
    page = max(1, int(page))
    page_size = max(5, min(int(page_size), 100))
    q = db.query(Merchant)
    if status:
        q = q.filter(Merchant.status == status)
    if search:
        like = f"%{search.strip()}%"
        q = q.filter(or_(Merchant.company_name.ilike(like), Merchant.email.ilike(like),
                         Merchant.legal_name.ilike(like)))
    merchants = q.order_by(Merchant.created_at.desc()).limit(2000).all()
    now = datetime.now(UTC)
    facts = collect_facts(db, merchants, now=now)
    crm_owner = _crm_owner_ids(db, [m.id for m in merchants])

    rows: list[dict[str, Any]] = []
    for m in merchants:
        f = facts[m.id]
        h = evaluate(m, f, now=now)
        seg = segment_of(m, shop_connected=f.shop_connected)
        owner = m.owner_admin_id or crm_owner.get(m.id)
        rows.append(
            {
                "id": m.id,
                "company_name": m.company_name,
                "status": m.status,
                "segment": seg,
                "segment_label": SEGMENTS[seg],
                "owner_id": owner,
                "pricing_model": m.pricing_model,
                "payment_terms": m.payment_terms,
                "credit_hold": m.credit_hold_mode in ("manual", "auto"),
                "health": {"score": h["score"], "band": h["band"], "top_reason": h["reasons"][0]["label"]
                           if h["reasons"] else None},
                "signals": h["signals"],
                "needs_action": h["needs_action"],
                "needs_labels": [NEEDS_LABELS[n] for n in h["needs_action"]],
                "next_action": h["next_action"],
                "trend": h["trend"],
                "connections": h["connections"],
                "outstanding_cents": h["outstanding_cents"],
                "overdue_cents": h["overdue_cents"],
                "days_since_last_order": h["days_since_last_order"],
            }
        )
    names = _owner_names(db, {r["owner_id"] for r in rows if r["owner_id"]})
    for r in rows:
        r["owner_name"] = names.get(r["owner_id"] or "")

    counts = {
        "needs_action": sum(1 for r in rows if r["needs_action"]),
        "all": len(rows),
        "segments": {k: sum(1 for r in rows if r["segment"] == k) for k in SEGMENTS},
        # Numbers-first strip on the board (whole book, not the page).
        "at_risk": sum(1 for r in rows if r["health"]["band"] == "at_risk"),
        "on_hold": sum(1 for r in rows if r["credit_hold"]),
        "overdue_cents": sum(r["overdue_cents"] or 0 for r in rows),
        "outstanding_cents": sum(r["outstanding_cents"] or 0 for r in rows),
    }
    if view == "needs_action":
        rows = [r for r in rows if r["needs_action"]]
    if segment:
        rows = [r for r in rows if r["segment"] == segment]
    if owner_id:
        rows = [r for r in rows if r["owner_id"] == owner_id]

    severity = ["credit_hold", "integration", "overdue", "churn_risk", "exceptions", "onboarding_stuck", "at_risk"]

    def prio(r: dict[str, Any]) -> tuple:
        first = min((severity.index(n) for n in r["needs_action"]), default=len(severity))
        return (first, r["health"]["score"], r["company_name"].lower())

    keyers = {
        "priority": (prio, False),
        "health": (lambda r: r["health"]["score"], False),
        "volume": (lambda r: r["trend"]["last_4w"], True),
        "trend": (lambda r: r["trend"]["change_pct"] if r["trend"]["change_pct"] is not None else -999, False),
        "outstanding": (lambda r: r["outstanding_cents"], True),
        "name": (lambda r: r["company_name"].lower(), False),
    }
    key, reverse = keyers.get(sort, keyers["priority"])
    rows.sort(key=key, reverse=reverse)
    total = len(rows)
    start = (page - 1) * page_size
    return {
        "items": rows[start:start + page_size],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": max(1, -(-total // page_size)),
        "counts": counts,
        "segments": [{"value": k, "label": v} for k, v in SEGMENTS.items()],
    }


def merchant_ops(db: Session, merchant_id: str, settings: Any) -> dict[str, Any]:
    """Overview payload for one merchant: health, credit, owner, segment, connections light."""
    from porterchain_api.merchant_engine.account_ops import get_merchant
    from porterchain_api.merchant_engine.account_ops.credit import credit_state

    m = get_merchant(db, merchant_id)
    now = datetime.now(UTC)
    f = collect_facts(db, [m], now=now)[m.id]
    h = evaluate(m, f, now=now)
    owner = m.owner_admin_id or _crm_owner_ids(db, [m.id]).get(m.id)
    seg = segment_of(m, shop_connected=f.shop_connected)
    return {
        "merchant_id": m.id,
        "health": h,
        "needs_labels": [NEEDS_LABELS[n] for n in h["needs_action"]],
        "credit": credit_state(db, m, now=now),
        "owner": {"id": owner, "name": _owner_names(db, {owner} if owner else set()).get(owner or "")},
        "segment": {"value": seg, "label": SEGMENTS[seg], "tags": list(m.segment_tags or [])},
    }


def set_owner(db: Session, ctx: Any, merchant_id: str, owner_id: str | None) -> dict[str, Any]:
    from porterchain_api.crm_models import CrmCompany
    from porterchain_api.merchant_engine.account_ops import get_merchant, staff_audit
    from porterchain_api.merchant_engine.account_ops.lookups import active_admin

    m = get_merchant(db, merchant_id)
    if owner_id:
        user = active_admin(db, owner_id)
        if user is None or user.role not in OWNER_ROLES:
            raise ValueError("owner_invalid")
    old = m.owner_admin_id
    m.owner_admin_id = owner_id or None
    company = db.query(CrmCompany).filter(CrmCompany.merchant_id == merchant_id).first()
    if company is not None:
        company.owner_id = owner_id or None
    staff_audit(
        db, ctx, merchant_id, action="merchant.owner_set", resource_type="owner", resource_id=merchant_id,
        payload={"changes": {"owner_admin_id": {"old": old, "new": m.owner_admin_id}}},
    )
    return {"owner_id": m.owner_admin_id}


def set_segment(db: Session, ctx: Any, merchant_id: str, segment: str | None) -> dict[str, Any]:
    from porterchain_api.merchant_engine.account_ops import get_merchant, staff_audit

    if segment and segment not in SEGMENTS:
        raise ValueError("segment_invalid")
    m = get_merchant(db, merchant_id)
    old = list(m.segment_tags or [])
    m.segment_tags = [segment] if segment else None
    staff_audit(
        db, ctx, merchant_id, action="merchant.segment_set", resource_type="segments", resource_id=merchant_id,
        payload={"changes": {"segment": {"old": old[0] if old else None, "new": segment}}},
    )
    return {"segment": segment}


def bulk(db: Session, ctx: Any, *, action: str, merchant_ids: list[str], value: str | None,
         reason: str | None) -> dict[str, Any]:
    """Run one action over many merchants. Each merchant succeeds or fails on its own."""
    from porterchain_api.merchant_engine.account_ops import get_merchant
    from porterchain_api.merchant_engine.account_ops.credit import set_credit
    if action not in BULK_ACTIONS:
        raise ValueError("bulk_action_invalid")
    ids = list(dict.fromkeys(merchant_ids or []))
    if not ids or len(ids) > MAX_BULK:
        raise ValueError("bulk_size_invalid")
    if action in ("credit_hold", "credit_release"):
        # Money-editor role is enforced by the admin router before this runs.
        if not (reason or "").strip():
            raise ValueError("reason_required")
    ok: list[str] = []
    failed: list[dict[str, str]] = []
    for mid in ids:
        try:
            if action == "assign_owner":
                set_owner(db, ctx, mid, value)
            elif action == "set_segment":
                set_segment(db, ctx, mid, value)
            elif action == "credit_hold":
                set_credit(db, ctx, get_merchant(db, mid), action="hold", reason=reason)
            elif action == "credit_release":
                set_credit(db, ctx, get_merchant(db, mid), action="release", reason=reason)
            ok.append(mid)
        except (LookupError, ValueError, PermissionError, RuntimeError) as exc:
            db.rollback()
            failed.append({"id": mid, "error": str(exc) or exc.__class__.__name__})
    db.commit()
    return {"action": action, "ok": ok, "failed": failed}
