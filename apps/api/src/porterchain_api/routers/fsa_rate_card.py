"""FSA rate card: merchant read/export, admin regenerate + cell overrides."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_engine.rbac import require_module as require_admin_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.pricing_engine import fsa_rate_card as cards
from porterchain_api.routers.merchant._deps import (
    MerchantContext,
    get_merchant_context,
    require_module,
)

merchant_router = APIRouter(prefix="/v1/merchant", tags=["merchant"])
admin_router = APIRouter(prefix="/v1/admin/merchants", tags=["merchants"])

Format = Literal["json", "csv", "pdf"]


class FsaCellOverride(BaseModel):
    #: New price for this drop FSA in cents; null restores the computed price.
    cents: int | None = Field(default=None, gt=0, le=1_000_000)


def _card(db: Session, merchant_id: str, fmt: Format):
    try:
        card = cards.rate_card(db, merchant_id)
        from porterchain_api.admin_engine.platform_settings import supplier_gst_hst_number

        card["supplier_gst_hst_number"] = supplier_gst_hst_number(db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    if fmt == "csv":
        return Response(
            cards.to_csv(card),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=porterchain-fsa-rate-card.csv"},
        )
    if fmt == "pdf":
        return Response(
            cards.to_pdf(card),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=porterchain-fsa-rate-card.pdf"},
        )
    return card


@merchant_router.get("/pricing/fsa-rate-card")
def merchant_fsa_rate_card(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    format: Format = Query(default="json"),
    db: Session = Depends(get_db),
):
    require_module(ctx, "billing")
    return _card(db, ctx.merchant.id, format)


@admin_router.get("/{merchant_id}/fsa-rate-card")
def admin_fsa_rate_card(
    merchant_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    format: Format = Query(default="json"),
    db: Session = Depends(get_db),
):
    require_admin_module(ctx, "merchants")
    return _card(db, merchant_id, format)


@admin_router.post("/{merchant_id}/fsa-rate-card/regenerate")
def admin_regenerate_fsa_rate_card(
    merchant_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_admin_module(ctx, "merchants")
    try:
        cards.generate(db, merchant_id, force=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    return _card(db, merchant_id, "json")


@admin_router.put("/{merchant_id}/fsa-rate-card/cells/{dest_fsa}")
def admin_override_fsa_cell(
    merchant_id: str,
    dest_fsa: str,
    body: FsaCellOverride,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_admin_module(ctx, "merchants")
    try:
        row = cards.override(db, merchant_id, dest_fsa, body.cents)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {
        "dest_fsa": row.dest_fsa,
        "price_cents": row.flat_cents,
        "override": bool((row.config or {}).get("override")),
    }
