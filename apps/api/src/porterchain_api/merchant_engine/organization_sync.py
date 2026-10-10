"""Keep crm_companies a projection of the merchants row (org SSOT)."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from porterchain_api.merchant_models import Merchant

ActorKind = Literal["merchant", "admin"]


def _profile_map(merchant: Merchant) -> dict[str, Any]:
    return dict(merchant.profile) if isinstance(merchant.profile, dict) else {}


def sanitize_logo_url(value: Any) -> str | None:
    """Allow only http(s) logo URLs. Empty clears. Reject javascript/data."""
    if value is None:
        return None
    url = str(value).strip()
    if not url:
        return None
    if len(url) > 512:
        raise ValueError("logo_url_invalid")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("logo_url_invalid")
    return url


def _branding_bucket(merchant: Merchant) -> dict[str, Any]:
    settings = _profile_map(merchant).get("settings")
    if not isinstance(settings, dict):
        return {}
    branding = settings.get("branding")
    return dict(branding) if isinstance(branding, dict) else {}


def branding_logo_url(merchant: Merchant) -> str | None:
    raw = _branding_bucket(merchant).get("logo_url")
    try:
        return sanitize_logo_url(raw)
    except ValueError:
        return None


def tracking_page_message(merchant: Merchant) -> str | None:
    message = _branding_bucket(merchant).get("tracking_page_message")
    text = str(message).strip() if message else ""
    return text or None


def public_shipper_branding(merchant: Merchant | None) -> dict[str, Any]:
    if merchant is None:
        return {"company_name": None, "logo_url": None, "tracking_page_message": None}
    return {
        "company_name": merchant.company_name,
        "logo_url": branding_logo_url(merchant),
        "tracking_page_message": tracking_page_message(merchant),
    }


def website_of(merchant: Merchant) -> str | None:
    column = getattr(merchant, "website", None)
    if column:
        return str(column).strip() or None
    value = _profile_map(merchant).get("website")
    return str(value).strip() or None if value else None


def industry_of(merchant: Merchant) -> str | None:
    column = getattr(merchant, "industry", None)
    if column:
        return str(column).strip() or None
    value = _profile_map(merchant).get("industry")
    return str(value).strip() or None if value else None


_UNSET = object()


def stamp_identity_meta(merchant: Merchant, *, actor: ActorKind, actor_id: str | None) -> None:
    profile = _profile_map(merchant)
    profile["identity_meta"] = {
        "updated_by": actor,
        "updated_at": datetime.now(UTC).isoformat(),
        "actor_id": actor_id,
    }
    merchant.profile = profile


def tax_settings_of(merchant: Merchant) -> dict[str, Any]:
    settings = _profile_map(merchant).get("settings")
    if not isinstance(settings, dict):
        return {}
    tax = settings.get("tax")
    return dict(tax) if isinstance(tax, dict) else {}


def tax_legal_meta_of(merchant: Merchant) -> dict[str, Any] | None:
    meta = _profile_map(merchant).get("tax_legal_meta")
    return dict(meta) if isinstance(meta, dict) else None


def tax_legal_snapshot(merchant: Merchant) -> dict[str, Any]:
    tax = tax_settings_of(merchant)
    return {
        "legal_name": merchant.legal_name,
        "hst_number": merchant.hst_number,
        "business_number": merchant.business_number,
        "tax_exempt": bool(tax.get("tax_exempt", False)),
        "tax_region": tax.get("tax_region") or "ON",
        "billing_address": merchant.billing_address,
        "tax_legal_meta": tax_legal_meta_of(merchant),
    }


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


# CRA business number is 9 digits; program accounts append XX#### (e.g. RT0001 for GST/HST).
_CA_BN_RE = re.compile(r"^\d{9}([A-Za-z]{2}\d{4})?$")
_CA_TAX_REGIONS = frozenset(
    {
        "AB",
        "BC",
        "MB",
        "NB",
        "NL",
        "NS",
        "NT",
        "NU",
        "ON",
        "PE",
        "QC",
        "SK",
        "YT",
    }
)


def normalize_ca_tax_id(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"[\s\-]", "", value).upper()


def validate_ca_business_number(value: str | None) -> str | None:
    """Return normalized BN or raise ValueError('business_number_invalid')."""
    cleaned = normalize_ca_tax_id(value)
    if cleaned is None:
        return None
    if not _CA_BN_RE.match(cleaned):
        raise ValueError("business_number_invalid")
    return cleaned


def validate_ca_hst_number(value: str | None) -> str | None:
    """GST/HST account: BN or BN+RTxxxx. Raise ValueError('hst_number_invalid')."""
    cleaned = normalize_ca_tax_id(value)
    if cleaned is None:
        return None
    if not _CA_BN_RE.match(cleaned):
        raise ValueError("hst_number_invalid")
    # Prefer RT program account when a suffix is present.
    if len(cleaned) > 9 and cleaned[9:11] not in {"RT", "RC", "RP", "RM"}:
        raise ValueError("hst_number_invalid")
    return cleaned


def validate_ca_tax_region(value: str | None) -> str:
    region = (normalize_ca_tax_id(value) or "ON")[:2]
    if region not in _CA_TAX_REGIONS:
        raise ValueError("tax_region_invalid")
    return region


def apply_tax_legal(
    merchant: Merchant,
    *,
    actor: ActorKind,
    actor_id: str | None,
    legal_name: Any = _UNSET,
    hst_number: Any = _UNSET,
    business_number: Any = _UNSET,
    tax_exempt: Any = _UNSET,
    tax_region: Any = _UNSET,
) -> list[str]:
    """Last writer on shared tax/legal. Omitted keys stay. Empty string clears."""
    changed: list[str] = []
    if legal_name is not _UNSET:
        next_value = _clean_text(legal_name)
        if merchant.legal_name != next_value:
            merchant.legal_name = next_value
            changed.append("legal_name")
    if hst_number is not _UNSET:
        next_value = validate_ca_hst_number(_clean_text(hst_number))
        if merchant.hst_number != next_value:
            merchant.hst_number = next_value
            changed.append("hst_number")
    if business_number is not _UNSET:
        next_value = validate_ca_business_number(_clean_text(business_number))
        if merchant.business_number != next_value:
            merchant.business_number = next_value
            changed.append("business_number")

    tax_changed = False
    tax = tax_settings_of(merchant)
    if tax_exempt is not _UNSET:
        next_exempt = bool(tax_exempt)
        if bool(tax.get("tax_exempt", False)) != next_exempt:
            tax["tax_exempt"] = next_exempt
            tax_changed = True
            changed.append("tax_exempt")
    if tax_region is not _UNSET:
        next_region = validate_ca_tax_region(_clean_text(tax_region))
        if (tax.get("tax_region") or "ON") != next_region:
            tax["tax_region"] = next_region
            tax_changed = True
            changed.append("tax_region")
    if tax_changed:
        profile = _profile_map(merchant)
        settings = dict(profile.get("settings") or {}) if isinstance(profile.get("settings"), dict) else {}
        settings["tax"] = tax
        profile["settings"] = settings
        merchant.profile = profile

    if changed:
        profile = _profile_map(merchant)
        profile["tax_legal_meta"] = {
            "updated_by": actor,
            "updated_at": datetime.now(UTC).isoformat(),
            "actor_id": actor_id,
            "fields": changed,
        }
        merchant.profile = profile
    return changed


def project_merchant_company(db: Session, merchant: Merchant) -> Any:
    """Copy operational org fields onto the linked CRM company."""
    from porterchain_api.collaboration_engine.crm_service import CrmSalesService

    return CrmSalesService().project_from_merchant(db, merchant)
