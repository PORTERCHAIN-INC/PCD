"""Pricing admin (doc 72 §9): Standard rate card versions, org Custom pricing, audit.

One Standard card for every channel. Super admins edit and publish the Standard
card; admins set an org to Standard or Custom (presets, band overrides) within
the guardrails. Every change writes a pricing_audit row.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext, AdminRole
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.pricing_engine.smart_apply import three_model_preview
from porterchain_api.pricing_engine.models import (
    PricingAudit,
    PricingOrgPricing,
    PricingRateCard,
    PricingRateCardVersion,
)
from porterchain_pricing.standard_card import (
    STANDARD_CODE,
    Item,
    ManualQuoteRequired,
    OrgPricing,
    diff_lines,
    quote,
    sample_basket_preview,
    standard_v1,
)

router = APIRouter(prefix="/v1/pricing", tags=["pricing-admin"])

AdminDep = Annotated[AdminContext, Depends(get_admin_context)]
DbDep = Annotated[Session, Depends(get_db)]


def _staff(ctx: AdminContext) -> None:
    if ctx.role not in (AdminRole.SUPER_ADMIN, AdminRole.ADMIN):
        raise HTTPException(status_code=403, detail="pricing_admin_only")


def _super(ctx: AdminContext) -> None:
    if ctx.role != AdminRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="super_admin_only")


def _actor(ctx: AdminContext) -> str | None:
    return getattr(ctx.user, "id", None) or getattr(ctx.user, "porterchain_user_id", None)


def _audit(db: Session, ctx: AdminContext, entity: str, entity_id: str, action: str, diff: Any, reason: str | None = None) -> None:
    db.add(PricingAudit(entity=entity, entity_id=entity_id, action=action, diff=diff, actor_id=_actor(ctx), reason=reason))


def _standard_card(db: Session) -> PricingRateCard:
    card = db.scalar(select(PricingRateCard).where(PricingRateCard.code == STANDARD_CODE))
    if card is None:
        card = PricingRateCard(code=STANDARD_CODE, name="PorterChain Standard", kind="standard")
        db.add(card)
        db.flush()
        db.add(
            PricingRateCardVersion(
                rate_card_id=card.id, version=1, status="published", lines=standard_v1(),
                effective_from=datetime.now(UTC), published_at=datetime.now(UTC), notes="Standard v1 (doc 72)",
            )
        )
        db.flush()
    return card


def _versions(db: Session, card_id: str) -> list[PricingRateCardVersion]:
    return list(
        db.scalars(
            select(PricingRateCardVersion)
            .where(PricingRateCardVersion.rate_card_id == card_id)
            .order_by(PricingRateCardVersion.version.desc())
        )
    )


def published_lines(db: Session) -> dict[str, Any]:
    """Live Standard lines (falls back to the code default)."""
    card = _standard_card(db)
    for v in _versions(db, card.id):
        if v.status == "published":
            return v.lines
    return standard_v1()


def _ver_out(v: PricingRateCardVersion) -> dict[str, Any]:
    return {
        "id": v.id, "version": v.version, "status": v.status, "notes": v.notes,
        "effective_from": v.effective_from.isoformat() if v.effective_from else None,
        "published_at": v.published_at.isoformat() if v.published_at else None,
    }


@router.get("/rate-cards/standard")
def get_standard(ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    _staff(ctx)
    card = _standard_card(db)
    vs = _versions(db, card.id)
    live = next((v for v in vs if v.status == "published"), None)
    draft = next((v for v in vs if v.status == "draft"), None)
    db.commit()
    return {
        "code": card.code, "name": card.name,
        "published": _ver_out(live) | {"lines": live.lines} if live else None,
        "draft": _ver_out(draft) | {"lines": draft.lines} if draft else None,
        "versions": [_ver_out(v) for v in vs],
        "can_edit": ctx.role == AdminRole.SUPER_ADMIN,
    }


class DraftBody(BaseModel):
    lines: dict[str, Any] | None = None
    notes: str | None = Field(default=None, max_length=2000)


def _validate_lines(lines: dict[str, Any]) -> None:
    try:
        quote([Item(weight_kg=4, length_cm=40, width_cm=30, height_cm=20)], "Z1", lines=lines)
        sample_basket_preview(lines)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"invalid_rate_card:{exc}") from exc


@router.post("/rate-cards/standard/draft")
def save_draft(body: DraftBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    _super(ctx)
    card = _standard_card(db)
    vs = _versions(db, card.id)
    draft = next((v for v in vs if v.status == "draft"), None)
    base = body.lines or copy.deepcopy(published_lines(db))
    _validate_lines(base)
    if draft is None:
        draft = PricingRateCardVersion(rate_card_id=card.id, version=(vs[0].version + 1) if vs else 1, status="draft", lines=base)
        db.add(draft)
    else:
        draft.lines = base
    draft.notes = body.notes
    db.flush()
    _audit(db, ctx, "rate_card_version", draft.id, "draft_saved", diff_lines(published_lines(db), base))
    db.commit()
    return _ver_out(draft) | {"lines": draft.lines}


@router.post("/rate-cards/standard/preview")
def preview_lines(body: DraftBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    _staff(ctx)
    lines = body.lines or published_lines(db)
    _validate_lines(lines)
    live = published_lines(db)
    db.commit()
    return {"rows": sample_basket_preview(lines), "live_rows": sample_basket_preview(live), "diff": diff_lines(live, lines)}


class PublishBody(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


@router.post("/rate-cards/standard/publish")
def publish(body: PublishBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    _super(ctx)
    card = _standard_card(db)
    vs = _versions(db, card.id)
    draft = next((v for v in vs if v.status == "draft"), None)
    if draft is None:
        raise HTTPException(status_code=409, detail="no_draft")
    now = datetime.now(UTC)
    old = published_lines(db)
    for v in vs:
        if v.status == "published":
            v.status, v.effective_to = "retired", now
    draft.status, draft.published_at, draft.effective_from, draft.published_by = "published", now, now, _actor(ctx)
    _audit(db, ctx, "rate_card_version", draft.id, "published", diff_lines(old, draft.lines), body.reason)
    db.commit()
    return _ver_out(draft)


class RollbackBody(BaseModel):
    version: int
    reason: str = Field(min_length=3, max_length=2000)


@router.post("/rate-cards/standard/rollback")
def rollback(body: RollbackBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    """Republish an older version's lines as a new version (history is never rewritten)."""
    _super(ctx)
    card = _standard_card(db)
    vs = _versions(db, card.id)
    target = next((v for v in vs if v.version == body.version), None)
    if target is None:
        raise HTTPException(status_code=404, detail="version_not_found")
    now = datetime.now(UTC)
    old = published_lines(db)
    for v in vs:
        if v.status in ("published", "draft"):
            v.status, v.effective_to = "retired", now
    new = PricingRateCardVersion(
        rate_card_id=card.id, version=vs[0].version + 1, status="published", lines=copy.deepcopy(target.lines),
        published_at=now, effective_from=now, published_by=_actor(ctx), notes=f"Rollback to v{target.version}",
    )
    db.add(new)
    db.flush()
    _audit(db, ctx, "rate_card_version", new.id, "rollback", diff_lines(old, new.lines), body.reason)
    db.commit()
    return _ver_out(new)


class OrgPricingBody(BaseModel):
    mode: str = Field(pattern="^(standard|custom)$")
    preset_pct: float | None = Field(default=None, ge=-30, le=50)
    preset_per_stop_cents: int | None = Field(default=None, ge=-5000, le=5000)
    flat_parcel_cents: int | None = Field(default=None, ge=1, le=100000)
    band_overrides: dict[str, int] = Field(default_factory=dict)
    contract_document_id: str | None = None
    red_reason: str | None = Field(default=None, max_length=2000)
    expires_at: datetime | None = None
    reason: str | None = Field(default=None, max_length=2000)


def _org_obj(row: PricingOrgPricing | None) -> OrgPricing:
    if row is None or row.mode != "custom":
        return OrgPricing()
    return OrgPricing(
        mode="custom", preset_pct=row.preset_pct, preset_per_stop_cents=row.preset_per_stop_cents,
        flat_parcel_cents=row.flat_parcel_cents, band_overrides=dict(row.band_overrides or {}),
    )


def _org_out(org_id: str, row: PricingOrgPricing | None) -> dict[str, Any]:
    if row is None:
        return {"org_id": org_id, "mode": "standard", "preset_pct": None, "preset_per_stop_cents": None, "flat_parcel_cents": None, "band_overrides": {}}
    return {
        "org_id": org_id, "mode": row.mode, "preset_pct": row.preset_pct,
        "preset_per_stop_cents": row.preset_per_stop_cents, "flat_parcel_cents": row.flat_parcel_cents, "band_overrides": row.band_overrides or {},
        "contract_document_id": row.contract_document_id, "red_reason": row.red_reason,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
    }


@router.get("/orgs/{org_id}")
def get_org(org_id: str, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    _staff(ctx)
    row = db.get(PricingOrgPricing, org_id)
    lines = published_lines(db)
    db.commit()
    return _org_out(org_id, row) | {"preview": three_model_preview(_org_obj(row))}


def _body_org(body: OrgPricingBody) -> OrgPricing:
    if body.mode != "custom":
        return OrgPricing()
    return OrgPricing(mode="custom", preset_pct=body.preset_pct, preset_per_stop_cents=body.preset_per_stop_cents, flat_parcel_cents=body.flat_parcel_cents, band_overrides=body.band_overrides)


@router.post("/orgs/{org_id}/preview")
def preview_org(org_id: str, body: OrgPricingBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    _staff(ctx)
    lines = published_lines(db)
    db.commit()
    try:
        return {"org_id": org_id, "rows": three_model_preview(_body_org(body))}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/orgs/{org_id}")
def put_org(org_id: str, body: OrgPricingBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    _staff(ctx)
    lines = published_lines(db)
    try:
        rows = three_model_preview(_body_org(body))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if body.mode == "custom" and body.band_overrides and not body.contract_document_id:
        raise HTTPException(status_code=422, detail="contract_required_for_overrides")
    row = db.get(PricingOrgPricing, org_id)
    before = _org_out(org_id, row)
    if row is None:
        row = PricingOrgPricing(org_id=org_id)
        db.add(row)
    row.mode = body.mode
    row.preset_pct = body.preset_pct if body.mode == "custom" else None
    row.preset_per_stop_cents = body.preset_per_stop_cents if body.mode == "custom" else None
    row.flat_parcel_cents = body.flat_parcel_cents if body.mode == "custom" else None
    row.band_overrides = body.band_overrides if body.mode == "custom" else {}
    row.contract_document_id = body.contract_document_id
    row.red_reason = body.red_reason
    row.expires_at = body.expires_at
    row.effective_from = datetime.now(UTC)
    row.updated_by = _actor(ctx)
    db.flush()
    after = _org_out(org_id, row)
    _audit(db, ctx, "org_pricing", org_id, "updated", diff_lines(before, after), body.reason)
    db.commit()
    return after | {"preview": rows}


@router.get("/audit")
def audit(ctx: AdminDep, db: DbDep, entity_id: str | None = None, limit: int = 100) -> dict[str, Any]:
    _staff(ctx)
    q = select(PricingAudit).order_by(PricingAudit.created_at.desc()).limit(max(1, min(limit, 500)))
    if entity_id:
        q = q.where(PricingAudit.entity_id == entity_id)
    return {
        "items": [
            {"id": a.id, "entity": a.entity, "entity_id": a.entity_id, "action": a.action, "diff": a.diff,
             "actor_id": a.actor_id, "reason": a.reason, "created_at": a.created_at.isoformat() if a.created_at else None}
            for a in db.scalars(q)
        ]
    }


class QuoteItem(BaseModel):
    kind: str = "parcel"
    weight_kg: float = 0
    length_cm: float = 0
    width_cm: float = 0
    height_cm: float = 0
    furniture_class: str | None = None
    qty: int = Field(default=1, ge=1, le=200)


class StandardQuoteBody(BaseModel):
    items: list[QuoteItem] = Field(min_length=1, max_length=200)
    zone: str = "Z1"
    add_ons: dict[str, int] = Field(default_factory=dict)
    audience: str = Field(default="retail", pattern="^(retail|b2b)$")
    org_id: str | None = None
    stops: int = Field(default=1, ge=1, le=200)


@router.post("/standard/quote")
def standard_quote(body: StandardQuoteBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    """Staff explainer: the one Standard price (plus the org's Custom view)."""
    _staff(ctx)
    lines = published_lines(db)
    org = _org_obj(db.get(PricingOrgPricing, body.org_id)) if body.org_id else None
    db.commit()
    try:
        return quote(
            [Item(**i.model_dump()) for i in body.items], body.zone, add_ons=body.add_ons,
            audience=body.audience, lines=lines, org=org, stops=body.stops,
        )
    except ManualQuoteRequired as exc:
        raise HTTPException(status_code=422, detail=f"manual_quote:{exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---- §9.3 Send quote (72 h) -------------------------------------------------------

class SendQuoteBody(StandardQuoteBody):
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    lead_id: str | None = None


def _sent_out(row: Any) -> dict[str, Any]:
    from porterchain_api.pricing_engine.quote_send import quote_state

    return {
        "id": row.id, "token": row.token, "email": row.email, "org_id": row.org_id, "lead_id": row.lead_id,
        "total_cents": row.total_cents, "status": quote_state(row), "card_version": row.card_version,
        "expires_at": row.expires_at.isoformat(), "quote": row.payload,
    }


@router.post("/quotes/send")
def send_quote(body: SendQuoteBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    """Price on the published card, store it for 72 h and email the link (no booking, no invoice)."""
    from porterchain_api.config import get_settings
    from porterchain_api.pricing_engine.quote_send import create_sent_quote, deliver_quote_email
    from porterchain_api.pricing_engine.standard_live import published_lines as live_lines

    _staff(ctx)
    lines, version = live_lines(db)
    org = _org_obj(db.get(PricingOrgPricing, body.org_id)) if body.org_id else None
    try:
        q = quote([Item(**i.model_dump()) for i in body.items], body.zone, add_ons=body.add_ons,
                  audience=body.audience, lines=lines, org=org, stops=body.stops)
    except ManualQuoteRequired as exc:
        raise HTTPException(status_code=422, detail=f"manual_quote:{exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    row = create_sent_quote(db, email=body.email, payload=q, audience=body.audience, card_version=version,
                            org_id=body.org_id, lead_id=body.lead_id, actor_id=_actor(ctx))
    _audit(db, ctx, "sent_quote", row.id, "send", {"total_cents": row.total_cents, "email_domain": body.email.split("@")[-1]})
    link = f"{get_settings().customer_portal_url.rstrip('/')}/quote/{row.token}"
    delivery = deliver_quote_email(db, row, link)
    db.commit()
    return _sent_out(row) | {"link": link, "delivery": delivery}


@router.get("/quotes/sent")
def list_sent_quotes(ctx: AdminDep, db: DbDep, org_id: str | None = None, lead_id: str | None = None) -> dict[str, Any]:
    from porterchain_api.pricing_engine.models import PricingSentQuote

    _staff(ctx)
    stmt = select(PricingSentQuote).order_by(PricingSentQuote.created_at.desc()).limit(200)
    if org_id:
        stmt = stmt.where(PricingSentQuote.org_id == org_id)
    if lead_id:
        stmt = stmt.where(PricingSentQuote.lead_id == lead_id)
    return {"items": [_sent_out(r) for r in db.scalars(stmt)]}


@router.post("/quotes/{quote_id}/void")
def void_sent_quote(quote_id: str, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    from porterchain_api.pricing_engine.models import PricingSentQuote

    _staff(ctx)
    row = db.get(PricingSentQuote, quote_id)
    if row is None:
        raise HTTPException(status_code=404, detail="quote_not_found")
    row.status = "void"
    _audit(db, ctx, "sent_quote", row.id, "void", None)
    db.commit()
    return _sent_out(row)


# ---- §9.4 Per-order adjustments (role limits + reason) ---------------------------

class AdjustmentBody(BaseModel):
    cents: int = Field(ge=-1_000_000, le=1_000_000)
    category: str
    reason: str = Field(min_length=1, max_length=500)


def _role_key(ctx: AdminContext) -> str:
    return {AdminRole.SUPER_ADMIN: "super_admin", AdminRole.ADMIN: "admin"}.get(ctx.role, "other")


@router.get("/orders/{order_id}/adjustments")
def list_adjustments(order_id: str, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    from porterchain_api.booking_models import Order
    from porterchain_api.pricing_engine.models import PricingOrderAdjustment
    from porterchain_api.pricing_engine.quote_send import ADJUST_CATEGORIES, ADJUST_LIMITS, adjustments_total

    _staff(ctx)
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order_not_found")
    rows = db.scalars(select(PricingOrderAdjustment).where(PricingOrderAdjustment.order_id == order_id)
                      .order_by(PricingOrderAdjustment.created_at))
    adj = adjustments_total(db, order_id)
    cap, pct = ADJUST_LIMITS[_role_key(ctx)]
    allowed = int(order.amount_cents or 0) * pct // 100
    return {
        "order_amount_cents": int(order.amount_cents or 0), "adjustments_cents": adj,
        "adjusted_total_cents": int(order.amount_cents or 0) + adj,
        "limit_cents": min(allowed, cap) if cap is not None else allowed, "categories": list(ADJUST_CATEGORIES),
        "items": [{"id": r.id, "cents": r.cents, "category": r.category, "reason": r.reason,
                   "actor_role": r.actor_role, "created_at": r.created_at.isoformat() if r.created_at else None}
                  for r in rows],
    }


@router.post("/orders/{order_id}/adjustments")
def create_adjustment(order_id: str, body: AdjustmentBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    from porterchain_api.booking_models import Order
    from porterchain_api.pricing_engine.quote_send import AdjustmentRefused, add_adjustment

    _staff(ctx)
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order_not_found")
    try:
        row = add_adjustment(db, order=order, cents=body.cents, category=body.category, reason=body.reason,
                             role=_role_key(ctx), actor_id=_actor(ctx))
    except AdjustmentRefused as exc:  # refused before anything was written
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, ctx, "order_adjustment", order_id, "adjust", {"cents": body.cents, "category": body.category}, body.reason)
    db.commit()
    return list_adjustments(order_id, ctx, db) | {"created_id": row.id}


# ---- Public: view / accept a sent quote ------------------------------------------

public_router = APIRouter(prefix="/v1/public/quotes", tags=["public-quotes"])


@public_router.get("/{token}")
def public_quote(token: str, db: DbDep) -> dict[str, Any]:
    from porterchain_api.pricing_engine.models import PricingSentQuote
    from porterchain_api.pricing_engine.quote_send import quote_state

    row = db.scalar(select(PricingSentQuote).where(PricingSentQuote.token == token))
    if row is None:
        raise HTTPException(status_code=404, detail="quote_not_found")
    state = quote_state(row)
    if state in ("expired", "void"):
        raise HTTPException(status_code=410, detail=f"quote_{state}")
    return {"status": state, "total_cents": row.total_cents, "expires_at": row.expires_at.isoformat(),
            "lines": row.payload.get("lines", []), "hst_cents": row.payload.get("hst_cents"),
            "subtotal_cents": row.payload.get("subtotal_cents"), "zone_label": row.payload.get("zone_label")}


@public_router.post("/{token}/accept")
def accept_public_quote(token: str, db: DbDep) -> dict[str, Any]:
    from porterchain_api.pricing_engine.models import PricingSentQuote
    from porterchain_api.pricing_engine.quote_send import quote_state

    row = db.scalar(select(PricingSentQuote).where(PricingSentQuote.token == token))
    if row is None:
        raise HTTPException(status_code=404, detail="quote_not_found")
    state = quote_state(row)
    if state != "sent" and state != "accepted":
        raise HTTPException(status_code=410, detail=f"quote_{state}")
    if state == "sent":
        row.status = "accepted"
        row.accepted_at = datetime.now(UTC)
        db.add(PricingAudit(entity="sent_quote", entity_id=row.id, action="accept", diff=None))
        db.commit()
    return {"status": "accepted", "total_cents": row.total_cents}
