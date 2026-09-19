"""Async lead ingest — Redis WEBHOOKS queue for hot fan-in volumes."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def enqueue_lead_ingest_events(events: list[dict[str, Any]], *, provider: str) -> str | None:
    """Enqueue pre-normalized CanonicalLeadEvent dicts. Returns message id or None."""
    if not events:
        return None
    try:
        from porterchain_shared.queue.names import QueueName
        from porterchain_shared.queue.publisher import get_queue_publisher

        msg = get_queue_publisher().enqueue(
            QueueName.WEBHOOKS,
            {
                "action": "lead_ingest",
                "provider": provider,
                "events": events,
            },
        )
        return getattr(msg, "message_id", None) or "queued"
    except Exception:
        logger.exception("lead_ingest_enqueue_failed provider=%s count=%s", provider, len(events))
        return None


def canonical_event_to_dict(event: Any) -> dict[str, Any]:
    """Serialize CanonicalLeadEvent for the worker (no actor)."""
    return {
        "channel": event.channel,
        "source": event.source,
        "provider": event.provider,
        "external_event_id": event.external_event_id,
        "company_name": event.company_name,
        "primary_contact_name": event.primary_contact_name,
        "email": event.email,
        "phone": event.phone,
        "intent_type": event.intent_type,
        "priority": event.priority,
        "status": event.status,
        "decision_status": event.decision_status,
        "message": event.message,
        "tags": list(event.tags or []),
        "custom_fields": dict(event.custom_fields or {}),
        "consent": dict(event.consent or {}),
        "attribution": dict(event.attribution or {}),
        "external_ids": dict(event.external_ids or {}),
        "referred_by_merchant_id": event.referred_by_merchant_id,
        "seed_conversation": bool(event.seed_conversation),
        "sla_first_response_minutes": int(event.sla_first_response_minutes or 60),
    }


def process_queued_lead_ingest(payload: dict[str, Any]) -> dict[str, Any]:
    """Worker entry — ingest each event via LeadIngestService."""
    from porterchain_api.collaboration_engine.lead_ingest_service import (
        CanonicalLeadEvent,
        LeadIngestService,
    )
    from porterchain_api.db import SessionLocal

    raw_events = payload.get("events") or []
    if not isinstance(raw_events, list):
        return {"ok": False, "error": "invalid_events"}

    svc = LeadIngestService()
    created = 0
    merged = 0
    errors = 0
    db = SessionLocal()
    try:
        for raw in raw_events:
            if not isinstance(raw, dict):
                errors += 1
                continue
            try:
                event = CanonicalLeadEvent(
                    channel=str(raw.get("channel") or "other"),
                    source=str(raw.get("source") or "other"),
                    provider=str(raw.get("provider") or "queued"),
                    external_event_id=str(raw.get("external_event_id") or ""),
                    company_name=str(raw.get("company_name") or "Unknown"),
                    primary_contact_name=raw.get("primary_contact_name"),
                    email=raw.get("email"),
                    phone=raw.get("phone"),
                    intent_type=str(raw.get("intent_type") or "merchant"),
                    priority=str(raw.get("priority") or "medium"),
                    status=str(raw.get("status") or "new"),
                    decision_status=str(raw.get("decision_status") or "new"),
                    message=raw.get("message"),
                    tags=list(raw.get("tags") or []),
                    custom_fields=dict(raw.get("custom_fields") or {}),
                    consent=dict(raw.get("consent") or {}),
                    attribution=dict(raw.get("attribution") or {}),
                    external_ids=dict(raw.get("external_ids") or {}),
                    referred_by_merchant_id=raw.get("referred_by_merchant_id"),
                    seed_conversation=bool(raw.get("seed_conversation", True)),
                    sla_first_response_minutes=int(raw.get("sla_first_response_minutes") or 60),
                )
                if not event.external_event_id:
                    errors += 1
                    continue
                result = svc.ingest(db, event)
                if result.created:
                    created += 1
                elif result.merged:
                    merged += 1
            except Exception:
                logger.exception("queued_lead_ingest_event_failed")
                errors += 1
                db.rollback()
    finally:
        db.close()
    return {
        "ok": errors == 0,
        "created": created,
        "merged": merged,
        "errors": errors,
        "count": len(raw_events),
    }


__all__ = [
    "canonical_event_to_dict",
    "enqueue_lead_ingest_events",
    "process_queued_lead_ingest",
]
