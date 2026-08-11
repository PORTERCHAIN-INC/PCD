"""Visitor session tracking — anonymous quote + first-party intent signals."""

from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.domain.visitor_intent import compute_intent_score
from porterchain_api.models import VisitorSession


def _merge_signals(existing: dict | None, patch: dict[str, Any]) -> dict[str, Any]:
    base: dict[str, Any] = dict(existing or {})
    for key, value in patch.items():
        if value is None or value == "" or value == []:
            continue
        if key == "paths" and isinstance(value, list):
            prev = base.get("paths") if isinstance(base.get("paths"), list) else []
            merged = list(prev)
            for path in value:
                if isinstance(path, str) and path and (not merged or merged[-1] != path):
                    merged.append(path[:256])
            base["paths"] = merged[-24:]
            continue
        if key == "page_view_count" and isinstance(value, int):
            prev_count = base.get("page_view_count")
            prev_n = prev_count if isinstance(prev_count, int) else 0
            base["page_view_count"] = max(prev_n, value)
            continue
        base[key] = value
    return base


class VisitorTrackingService:
    def ensure_session(
        self,
        db: Session,
        *,
        session_id: str,
        ip_address: str | None = None,
        browser: str | None = None,
        utm_source: str | None = None,
        utm_medium: str | None = None,
        utm_campaign: str | None = None,
        referrer: str | None = None,
        device: str | None = None,
        location: dict | None = None,
        signals: dict[str, Any] | None = None,
    ) -> VisitorSession:
        visitor = db.query(VisitorSession).filter(VisitorSession.id == session_id).first()
        ip_hash = self._hash_ip(ip_address) if ip_address else None
        signal_patch = dict(signals or {})

        if visitor:
            if ip_hash:
                visitor.ip_hash = ip_hash
            if browser:
                visitor.browser = browser
            if utm_source:
                visitor.utm_source = utm_source
            if utm_medium:
                visitor.utm_medium = utm_medium
            if utm_campaign:
                visitor.utm_campaign = utm_campaign
            if referrer:
                visitor.referrer = referrer
            if device:
                visitor.device = device
            if location:
                visitor.location = location
            visitor.signals = _merge_signals(visitor.signals, signal_patch)
            visitor.touch_count = int(visitor.touch_count or 0) + 1
        else:
            visitor = VisitorSession(
                id=session_id,
                ip_hash=ip_hash,
                browser=browser,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                referrer=referrer,
                device=device,
                location=location,
                signals=_merge_signals(None, signal_patch),
                touch_count=1,
            )
            db.add(visitor)
            emit_event(
                db,
                event_type=E.VISITOR_SESSION_STARTED,
                aggregate_type="visitor",
                aggregate_id=session_id,
                actor_type="visitor",
                actor_id=session_id,
            )

        visitor.intent_score = compute_intent_score(
            signals=visitor.signals if isinstance(visitor.signals, dict) else {},
            quote_generated=bool(visitor.quote_generated),
            touch_count=int(visitor.touch_count or 0),
            has_utm=bool(visitor.utm_source or visitor.utm_medium or visitor.utm_campaign),
        )
        db.commit()
        db.refresh(visitor)
        return visitor

    def record_quote(self, db: Session, session_id: str, quote_id: str) -> None:
        visitor = db.query(VisitorSession).filter(VisitorSession.id == session_id).first()
        if not visitor:
            return
        visitor.quote_generated = True
        visitor.last_quote_id = quote_id
        visitor.signals = _merge_signals(
            visitor.signals if isinstance(visitor.signals, dict) else {},
            {"last_quote_id": quote_id, "intent": "quote"},
        )
        visitor.intent_score = compute_intent_score(
            signals=visitor.signals if isinstance(visitor.signals, dict) else {},
            quote_generated=True,
            touch_count=int(visitor.touch_count or 0),
            has_utm=bool(visitor.utm_source or visitor.utm_medium or visitor.utm_campaign),
        )
        db.commit()

    def merge_to_customer(self, db: Session, session_id: str, customer_id: str) -> None:
        visitor = db.query(VisitorSession).filter(VisitorSession.id == session_id).first()
        if visitor:
            visitor.customer_id = customer_id
            existing = getattr(visitor, "signals", None)
            visitor.signals = _merge_signals(
                existing if isinstance(existing, dict) else {},
                {"merged_customer_id": customer_id},
            )
        emit_event(
            db,
            event_type=E.SESSION_MERGED,
            aggregate_type="visitor",
            aggregate_id=session_id,
            actor_type="customer",
            actor_id=customer_id,
            payload={"customer_id": customer_id, "session_id": session_id},
        )
        db.commit()

    def get_session(self, db: Session, session_id: str) -> VisitorSession | None:
        return db.query(VisitorSession).filter(VisitorSession.id == session_id).first()

    @staticmethod
    def signals_from_tracking(tracking: Any | None) -> dict[str, Any]:
        if tracking is None:
            return {}
        data = tracking.model_dump() if hasattr(tracking, "model_dump") else dict(tracking)
        keys = (
            "landing_page",
            "from_page",
            "locale",
            "source_page",
            "page_view_count",
            "paths",
            "intent",
            "guide_stage",
            "utm_term",
            "utm_content",
        )
        return {k: data[k] for k in keys if data.get(k) is not None}

    @staticmethod
    def _hash_ip(ip: str) -> str:
        return hashlib.sha256(ip.encode()).hexdigest()[:32]
