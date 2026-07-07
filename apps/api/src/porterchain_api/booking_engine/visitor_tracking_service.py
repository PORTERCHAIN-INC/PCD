"""Visitor session tracking — anonymous quote flow per BUSINESS_WORKFLOW.md."""

import hashlib

from sqlalchemy.orm import Session

from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.models import VisitorSession


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
    ) -> VisitorSession:
        visitor = db.query(VisitorSession).filter(VisitorSession.id == session_id).first()
        ip_hash = self._hash_ip(ip_address) if ip_address else None

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

        db.commit()
        db.refresh(visitor)
        return visitor

    def record_quote(self, db: Session, session_id: str, quote_id: str) -> None:
        visitor = db.query(VisitorSession).filter(VisitorSession.id == session_id).first()
        if not visitor:
            return
        visitor.quote_generated = True
        visitor.last_quote_id = quote_id
        db.commit()

    def merge_to_customer(self, db: Session, session_id: str, customer_id: str) -> None:
        emit_event(
            db,
            event_type=E.SESSION_MERGED,
            aggregate_type="visitor",
            aggregate_id=session_id,
            actor_type="customer",
            actor_id=customer_id,
            payload={"customer_id": customer_id},
        )
        db.commit()

    @staticmethod
    def _hash_ip(ip: str) -> str:
        return hashlib.sha256(ip.encode()).hexdigest()[:32]
