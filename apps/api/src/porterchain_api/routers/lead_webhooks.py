"""Public lead channel webhooks — Meta / WhatsApp / Google → Lead Ingest Bus."""

from __future__ import annotations

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.lead_channel_adapters import (
    event_from_google_lead,
    event_from_linkedin_lead,
    event_from_x_lead,
    event_from_youtube_lead,
    events_from_meta_payload,
    verify_meta_signature,
)
from porterchain_api.collaboration_engine.lead_ingest_service import LeadIngestService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.platform.rate_limit import (
    bucket_key,
    check_fixed_window,
    incr_rate_limit_unavailable,
    incr_rate_limited,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/public/leads", tags=["lead-webhooks"])
_ingest = LeadIngestService()

# Public fan-in: generous but bounded (per client IP / minute).
_LEAD_WEBHOOK_LIMIT = 120
_TRAFFIC = "lead_webhooks"


def _rate_limit_webhook(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    identity = forwarded or client
    key = bucket_key(_TRAFFIC, identity)
    allowed, _current, err = check_fixed_window(key, _LEAD_WEBHOOK_LIMIT)
    if err:
        incr_rate_limit_unavailable(_TRAFFIC)
        # Fail open for webhooks when Redis is dark — signature still required.
        logger.warning("lead_webhook_rate_limit_unavailable: %s", err)
        return
    if not allowed:
        incr_rate_limited(_TRAFFIC)
        raise HTTPException(status_code=429, detail="lead_webhook_rate_limited")


def _process_events(
    db: Session,
    settings: Settings,
    events: list,
    *,
    provider: str,
) -> dict:
    """Sync ingest, or enqueue when LEAD_INGEST_ASYNC / batch size hot."""
    from porterchain_api.collaboration_engine.lead_ingest_jobs import (
        canonical_event_to_dict,
        enqueue_lead_ingest_events,
    )

    async_mode = bool(getattr(settings, "lead_ingest_async", False)) or len(events) >= 5
    if async_mode and events:
        queued = enqueue_lead_ingest_events(
            [canonical_event_to_dict(e) for e in events],
            provider=provider,
        )
        if queued:
            return {
                "ok": True,
                "queued": True,
                "queue_id": queued,
                "count": len(events),
            }
        # Fall through to sync if enqueue failed.

    created = 0
    merged = 0
    lead_ids: list[str] = []
    for event in events:
        try:
            result = _ingest.ingest(db, event)
            lead_ids.append(result.lead.id)
            if result.created:
                created += 1
            elif result.merged:
                merged += 1
        except Exception:
            logger.exception("lead_webhook_ingest_failed provider=%s", provider)
    return {
        "ok": True,
        "queued": False,
        "created": created,
        "merged": merged,
        "lead_ids": lead_ids,
        "count": len(events),
    }


@router.get("/webhooks/meta")
def meta_webhook_verify(
    settings: Settings = Depends(get_settings),
    hub_mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    hub_verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    hub_challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
) -> int | dict:
    token = (settings.meta_webhook_verify_token or "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="meta_webhook_not_configured")
    if hub_mode == "subscribe" and hub_verify_token == token and hub_challenge is not None:
        try:
            return int(hub_challenge)
        except ValueError:
            return {"challenge": hub_challenge}
    raise HTTPException(status_code=403, detail="meta_verify_failed")


@router.post("/webhooks/meta")
async def meta_webhook_ingest(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_hub_signature_256: Annotated[str | None, Header(alias="X-Hub-Signature-256")] = None,
) -> dict:
    _rate_limit_webhook(request)
    secret = (settings.meta_app_secret or "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="meta_webhook_not_configured")
    raw = await request.body()
    if not verify_meta_signature(
        app_secret=secret, raw_body=raw, signature_header=x_hub_signature_256
    ):
        raise HTTPException(status_code=401, detail="invalid_meta_signature")
    try:
        payload = json.loads(raw.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid_json") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid_payload")

    events = events_from_meta_payload(payload)
    return _process_events(db, settings, events, provider="meta")


@router.post("/webhooks/google")
async def google_lead_webhook(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_lead_webhook_secret: Annotated[str | None, Header(alias="X-Lead-Webhook-Secret")] = None,
) -> dict:
    _rate_limit_webhook(request)
    expected = (settings.google_lead_webhook_secret or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="google_lead_webhook_not_configured")
    if not x_lead_webhook_secret or x_lead_webhook_secret != expected:
        raise HTTPException(status_code=401, detail="invalid_webhook_secret")
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid_json") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid_payload")
    event = event_from_google_lead(payload)
    out = _process_events(db, settings, [event], provider="google")
    if out.get("queued"):
        return out
    return {
        "ok": True,
        "lead_id": (out.get("lead_ids") or [None])[0],
        "created": out.get("created", 0) > 0,
        "merged": out.get("merged", 0) > 0,
        "queued": False,
    }


def _require_social_secret(settings: Settings, header: str | None) -> None:
    expected = (settings.social_lead_webhook_secret or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="social_lead_webhook_not_configured")
    if not header or header != expected:
        raise HTTPException(status_code=401, detail="invalid_webhook_secret")


async def _json_body(request: Request) -> dict:
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid_json") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid_payload")
    return payload


def _social_result(out: dict) -> dict:
    if out.get("queued"):
        return out
    return {
        "ok": True,
        "lead_id": (out.get("lead_ids") or [None])[0],
        "created": out.get("created", 0) > 0,
        "merged": out.get("merged", 0) > 0,
        "queued": False,
    }


@router.post("/webhooks/linkedin")
async def linkedin_lead_webhook(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_lead_webhook_secret: Annotated[str | None, Header(alias="X-Lead-Webhook-Secret")] = None,
) -> dict:
    _rate_limit_webhook(request)
    _require_social_secret(settings, x_lead_webhook_secret)
    event = event_from_linkedin_lead(await _json_body(request))
    return _social_result(_process_events(db, settings, [event], provider="linkedin"))


@router.post("/webhooks/x")
async def x_lead_webhook(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_lead_webhook_secret: Annotated[str | None, Header(alias="X-Lead-Webhook-Secret")] = None,
) -> dict:
    _rate_limit_webhook(request)
    _require_social_secret(settings, x_lead_webhook_secret)
    event = event_from_x_lead(await _json_body(request))
    return _social_result(_process_events(db, settings, [event], provider="x"))


@router.post("/webhooks/youtube")
async def youtube_lead_webhook(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_lead_webhook_secret: Annotated[str | None, Header(alias="X-Lead-Webhook-Secret")] = None,
) -> dict:
    _rate_limit_webhook(request)
    _require_social_secret(settings, x_lead_webhook_secret)
    event = event_from_youtube_lead(await _json_body(request))
    return _social_result(_process_events(db, settings, [event], provider="youtube"))
