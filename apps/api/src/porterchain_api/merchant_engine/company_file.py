"""Company file completeness. Missing HST does not lock an ACTIVE dispatcher out."""

from __future__ import annotations

from typing import Any

from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_engine.rbac import parse_merchant_role
from porterchain_api.merchant_models import Merchant

COMPANY_FILE_FIELDS: tuple[tuple[str, str], ...] = (
    ("legal_name", "Legal name"),
    ("phone", "Phone"),
    ("billing_address", "Billing address"),
    ("hst_number", "HST number"),
)

_EDIT_ROLES = frozenset({MerchantRole.OWNER, MerchantRole.ADMIN})
_EDIT_STATUSES = frozenset({MerchantStatus.ONBOARDING.value, MerchantStatus.ACTIVE.value})


def billing_address_present(value: Any) -> bool:
    if not value:
        return False
    if isinstance(value, dict):
        text = (
            value.get("formatted")
            or value.get("line1")
            or value.get("street")
            or ""
        )
        return bool(str(text).strip())
    return bool(str(value).strip())


def company_file_missing(merchant: Merchant | None) -> list[str]:
    if merchant is None:
        return [key for key, _ in COMPANY_FILE_FIELDS]
    missing: list[str] = []
    if not (merchant.legal_name or "").strip():
        missing.append("legal_name")
    if not (merchant.phone or "").strip():
        missing.append("phone")
    if not billing_address_present(merchant.billing_address):
        missing.append("billing_address")
    if not (merchant.hst_number or "").strip():
        missing.append("hst_number")
    return missing


def company_file_snapshot(merchant: Merchant | None) -> dict[str, Any]:
    if merchant is None:
        return {
            "company_name": None,
            "legal_name": None,
            "email": None,
            "phone": None,
            "hst_number": None,
            "billing_address": None,
        }
    return {
        "company_name": merchant.company_name,
        "legal_name": merchant.legal_name,
        "email": merchant.email,
        "phone": merchant.phone,
        "hst_number": merchant.hst_number,
        "billing_address": merchant.billing_address,
    }


def can_edit_company_file(status: str | None, role: MerchantRole | str | None) -> bool:
    if not status or status not in _EDIT_STATUSES:
        return False
    parsed = role if isinstance(role, MerchantRole) else parse_merchant_role(role or "")
    return parsed in _EDIT_ROLES


def completeness_payload(merchant: Merchant | None, *, can_edit: bool) -> dict[str, Any]:
    missing = company_file_missing(merchant)
    return {
        "complete": len(missing) == 0,
        "missing": missing,
        "missing_labels": [label for key, label in COMPANY_FILE_FIELDS if key in missing],
        "can_edit": can_edit,
    }


def signup_url(merchant_portal_url: str | None) -> str:
    base = (merchant_portal_url or "http://localhost:3001").rstrip("/")
    return f"{base}/sign-up"
