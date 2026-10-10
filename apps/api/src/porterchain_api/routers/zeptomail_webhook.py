"""ZeptoMail bounce and complaint webhook."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.config import get_settings
from porterchain_api.db import get_db
from porterchain_api.notification_engine.bounce import (
    extract_bounced_addresses,
    is_bounce_event,
    mark_addresses_bounced,
)

router = APIRouter(prefix="/v1/public/mail", tags=["mail"])


@router.post("/zeptomail")
def zeptomail_event(
    body: dict[str, Any],
    db: Session = Depends(get_db),
    x_porterchain_mail_webhook: str | None = Header(default=None),
) -> dict[str, int | bool]:
    settings = get_settings()
    secret = (getattr(settings, "zeptomail_webhook_secret", None) or "").strip()
    if secret and (x_porterchain_mail_webhook or "").strip() != secret:
        raise HTTPException(status_code=401, detail="mail_webhook_unauthorized")
    if not is_bounce_event(body):
        return {"ok": True, "bounced": 0}
    marked = mark_addresses_bounced(db, extract_bounced_addresses(body))
    return {"ok": True, "bounced": marked}
