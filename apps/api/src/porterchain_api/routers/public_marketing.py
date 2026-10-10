"""Public marketing endpoints for the website: instant estimate, calculator lead, config.

No auth (public website), no PII needed for a price, per-IP rate limits.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.marketing_site.config import (
    get_marketing_site,
    public_marketing_config,
)
from porterchain_api.marketing_site.estimate_service import estimate_price
from porterchain_api.marketing_site.lead_service import submit_calculator_lead
from porterchain_api.marketing_site.rate_limit import client_ip, enforce_public_limit
from porterchain_api.routers.public_ingest_auth import verify_public_ingest_key
from porterchain_api.marketing_site.schemas import (
    CalculatorLeadRequest,
    CalculatorLeadResponse,
    EstimateRequest,
    EstimateResponse,
)
from porterchain_api.routers.public_ingest_auth import verify_public_ingest_key

router = APIRouter(prefix="/v1/public", tags=["public-marketing"])


@router.get("/marketing-config")
def get_public_marketing_config(db: Session = Depends(get_db)) -> dict:
    """Website switches (hero A/B flag). Safe to cache briefly."""
    return public_marketing_config(get_marketing_site(db))


@router.post("/estimate", response_model=EstimateResponse)
def post_public_estimate(
    body: EstimateRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EstimateResponse:
    """Live retail price between two postal areas. Stores nothing."""
    cfg = get_marketing_site(db)["calculator"]
    if not cfg.get("enabled", True):
        raise HTTPException(status_code=404, detail="calculator_disabled")
    enforce_public_limit(
        request, bucket="estimate", limit=int(cfg["estimates_per_minute"]), app_env=settings.app_env
    )
    try:
        data = estimate_price(
            db,
            settings,
            pickup=body.pickup_postal,
            dropoff=body.dropoff_postal,
            vehicle_class=body.vehicle_class,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return EstimateResponse(**data)


@router.post("/calculator-leads", response_model=CalculatorLeadResponse, status_code=202)
def post_calculator_lead(
    body: CalculatorLeadRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_ingest_key: Annotated[str | None, Header(alias="X-Ingest-Key")] = None,
) -> CalculatorLeadResponse:
    """Lead form under the calculator -> CRM lead (no emails are sent)."""
    verify_public_ingest_key(settings, x_ingest_key)
    cfg = get_marketing_site(db)["calculator"]
    if not cfg.get("enabled", True):
        raise HTTPException(status_code=404, detail="calculator_disabled")
    enforce_public_limit(
        request, bucket="calc_lead", limit=int(cfg["leads_per_minute"]), app_env=settings.app_env
    )
    try:
        submit_calculator_lead(
            db,
            body,
            min_fill_seconds=int(cfg["min_fill_seconds"]),
            auto_outreach=bool(cfg.get("auto_outreach")),
            ip=client_ip(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # Same answer for real and dropped (spam) submissions.
    return CalculatorLeadResponse(status="received")
