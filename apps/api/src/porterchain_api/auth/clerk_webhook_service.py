"""Clerk webhook processing — signed, idempotent, no operational cascade deletes."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from porterchain_api.auth.clerk_webhook_idempotency import (
    claim_clerk_event,
    complete_clerk_event,
    release_clerk_event,
)
from porterchain_api.auth.clerk_webhook_verify import (
    ClerkWebhookSignatureError,
    verify_clerk_webhook_signature,
)
from porterchain_api.auth.ensure_user_service import EnsureUserService, normalize_email
from porterchain_api.config import Settings

logger = logging.getLogger("porterchain.security")

_HANDLED = frozenset(
    {
        "user.created",
        "user.updated",
        "user.deleted",
    }
)


class ClerkWebhookService:
    def __init__(self) -> None:
        self._ensure = EnsureUserService()

    def handle(
        self,
        db: Session,
        settings: Settings,
        *,
        payload: bytes,
        svix_id: str | None,
        svix_timestamp: str | None,
        svix_signature: str | None,
    ) -> dict[str, str]:
        secret = (settings.clerk_webhook_signing_secret or "").strip()
        if not secret:
            raise HTTPException(status_code=503, detail="clerk_webhook_not_configured")

        try:
            verify_clerk_webhook_signature(
                payload=payload,
                secret=secret,
                svix_id=svix_id,
                svix_timestamp=svix_timestamp,
                svix_signature=svix_signature,
            )
        except ClerkWebhookSignatureError as exc:
            logger.warning("clerk_webhook_reject reason=%s", exc)
            raise HTTPException(status_code=400, detail="invalid_signature") from exc

        try:
            body = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=400, detail="invalid_payload") from exc

        event_type = str(body.get("type") or "")
        event_id = str(svix_id or body.get("id") or "")
        if not event_id:
            raise HTTPException(status_code=400, detail="missing_event_id")

        if event_type not in _HANDLED:
            logger.info("clerk_webhook_ignored type=%s", event_type)
            return {"status": "ignored"}

        if not claim_clerk_event(db, clerk_event_id=event_id, event_type=event_type):
            db.commit()
            return {"status": "duplicate"}

        try:
            data = body.get("data") if isinstance(body.get("data"), dict) else {}
            self._dispatch(db, settings, event_type=event_type, data=data)
            complete_clerk_event(db, clerk_event_id=event_id)
            db.commit()
            return {"status": "ok"}
        except Exception:
            db.rollback()
            # Re-open session work for release
            try:
                release_clerk_event(db, clerk_event_id=event_id)
                db.commit()
            except Exception:  # noqa: BLE001
                db.rollback()
            logger.exception("clerk_webhook_processing_failed")
            raise HTTPException(status_code=500, detail="webhook_processing_failed") from None

    def _dispatch(self, db: Session, settings: Settings, *, event_type: str, data: dict[str, Any]) -> None:
        clerk_user_id = str(data.get("id") or "")
        if not clerk_user_id:
            raise ValueError("missing_clerk_user_id")

        if event_type == "user.deleted":
            self._ensure.deactivate_clerk_user(db, clerk_user_id=clerk_user_id, commit=False)
            return

        email, verified = _primary_email(data)
        phone = _primary_phone(data)
        issuer = _issuer_from_settings(settings)

        # Never elevate: ensure creates pending/unprovisioned + mirrors legacy only
        self._ensure.ensure_from_clerk_user_payload(
            db,
            clerk_user_id=clerk_user_id,
            email=email,
            email_verified=verified,
            phone=phone,
            issuer=issuer,
            commit=False,
        )


def _primary_email(data: dict[str, Any]) -> tuple[str | None, bool]:
    addresses = data.get("email_addresses") or []
    primary_id = data.get("primary_email_address_id")
    chosen = None
    if primary_id and isinstance(addresses, list):
        for item in addresses:
            if isinstance(item, dict) and item.get("id") == primary_id:
                chosen = item
                break
    if chosen is None and isinstance(addresses, list) and addresses:
        first = addresses[0]
        chosen = first if isinstance(first, dict) else None
    if not chosen:
        return None, False
    email = normalize_email(chosen.get("email_address"))
    verified = str(chosen.get("verification", {}).get("status") or "").lower() == "verified"
    # Also accept Clerk boolean-ish
    if chosen.get("verification") is True:
        verified = True
    return email, verified


def _primary_phone(data: dict[str, Any]) -> str | None:
    phones = data.get("phone_numbers") or []
    if not isinstance(phones, list) or not phones:
        return None
    first = phones[0]
    if isinstance(first, dict):
        return first.get("phone_number")
    return None


def _issuer_from_settings(settings: Settings) -> str | None:
    issuers = [p.strip() for p in (settings.clerk_authorized_issuers or "").split(",") if p.strip()]
    return issuers[0] if len(issuers) == 1 else None
