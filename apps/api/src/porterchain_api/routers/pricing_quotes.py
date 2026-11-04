"""Pricing admin §9.3 sent quotes (72 h), §9.4 per-order adjustments, and the public quote view.

Mounted under ``/v1/pricing`` by ``routers/pricing_cards.py``; DB access in ``pricing_engine.quote_admin``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from porterchain_api.admin_engine.rbac import AdminContext, AdminRole
from porterchain_api.pricing_engine import quote_admin as quotes
from porterchain_api.routers.pricing_cards import (
    AdminDep,
    DbDep,
    StandardQuoteBody,
    _actor,
    _call,
    _staff,
    items_of,
)

quotes_router = APIRouter()


class SendQuoteBody(StandardQuoteBody):
    email: str = Field(min_length=3, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    lead_id: str | None = None


@quotes_router.post("/quotes/send")
def send_quote(body: SendQuoteBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    """Price on the published card, store it for 72 h and email the link (no booking, no invoice)."""
    _staff(ctx)
    return _call(lambda: quotes.send_quote(db, _actor(ctx), body, items_of(body)))


@quotes_router.get("/quotes/sent")
def list_sent_quotes(
    ctx: AdminDep, db: DbDep, org_id: str | None = None, lead_id: str | None = None
) -> dict[str, Any]:
    _staff(ctx)
    return quotes.list_sent_quotes(db, org_id, lead_id)


@quotes_router.post("/quotes/{quote_id}/void")
def void_sent_quote(quote_id: str, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    _staff(ctx)
    return _call(lambda: quotes.void_sent_quote(db, _actor(ctx), quote_id))


class AdjustmentBody(BaseModel):
    cents: int = Field(ge=-1_000_000, le=1_000_000)
    category: str
    reason: str = Field(min_length=1, max_length=500)


def _role_key(ctx: AdminContext) -> str:
    return {AdminRole.SUPER_ADMIN: "super_admin", AdminRole.ADMIN: "admin"}.get(ctx.role, "other")


@quotes_router.get("/orders/{order_id}/adjustments")
def list_adjustments(order_id: str, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    _staff(ctx)
    return _call(lambda: quotes.list_adjustments(db, order_id, _role_key(ctx)))


@quotes_router.post("/orders/{order_id}/adjustments")
def create_adjustment(order_id: str, body: AdjustmentBody, ctx: AdminDep, db: DbDep) -> dict[str, Any]:
    _staff(ctx)
    return _call(
        lambda: quotes.create_adjustment(
            db, _actor(ctx), _role_key(ctx), order_id, body.cents, body.category, body.reason
        )
    )


# ---- Public: view / accept a sent quote ------------------------------------------

public_router = APIRouter(prefix="/v1/public/quotes", tags=["public-quotes"])


@public_router.get("/{token}")
def public_quote(token: str, db: DbDep) -> dict[str, Any]:
    return _call(lambda: quotes.public_quote(db, token))


@public_router.post("/{token}/accept")
def accept_public_quote(token: str, db: DbDep) -> dict[str, Any]:
    return _call(lambda: quotes.accept_public_quote(db, token))
