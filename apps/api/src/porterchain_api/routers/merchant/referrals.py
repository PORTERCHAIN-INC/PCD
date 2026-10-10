"""Merchant self-serve referrals — share link, submit lead, credits."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from porterchain_api.auth.merchant import get_merchant_context
from porterchain_api.collaboration_engine.lead_channel_adapters import (
    event_from_referral,
)
from porterchain_api.collaboration_engine.lead_ingest_service import LeadIngestService
from porterchain_api.collaboration_engine.lead_ops import merchant_referral_overview
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.merchant_engine.rbac import MerchantContext, require_module
from porterchain_api.routers.merchant._deps import _handle_permission, router
from porterchain_api.schemas_crm import LeadOut

_ingest = LeadIngestService()


class MerchantReferralCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=64)
    contact_name: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=4000)


@router.get("/referrals")
def get_merchant_referrals(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Share link + credit status for the signed-in merchant."""
    try:
        require_module(ctx, "settings")
        return merchant_referral_overview(
            db, merchant_id=ctx.merchant.id, settings=settings
        )
    except PermissionError as exc:
        _handle_permission(exc)
        raise


@router.post("/referrals", response_model=LeadOut, status_code=201)
def create_merchant_referral(
    body: MerchantReferralCreate,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> LeadOut:
    """Merchant submits a referred prospect into the lead ingest bus."""
    try:
        require_module(ctx, "settings")
        if not (body.email or body.phone):
            raise HTTPException(status_code=422, detail="email_or_phone_required")
        result = _ingest.ingest(
            db,
            event_from_referral(
                company_name=body.company_name,
                email=body.email,
                phone=body.phone,
                contact_name=body.contact_name,
                referred_by_merchant_id=ctx.merchant.id,
                notes=body.notes,
            ),
        )
        return LeadOut.model_validate(result.lead)
    except PermissionError as exc:
        _handle_permission(exc)
        raise
