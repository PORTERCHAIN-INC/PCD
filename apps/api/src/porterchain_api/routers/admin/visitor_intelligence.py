"""Admin visitor intelligence — first-party session + CRM fusion insights."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from porterchain_api.booking_engine.visitor_intelligence import VisitorIntelligenceService
from porterchain_api.collaboration_engine import CrmSalesService
from porterchain_api.routers.admin._deps import (
    AdminContext,
    Depends,
    get_admin_context,
    get_db,
    require_module,
    router,
)

_intel = VisitorIntelligenceService()
_crm = CrmSalesService()


class VisitorIntelligenceResponse(BaseModel):
    session_id: str | None = None
    intent_score: int | None = None
    touch_count: int | None = None
    quote_generated: bool | None = None
    last_quote_id: str | None = None
    customer_id: str | None = None
    device: str | None = None
    attribution: dict[str, Any] = Field(default_factory=dict)
    signals: dict[str, Any] = Field(default_factory=dict)
    quotes: list[dict[str, Any]] = Field(default_factory=list)
    guide: dict[str, Any] | None = None


@router.get(
    "/visitor-intelligence/{session_id}",
    response_model=VisitorIntelligenceResponse,
)
def get_visitor_intelligence(
    session_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> VisitorIntelligenceResponse:
    require_module(ctx, "crm_read")
    insight = _intel.insight_for_session(db, session_id.strip()[:64])
    if not insight:
        raise HTTPException(status_code=404, detail="visitor_session_not_found")
    return VisitorIntelligenceResponse(**insight)


@router.get(
    "/leads/{lead_id}/visitor-intelligence",
    response_model=VisitorIntelligenceResponse,
)
def get_lead_visitor_intelligence(
    lead_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> VisitorIntelligenceResponse:
    require_module(ctx, "crm_read")
    lead = _crm.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    insight = _intel.insight_for_lead(db, lead) or {}
    return VisitorIntelligenceResponse(**insight)
