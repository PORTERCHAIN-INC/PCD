"""Pricing admin (doc 72 §9): Standard rate card versions, org Custom pricing, audit.

One Standard card for every channel. Super admins edit and publish the Standard
card; admins set an org to Standard or Custom (presets, band overrides) within
the guardrails. Every change writes a pricing_audit row (``pricing_engine.rate_card_admin``).
Sent quotes, per-order adjustments and the public quote view live in ``pricing_quotes``.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Any, TypeVar

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext, AdminRole
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.pricing_engine import rate_card_admin as cards
from porterchain_api.pricing_engine.rate_card_admin import PricingAdminError
from porterchain_pricing.standard_card import Item

router = APIRouter(prefix="/v1/pricing", tags=["pricing-admin"])

AdminDep = Annotated[AdminContext, Depends(get_admin_context)]
DbDep = Annotated[Session, Depends(get_db)]
T = TypeVar("T")

published_lines = cards.published_lines


def _staff(ctx: AdminContext) -> None:
    if ctx.role not in (AdminRole.SUPER_ADMIN, AdminRole.ADMIN):
        raise HTTPException(status_code=403, detail="pricing_admin_only")


def _super(ctx: AdminContext) -> None:
    if ctx.role != AdminRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="super_admin_only")


def _actor(ctx: AdminContext) -> str | None:
    return getattr(ctx.user, "id", None) or getattr(ctx.user, "porterchain_user_id", None)


def _call(fn: Callable[[], T]) -> T:
    try:
        return fn()
    except PricingAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/rate-cards/standard")
def get_standard(ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    _staff(ctx)
    return cards.get_standard(db, can_edit=ctx.role == AdminRole.SUPER_ADMIN)


class DraftBody(BaseModel):
    lines: dict[str, Any] | None = None
    notes: str | None = Field(default=None, max_length=2000)


@router.post("/rate-cards/standard/draft")
def save_draft(body: DraftBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    _super(ctx)
    return _call(lambda: cards.save_draft(db, _actor(ctx), body.lines, body.notes))


@router.post("/rate-cards/standard/preview")
def preview_lines(body: DraftBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    _staff(ctx)
    return _call(lambda: cards.preview_lines(db, body.lines))


class PublishBody(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


@router.post("/rate-cards/standard/publish")
def publish(body: PublishBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    _super(ctx)
    return _call(lambda: cards.publish(db, _actor(ctx), body.reason))


class RollbackBody(BaseModel):
    version: int
    reason: str = Field(min_length=3, max_length=2000)


@router.post("/rate-cards/standard/rollback")
def rollback(body: RollbackBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    """Republish an older version's lines as a new version (history is never rewritten)."""
    _super(ctx)
    return _call(lambda: cards.rollback(db, _actor(ctx), body.version, body.reason))


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


@router.get("/orgs/{org_id}")
def get_org(org_id: str, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    _staff(ctx)
    return cards.get_org(db, org_id)


@router.post("/orgs/{org_id}/preview")
def preview_org(org_id: str, body: OrgPricingBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    _staff(ctx)
    return _call(lambda: cards.preview_org(db, org_id, body))


@router.put("/orgs/{org_id}")
def put_org(org_id: str, body: OrgPricingBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    _staff(ctx)
    return _call(lambda: cards.put_org(db, _actor(ctx), org_id, body))


@router.get("/audit")
def audit(ctx: AdminDep, db: DbDep, entity_id: str | None = None, limit: int = 100) -> dict[str, Any]:
    _staff(ctx)
    return cards.list_audit(db, entity_id, limit)


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


def items_of(body: StandardQuoteBody) -> list[Item]:
    return [Item(**i.model_dump()) for i in body.items]


@router.post("/standard/quote")
def standard_quote(body: StandardQuoteBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    """Staff explainer: the one Standard price (plus the org's Custom view)."""
    _staff(ctx)
    return _call(lambda: cards.standard_quote(db, body, items_of(body)))


# Sent quotes, adjustments and the public quote routes (split out to keep this module thin).
from porterchain_api.routers.pricing_quotes import public_router, quotes_router  # noqa: E402

router.include_router(quotes_router)

__all__ = ["public_router", "published_lines", "router"]
