"""One-click unsubscribe (RFC 8058) for non-transactional email.

CASL s.11: every commercial electronic message carries a working unsubscribe that is
honoured within 10 business days (we apply it immediately). Transactional mail about a
delivery or account (CASL s.6(6)) does not get these headers: it is not marketing and
the recipient cannot opt out of being told where their parcel is.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import quote

from sqlalchemy.orm import Session

#: Categories that are commercial (CASL CEM) and therefore get List-Unsubscribe.
NON_TRANSACTIONAL_CATEGORIES = frozenset({"marketing", "crm"})
TOKEN_TTL_SECONDS = 60 * 60 * 24 * 365


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(secret: str, body: str) -> str:
    key = hashlib.sha256(f"notif-unsub:{secret}".encode()).digest()
    return _b64(hmac.new(key, body.encode(), hashlib.sha256).digest())


def make_token(secret: str, *, role: str, user_id: str, category: str, now: float | None = None) -> str:
    payload = {"r": role, "u": user_id, "c": category, "exp": int((now or time.time()) + TOKEN_TTL_SECONDS)}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    return f"{body}.{_sign(secret, body)}"


def read_token(secret: str, token: str, *, now: float | None = None) -> dict[str, str] | None:
    try:
        body, sig = str(token or "").split(".", 1)
        if not hmac.compare_digest(sig, _sign(secret, body)):
            return None
        data = json.loads(_unb64(body))
    except Exception:  # noqa: BLE001 — any malformed token is simply invalid
        return None
    if not isinstance(data, dict) or not data.get("r") or not data.get("u") or not data.get("c"):
        return None
    if int(data.get("exp") or 0) < (now or time.time()):
        return None
    return {"role": str(data["r"]), "user_id": str(data["u"]), "category": str(data["c"])}


def needs_unsubscribe(category: str | None) -> bool:
    return (category or "").strip().lower() in NON_TRANSACTIONAL_CATEGORIES


def list_unsubscribe_headers(settings: Any, context: dict[str, Any]) -> dict[str, str]:
    """RFC 2369 + RFC 8058 headers for a non-transactional email, else {}."""
    category = str(context.get("category") or "")
    if not needs_unsubscribe(category):
        return {}
    role = str(context.get("recipient_type") or "").strip()
    user_id = str(context.get("recipient_id") or "").strip()
    secret = str(getattr(settings, "jwt_secret", "") or "").strip()
    if not role or not user_id or not secret:
        return {}
    token = make_token(secret, role=role, user_id=user_id, category=category)
    base = str(getattr(settings, "porterchain_api_url", "") or "").rstrip("/")
    url = f"{base}/v1/notifications/unsubscribe?t={quote(token, safe='')}"
    mailbox = str(getattr(settings, "unsubscribe_mailbox", "") or "unsubscribe@porterchain.com")
    return {
        "List-Unsubscribe": f"<{url}>, <mailto:{mailbox}?subject=unsubscribe>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }


SENDER_IDENTITY = "PorterChain Logistics Inc., Toronto, ON, Canada"


def casl_footer(
    settings: Any, context: dict[str, Any], text_body: str, html_body: str | None, headers: dict[str, str]
) -> tuple[str, str | None]:
    """CASL s.6 / GDPR Art. 21: every commercial email carries sender identity and a working,
    visible unsubscribe in the body (headers alone are not enough). Idempotent."""
    if not needs_unsubscribe(str(context.get("category") or "")):
        return text_body, html_body
    link = ""
    raw = headers.get("List-Unsubscribe", "")
    if raw.startswith("<http"):
        link = raw[1 : raw.index(">")]
    if not link:
        mailbox = str(getattr(settings, "unsubscribe_mailbox", "") or "unsubscribe@porterchain.com")
        link = f"mailto:{mailbox}?subject=unsubscribe"
    identity = str(getattr(settings, "casl_sender_identity", "") or SENDER_IDENTITY)
    lower = (text_body or "").lower()
    if "unsubscribe" not in lower and "stop these" not in lower and "abmelden" not in lower:
        text_body = f"{text_body}\n\n—\n{identity}\nUnsubscribe: {link}"
    elif identity.split(",")[0].lower() not in lower:
        text_body = f"{text_body}\n{identity}"
    if html_body is not None and "unsubscribe" not in html_body.lower():
        html_body = (
            f"{html_body}<p style=\"font-size:12px;color:#666\">{identity}<br>"
            f"<a href=\"{link}\">Unsubscribe</a></p>"
        )
    return text_body, html_body


def apply_unsubscribe(db: Session, *, role: str, user_id: str, category: str) -> None:
    """Turn email off for that category. (Leads are handled by the router: CASL consent.)"""
    from porterchain_api.notification_engine.preference_service import PreferenceService

    PreferenceService().upsert(db, user_role=role, user_id=user_id, category=category, email_enabled=False)
    if category == "marketing":  # CASL: withdrawing consent clears the consent record
        from porterchain_api.notification_engine.user_settings import (
            UserSettingsService,
        )

        row = UserSettingsService().get(db, user_role=role, user_id=user_id)
        if row is not None:
            row.marketing_consent_at = None
            row.marketing_consent_source = None
    db.commit()
