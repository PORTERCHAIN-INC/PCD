"""ZeptoMail webhook: per-message delivered / opened / bounced + hard-bounce suppression.

Header: X-PorterChain-Mail-Webhook (HTTP headers are case-insensitive, so the old
X-Porterchain-Mail-Webhook spelling is the same header).
"""

from __future__ import annotations

import hmac
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.config import get_settings
from porterchain_api.db import get_db

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
        # Deploy prerequisite (RUNBOOK "Email notifications"): without the secret anyone
        # could mark customer addresses as bounced. Fail closed outside local/test.
        if str(getattr(settings, "app_env", "")).lower() not in {"local", "development", "dev", "test"}:
            raise HTTPException(status_code=503, detail="mail_webhook_not_configured")
    elif not hmac.compare_digest((x_porterchain_mail_webhook or "").strip(), secret):
        raise HTTPException(status_code=401, detail="mail_webhook_unauthorized")
    from porterchain_api.notification_engine.bounce import (
        event_kinds,
        record_tracking_event,
    )

    if not event_kinds(body):
        return {"ok": True, "bounced": 0, "messages": 0}
    result = record_tracking_event(db, body)
    return {"ok": True, "bounced": result["suppressed"], "messages": result["messages"]}
