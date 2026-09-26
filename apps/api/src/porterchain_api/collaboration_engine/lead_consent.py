"""CASL-oriented consent evidence helpers for CrmLead.consent JSON."""

from __future__ import annotations

import hashlib
import hmac
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

CASL_TEXT_VERSION = "casl_v1_marketing"
_BOOL_KEYS = ("marketing", "sms", "whatsapp", "analytics", "experience")
LEGAL_BASIS_VALUES = frozenset({"consent", "legitimate_interest", "contract"})


def casl_evidence(
    raw: dict[str, Any] | None,
    *,
    source: str,
    actor: str = "lead",
    text_version: str = CASL_TEXT_VERSION,
    force_marketing: bool | None = None,
    legal_basis: str | None = None,
) -> dict[str, Any]:
    """Normalize form/CMP flags into a consent bag with capture evidence.

    ``legal_basis`` maps GDPR Art.6 / PIPEDA purpose: consent | legitimate_interest | contract.
    """
    data = dict(raw or {})
    out: dict[str, Any] = {}
    for key in _BOOL_KEYS:
        if key in data:
            out[key] = bool(data[key])
    if force_marketing is True:
        out["marketing"] = True
    elif force_marketing is False:
        out["marketing"] = False
    if not out and force_marketing is None and not legal_basis and "legal_basis" not in data:
        return {}
    out.setdefault("source", source)
    out.setdefault("actor", actor)
    out.setdefault("text_version", text_version)
    out.setdefault("captured_at", datetime.now(UTC).isoformat())
    # Preserve audit flags from booking without inventing nurture opt-in.
    for key in ("terms_accepted", "privacy_accepted", "dangerous_goods_confirmed", "consent_at"):
        if key in data and data[key] is not None:
            out[key] = data[key]

    basis = legal_basis or data.get("legal_basis")
    if isinstance(basis, str) and basis.strip():
        basis_n = basis.strip().lower()
        if basis_n in LEGAL_BASIS_VALUES:
            out["legal_basis"] = basis_n
    elif out.get("marketing") is True:
        out.setdefault("legal_basis", "consent")
    elif out.get("terms_accepted") or out.get("privacy_accepted"):
        out.setdefault("legal_basis", "contract")

    return out


def make_unsubscribe_token(*, lead_id: str, secret: str, ttl_seconds: int = 60 * 60 * 24 * 90) -> str:
    exp = int(time.time()) + max(60, ttl_seconds)
    msg = f"unsub:{lead_id.strip()}:{exp}"
    sig = hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{lead_id}.{exp}.{sig}"


def verify_unsubscribe_token(*, token: str, secret: str) -> str | None:
    """Return lead_id when token is valid, else None."""
    secret = (secret or "").strip()
    token = (token or "").strip()
    if not secret or not token:
        return None
    parts = token.split(".")
    if len(parts) != 3:
        return None
    lead_id, exp_s, sig = parts
    try:
        exp = int(exp_s)
    except ValueError:
        return None
    if exp < int(time.time()) or not lead_id:
        return None
    msg = f"unsub:{lead_id}:{exp}"
    expected = hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    return lead_id


def apply_unsubscribe(lead_consent: dict[str, Any] | None) -> dict[str, Any]:
    c = dict(lead_consent or {})
    c["marketing"] = False
    c["source"] = "unsubscribe"
    c["actor"] = "lead"
    c["text_version"] = CASL_TEXT_VERSION
    c["captured_at"] = datetime.now(UTC).isoformat()
    c["legal_basis"] = "consent"  # objection / withdraw consent
    return c


def commit_unsubscribe(db: Session, lead: Any) -> None:
    """Flip marketing consent, upsert suppression, and commit (public router UoW)."""
    from porterchain_api.collaboration_engine.lead_suppression import upsert_suppression

    lead.consent = apply_unsubscribe(lead.consent if isinstance(lead.consent, dict) else {})
    upsert_suppression(
        db,
        email=lead.email,
        phone=lead.phone,
        source="unsubscribe",
        lead_id=lead.id,
    )
    db.commit()


__all__ = [
    "CASL_TEXT_VERSION",
    "LEGAL_BASIS_VALUES",
    "apply_unsubscribe",
    "casl_evidence",
    "commit_unsubscribe",
    "make_unsubscribe_token",
    "verify_unsubscribe_token",
]
