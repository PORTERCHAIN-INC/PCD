"""Inbound email webhook → lead threads (HMAC-signed parsed mail)."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db

router = APIRouter(prefix="/v1/public/mail", tags=["mail"])


@router.post("/inbound")
async def inbound_email(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_signature: Annotated[str | None, Header(alias="X-PorterChain-Signature")] = None,
) -> dict:
    """Body: {from, from_name?, to[], subject, text, message_id, headers?}.

    Signature: hex HMAC-SHA256 of the raw body with LEAD_INBOUND_EMAIL_SECRET.
    """
    secret = (settings.lead_inbound_email_secret or "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="inbound_email_not_configured")
    raw = await request.body()
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    given = (x_signature or "").strip().removeprefix("sha256=")
    if not given or not hmac.compare_digest(given, expected):
        raise HTTPException(status_code=401, detail="invalid_signature")
    try:
        data = json.loads(raw.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="invalid_json") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="invalid_payload")
    from porterchain_api.collaboration_engine.lead_email_inbound import (
        InboundEmail,
        ingest_inbound_email,
    )

    to = data.get("to") or []
    msg = InboundEmail(
        from_addr=str(data.get("from") or ""),
        from_name=(str(data["from_name"]) if data.get("from_name") else None),
        to=[str(t) for t in (to if isinstance(to, list) else [to])][:10],
        subject=str(data.get("subject") or "")[:500],
        text=str(data.get("text") or "")[:50_000],
        message_id=str(data.get("message_id") or "")[:255],
        headers={
            str(k): str(v)
            for k, v in (data.get("headers") or {}).items()
            if isinstance(data.get("headers"), dict)
        },
    )
    return ingest_inbound_email(db, settings, msg)
