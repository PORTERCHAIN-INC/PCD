"""Webhook fan-in processing — keep routers free of db.commit (D2 §0.3.3)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.lead_ingest_service import LeadIngestService

logger = logging.getLogger(__name__)

_ingest = LeadIngestService()


def process_inbound_lead_events(
    db: Session,
    events: list,
    *,
    provider: str,
    settings: Any,
) -> dict[str, Any]:
    """Sync ingest (+ optional WhatsApp auto-reply), or enqueue when async/hot."""
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

    created = 0
    merged = 0
    lead_ids: list[str] = []
    replies: list[dict] = []
    for event in events:
        try:
            result = _ingest.ingest(db, event)
            lead_ids.append(result.lead.id)
            if result.created:
                created += 1
            elif result.merged:
                merged += 1
            ch = (event.channel or "").lower()
            wa_on = bool(getattr(settings, "whatsapp_cloud_enabled", False))
            if wa_on and (ch == "whatsapp" or (event.source or "").lower() == "whatsapp"):
                from porterchain_api.collaboration_engine.lead_agent import (
                    maybe_auto_reply_after_ingest,
                )

                reply = maybe_auto_reply_after_ingest(
                    db,
                    result.lead,
                    channel=event.channel,
                    message=event.message,
                )
                if reply:
                    replies.append({"lead_id": result.lead.id, **reply})
                    try:
                        db.commit()
                    except Exception:
                        db.rollback()
        except Exception:
            logger.exception("lead_webhook_ingest_failed provider=%s", provider)
    out: dict[str, Any] = {
        "ok": True,
        "queued": False,
        "created": created,
        "merged": merged,
        "lead_ids": lead_ids,
        "count": len(events),
    }
    if replies:
        out["wa_replies"] = replies
    return out


__all__ = ["process_inbound_lead_events"]
