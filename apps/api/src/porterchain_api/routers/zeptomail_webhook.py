"""ZeptoMail webhook: per-message delivered / opened / bounced + hard-bounce suppression.

Header: X-PorterChain-Mail-Webhook (HTTP headers are case-insensitive, so the old
X-Porterchain-Mail-Webhook spelling is the same header).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy.orm import Session
from fastapi import Depends

from porterchain_api.config import get_settings
from porterchain_api.db import get_db
from porterchain_api.platform.secret_compare import secrets_match

router = APIRouter(prefix="/v1/public/mail", tags=["mail"])


@router.post("/zeptomail")
def zeptomail_event(
    body: dict[str, Any],
    db: Session = Depends(get_db),
    x_porterchain_mail_webhook: str | None = Header(default=None),
) -> dict[str, int | bool]:
    settings = get_settings()
    secret = (getattr(settings, "zeptomail_webhook_secret", None) or "").strip()
    if not secret:
        # Fail closed: an unset secret must not let anyone mark addresses bounced.
        raise HTTPException(status_code=503, detail="mail_webhook_not_configured")
    if not secrets_match(x_porterchain_mail_webhook, secret):
        raise HTTPException(status_code=401, detail="mail_webhook_unauthorized")
    from porterchain_api.notification_engine.bounce import (
        event_kinds,
        record_tracking_event,
    )

    if not event_kinds(body):
        return {"ok": True, "bounced": 0, "messages": 0}
    result = record_tracking_event(db, body)
    return {"ok": True, "bounced": result["suppressed"], "messages": result["messages"]}

# Re-exports kept for existing importers (integration).
from porterchain_api.notification_engine.bounce import extract_bounced_addresses  # noqa: E402, F401
from porterchain_api.notification_engine.bounce import is_bounce_event  # noqa: E402, F401
from porterchain_api.notification_engine.bounce import mark_addresses_bounced  # noqa: E402, F401
